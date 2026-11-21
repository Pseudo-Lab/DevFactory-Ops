"""Dedicated newsletter DB dump; encrypted OCI storage, strict seven-day expiry."""
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid
import sys
import oci

PREFIX = 'newsletter/'
STATE = Path('/var/lib/newsletter-backup')

def main():
    os.umask(0o077)
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (STATE / 'lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if '--prune-only' not in sys.argv:
            (STATE / 'status.json').write_text(json.dumps({'success': False, 'at': dt.datetime.now(dt.timezone.utc).isoformat()}))
        c = json.loads(Path('/etc/ops-cluster-backup/config.json').read_text())
        client = oci.object_storage.ObjectStorageClient({'region': c['region']}, signer=oci.auth.signers.InstancePrincipalsSecurityTokenSigner(), timeout=(10,90))
        bucket = client.get_bucket(c['namespace'],c['bucket']).data
        if bucket.public_access_type != 'NoPublicAccess' or bucket.versioning != 'Disabled':
            raise RuntimeError('Private non-versioned backup bucket required')
        # Expiry is independent of successful new backup creation.
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
        start = None
        expired = []
        while True:
            page = client.list_objects(c['namespace'],c['bucket'],prefix=PREFIX,fields='name,timeCreated,etag',start=start).data
            for obj in page.objects:
                if obj.name.startswith(PREFIX) and obj.name.endswith('.dump.age') and obj.time_created < cutoff:
                    expired.append(obj)
            start = page.next_start_with
            if not start: break
        for obj in expired:
            client.delete_object(c['namespace'],c['bucket'],obj.name,if_match=obj.etag)
        if '--prune-only' in sys.argv:
            return
        with tempfile.TemporaryDirectory(prefix='newsletter-',dir='/run') as temp:
            dump = Path(temp)/'db.dump'
            with dump.open('wb') as out:
                r = subprocess.run(['/usr/local/bin/k3s','kubectl','exec','-n','shared-postgresql','shared-postgresql-0','--','sh','-c','exec pg_dump -U "$POSTGRES_USER" -d data_initiative_newsletter -Fc --no-owner --no-acl'],stdout=out,stderr=subprocess.DEVNULL)
            if r.returncode: raise RuntimeError('Dedicated database dump failed')
            with dump.open('rb') as source:
                subprocess.run(['/usr/local/bin/k3s','kubectl','exec','-i','-n','shared-postgresql','shared-postgresql-0','--','pg_restore','--list'],stdin=source,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
            encrypted = Path(temp)/'db.dump.age'
            subprocess.run(['/opt/ops-cluster-backup/age','-r',c['recipient'],'-o',str(encrypted),str(dump)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
            checksum=hashlib.sha256(encrypted.read_bytes()).hexdigest()
            name=PREFIX+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex+'.dump.age'
            with encrypted.open('rb') as data:
                response=client.put_object(c['namespace'],c['bucket'],name,data,if_none_match='*')
            obj=client.get_object(c['namespace'],c['bucket'],name,if_match=response.headers['etag'])
            h=hashlib.sha256()
            for chunk in obj.data.raw.stream(1024*1024,decode_content=False): h.update(chunk)
            if h.hexdigest()!=checksum: raise RuntimeError('Encrypted object verification failed')
            (STATE/'status.json').write_text(json.dumps({'success':True,'at':dt.datetime.now(dt.timezone.utc).isoformat(),'encrypted_bytes':encrypted.stat().st_size,'expired_deleted':len(expired)}))
if __name__ == '__main__':
    main()
