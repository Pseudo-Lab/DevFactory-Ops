import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import datetime as dt
import tempfile
import json

sys.modules.setdefault("oci", MagicMock())
spec = importlib.util.spec_from_file_location("newsletter_backup", Path(__file__).with_name("backup.py"))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

class BackupTests(unittest.TestCase):
    def exercise(self, objects=(), fail_dump=False, bad_checksum=False, prune=False):
        c = MagicMock()
        c.get_bucket.return_value.data.public_access_type = "NoPublicAccess"
        c.get_bucket.return_value.data.versioning = "Disabled"
        c.list_objects.return_value.data.objects = list(objects)
        c.list_objects.return_value.data.next_start_with = None
        c.put_object.return_value.headers = {"etag": "uploaded"}
        c.get_object.return_value.data.raw.stream.return_value = [b"wrong" if bad_checksum else b"encrypted"]
        real_tempdir=tempfile.TemporaryDirectory
        commands=[]
        def run(args, **kw):
            commands.append(args)
            if "pg_dump" in " ".join(args):
                if fail_dump: return MagicMock(returncode=1)
                kw["stdout"].write(b"synthetic dump")
            if args[0].endswith("/age"):
                Path(args[args.index("-o")+1]).write_bytes(b"encrypted")
            return MagicMock(returncode=0)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            read_text=Path.read_text
            def read(path, *a, **k):
                if str(path)=="/etc/ops-cluster-backup/config.json":
                    return json.dumps({"region":"test","namespace":"test","bucket":"test","recipient":"test"})
                return read_text(path,*a,**k)
            with patch.object(b.tempfile,"TemporaryDirectory",side_effect=lambda **kw: real_tempdir(dir=root)), patch.object(b,"STATE",root), patch.object(b.oci.object_storage,"ObjectStorageClient",return_value=c), patch.object(b.subprocess,"run",side_effect=run), patch.object(Path,"read_text",read), patch.object(sys,"argv",["backup"]+(["--prune-only"] if prune else [])):
                error=None
                try: b.main()
                except RuntimeError as e: error=e
                success=(root/"status.json").exists() and json.loads((root/"status.json").read_text())["success"]
            return c,commands,error,success

    def test_expiry_scoped_to_old_prefix_and_extension(self):
        now=dt.datetime.now(dt.timezone.utc)
        def obj(name,days): return type("Obj",(),{"name":name,"time_created":now-dt.timedelta(days=days),"etag":"old"})()
        c,_,e,_=self.exercise([obj("newsletter/old.dump.age",8),obj("newsletter/new.dump.age",6),obj("cluster/old.dump.age",8),obj("newsletter/other.txt",8)],prune=True)
        self.assertIsNone(e)
        self.assertEqual(c.delete_object.call_count,1)
        self.assertEqual(c.delete_object.call_args.args[2],"newsletter/old.dump.age")
        self.assertEqual(c.delete_object.call_args.kwargs["if_match"],"old")

    def test_expiry_runs_when_new_dump_fails(self):
        o=type("Obj",(),{"name":"newsletter/old.dump.age","time_created":dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=8),"etag":"old"})()
        c,_,e,success=self.exercise([o],fail_dump=True)
        self.assertIsNotNone(e)
        self.assertEqual(c.delete_object.call_count,1)
        self.assertFalse(success)
        c.put_object.assert_not_called()

    def test_dump_only_dedicated_database(self):
        _,cmds,e,success=self.exercise()
        self.assertIsNone(e)
        self.assertTrue(success)
        dump=[cmd for cmd in cmds if "pg_dump" in " ".join(cmd)]
        self.assertEqual(len(dump),1)
        self.assertIn("-d data_initiative_newsletter",dump[0][-1])
        self.assertNotIn("pg_dumpall",dump[0][-1])
        self.assertEqual(dump[0][:7], ["/usr/local/bin/k3s", "kubectl", "exec", "-n", "shared-postgresql", "shared-postgresql-0", "--"])
        self.assertFalse(any("devfactory-postgres" in cmd for cmd in cmds))

    def test_checksum_failure_does_not_report_success(self):
        _,_,e,success=self.exercise(bad_checksum=True)
        self.assertIsNotNone(e)
        self.assertFalse(success)

if __name__ == "__main__": unittest.main()
