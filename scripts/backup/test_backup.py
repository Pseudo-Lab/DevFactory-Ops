import hashlib
import json
from pathlib import Path
import sqlite3
import tarfile
import tempfile
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import patch

import backup


class Body:
    def __init__(self, data):
        self.data = data
        self.raw = self

    def stream(self, size, decode_content=False):
        yield self.data

    def close(self):
        pass


class Store:
    def __init__(self):
        self.objects = {}
        self.deleted = []
        self.corrupt = set()
        self.corrupt_new = False
        self.public_access_type = "NoPublicAccess"
        self.versioning = "Disabled"
        for i in range(5):
            name = f"cluster/2026010{i + 1}T030000Z-{'a' * 32}.tar.gz.age"
            self.objects[name] = b"old backup" + bytes([i])

    def get_bucket(self, *args):
        return Obj(data=Obj(public_access_type=self.public_access_type, versioning=self.versioning))

    def list_objects(self, *args, fields=None, start=None):
        items = [Obj(name=name, size=len(data), etag=name) for name, data in sorted(self.objects.items())]
        offset = int(start or 0)
        return Obj(data=Obj(objects=items[offset:offset + 2],
                            next_start_with=str(offset + 2) if offset + 2 < len(items) else None))

    def put_object(self, namespace, bucket, name, data, **kwargs):
        assert kwargs['if_none_match'] == '*'
        assert name not in self.objects
        self.objects[name] = data.read()
        assert kwargs['opc_meta']['sha256'] == hashlib.sha256(self.objects[name]).hexdigest()
        if self.corrupt_new:
            self.corrupt.add(name)
        return Obj(headers={'etag': name})

    def get_object(self, namespace, bucket, name, if_match):
        assert if_match == name
        data = self.objects[name]
        return Obj(headers={'opc-meta-sha256': hashlib.sha256(data).hexdigest()},
                   data=Body(data + b'corrupt' if name in self.corrupt else data))

    def delete_object(self, namespace, bucket, name, if_match):
        assert if_match == name
        self.deleted.append(name)
        del self.objects[name]


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.encrypted = self.root / 'encrypted.age'
        self.encrypted.write_bytes(b'new encrypted backup')
        self.config = {'namespace': 'test', 'bucket': 'test'}
        self.store = Store()

    def upload(self):
        return backup.upload_and_prune(self.store, self.config, self.encrypted)

    def test_retention_uses_all_pages_and_keeps_unrelated_objects(self):
        self.store.objects['unrelated'] = b'keep me'
        result = self.upload()
        self.assertEqual(result['retained'], 5)
        self.assertEqual(len(self.store.deleted), 1)
        self.assertIn('unrelated', self.store.objects)

    def test_corrupt_new_download_never_prunes(self):
        old = set(self.store.objects)
        self.store.corrupt_new = True
        with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
            self.upload()
        self.assertEqual(set(self.store.objects), old)
        self.assertEqual(len(self.store.deleted), 1)
        self.store.corrupt_new = False
        self.assertEqual(self.upload()['retained'], 5)

    def test_failed_new_upload_cleanup_never_deletes_old_backups(self):
        old = set(self.store.objects)
        self.store.corrupt_new = True
        with patch.object(self.store, 'delete_object', side_effect=TimeoutError):
            with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
                self.upload()
        self.assertTrue(old.issubset(self.store.objects))
        self.assertEqual(self.store.deleted, [])

    def test_corrupt_retained_backup_never_prunes(self):
        self.store.corrupt.add(sorted(self.store.objects)[-1])
        with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
            self.upload()
        self.assertEqual(self.store.deleted, [])

    def test_changed_bucket_settings_block_upload(self):
        for key, value in [('public_access_type', 'ObjectRead'), ('versioning', 'Enabled')]:
            with self.subTest(key=key):
                store = Store()
                setattr(store, key, value)
                with self.assertRaises(RuntimeError):
                    backup.upload_and_prune(store, self.config, self.encrypted)
                self.assertEqual(len(store.objects), 5)

    def test_budget_includes_new_upload_before_pruning(self):
        used = sum(map(len, self.store.objects.values()))
        with patch.object(backup, 'MAX_BYTES', used):
            with self.assertRaisesRegex(RuntimeError, 'budget'):
                self.upload()
        self.assertEqual(len(self.store.objects), 5)

    def test_unexpected_future_object_prevents_pruning(self):
        self.store.objects[f"cluster/99990101T030000Z-{'b' * 32}.tar.gz.age"] = b'future'
        with self.assertRaisesRegex(RuntimeError, 'concurrent writer'):
            self.upload()
        self.assertEqual(self.store.deleted, [])

    def test_failed_upload_does_not_delete_anything(self):
        with patch.object(self.store, 'put_object', side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                self.upload()
        self.assertEqual(self.store.deleted, [])

    def test_snapshot_restores_sqlite_and_manifest_without_upload_files(self):
        db = self.root / 'live.db'
        token = self.root / 'token'
        token.write_bytes(b'test recovery token')
        conn = sqlite3.connect(db)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('CREATE TABLE proof (value TEXT)')
        conn.execute("INSERT INTO proof VALUES ('committed-in-wal')")
        conn.commit()
        self.addCleanup(conn.close)
        target = self.root / 'snapshot'
        target.mkdir()
        with patch.object(backup, 'DB', db), patch.object(backup, 'TOKEN', token), \
             patch.object(backup, 'keys', return_value={'items': [{'data': {'tls.key': 'test'}}]}), \
             patch.object(backup.subprocess, 'run', return_value=Obj(stdout='k3s test')):
            archive = backup.snapshot(target)
        with tarfile.open(archive) as tar:
            self.assertEqual(set(tar.getnames()), {'state.db', 'server-token', 'sealed-secrets.json', 'manifest.json'})
            manifest = json.load(tar.extractfile('manifest.json'))
            for name, details in manifest['files'].items():
                self.assertEqual(hashlib.sha256(tar.extractfile(name).read()).hexdigest(), details['sha256'])
        restored = sqlite3.connect(target / 'state.db')
        self.addCleanup(restored.close)
        self.assertEqual(restored.execute('SELECT value FROM proof').fetchone()[0], 'committed-in-wal')

    def test_key_rotation_aborts_snapshot(self):
        db = self.root / 'live.db'
        sqlite3.connect(db).close()
        token = self.root / 'token'
        token.write_bytes(b'token')
        target = self.root / 'snapshot'
        target.mkdir()
        with patch.object(backup, 'DB', db), patch.object(backup, 'TOKEN', token), \
             patch.object(backup, 'keys', side_effect=[{'key': 'before'}, {'key': 'after'}]):
            with self.assertRaisesRegex(RuntimeError, 'changed during snapshot'):
                backup.snapshot(target)

    def test_empty_recovery_token_is_rejected(self):
        token = self.root / 'token'
        token.write_text('\n')
        with patch.object(backup, 'TOKEN', token):
            with self.assertRaisesRegex(RuntimeError, 'Empty server token'):
                backup.snapshot(self.root)

    def test_missing_sealing_private_key_is_rejected(self):
        result = Obj(stdout=json.dumps({'items': [{'data': {'tls.crt': 'cert'}}]}))
        with patch.object(backup.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'Incomplete sealing key'):
                backup.keys()

    def test_failure_preserves_last_success_and_marks_failed(self):
        with patch.object(backup, 'STATE', self.root), patch.object(backup, 'METRICS', self.root/'backup.prom'):
            backup.metrics(True, {'stored_bytes': 123, 'backup_bytes': 123, 'retained': 1})
            previous = json.loads((self.root/'status.json').read_text())['last_success']
            backup.metrics(False)
            state = json.loads((self.root/'status.json').read_text())
            self.assertEqual(state['last_success'], previous)
            self.assertEqual(state['success'], 0)
            self.assertIn('ops_cluster_backup_success 0', (self.root/'backup.prom').read_text())


if __name__ == '__main__':
    unittest.main()
