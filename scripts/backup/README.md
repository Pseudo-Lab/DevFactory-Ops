# Cluster recovery backup

Daily at 03:00–03:05 Asia/Seoul, `ops-cluster-backup.timer` backs up the
single-node k3s SQLite database through SQLite's online backup API, the server
token needed to decrypt bootstrap data, and all Sealed Secrets controller keys.
Hackathon uploads, other PVC contents and external databases are excluded.
This restores cluster configuration and secrets, not application file contents.

The snapshot is checked for SQLite integrity, compressed and encrypted with age
before upload to the private Standard bucket `devfactory-cluster-backups` in
`ap-chuncheon-1`. Plaintext lives in a root-only systemd runtime directory in
RAM, removed when the service stops. Only the public age recipient is installed
on production. Keep the private identity in an independent password manager;
losing it makes every backup unreadable. Never commit it or the recovery files.

The newest five objects are kept. Upload and download SHA-256 verification,
including verification of every retained object, must succeed before pruning.
An interrupted or failed run does not intentionally prune old backups. The
script stops before an upload would bring this bucket above 8 GB. Monitoring
warns above 6 GB, after a failed run persists for 20 minutes, or after 30 hours
without success (including missing metrics). These limits do not reserve the
account's free allowance; other Standard buckets also consume it.

## Provision and install

`terraform/oci/backup` is a separate Terraform root and state key in the existing
state bucket. It creates only the backup bucket, a dynamic group matching the
production instance and a bucket-scoped policy. Use the existing administrator
OCI configuration to provision it. Runtime uses instance principals, with no
API signing key in the backup configuration. The policy permits object listing,
reading, creation and deletion, but not overwrites or bucket administration.
Instance identity is host-scoped, not process-scoped. Because pruning permits
deletion, these backups are not immutable protection against a compromised host.

Install prerequisites: Python 3.12 with venv support and an official age v1.2.1
binary for the host architecture. Prepare a root-readable JSON configuration:

```json
{
  "region": "ap-chuncheon-1",
  "namespace": "axnda59strvy",
  "bucket": "devfactory-cluster-backups",
  "recipient": "<public age recipient>"
}
```

Run `sudo bash scripts/backup/install.sh /path/config.json /path/age`.
The installer does not activate the timer. First run
`sudo systemctl start ops-cluster-backup.service` and complete recovery
verification below, then `sudo systemctl enable --now ops-cluster-backup.timer`.
Check `systemctl list-timers ops-cluster-backup.timer` and
`sudo cat /var/lib/ops-cluster-backup/status.json`.

## Recovery verification and disaster recovery

1. Download the encrypted object to a trusted recovery host. Compare its SHA-256
   to the recorded object metadata/status, then decrypt with `age --decrypt -i
   /secure/identity.agekey -o backup.tar.gz backup.tar.gz.age`. Keep decrypted
   data on a private RAM-backed directory; it contains live credentials.
2. Require exactly `state.db`, `server-token`, `sealed-secrets.json` and
   `manifest.json`, all ordinary files. Check each size and SHA-256 against the
   manifest and run SQLite `PRAGMA integrity_check` against the extracted DB.
3. Use the k3s version recorded in the manifest. On an isolated disposable host,
   place the database at `/var/lib/rancher/k3s/server/db/state.db` and token at
   `/var/lib/rancher/k3s/server/token`, with root-only access. Start k3s with the
   saved token. A rehearsal must have no route to production and no application
   agents/workloads; verify API readiness and restored objects/keys. Do not
   start a copied cluster on the production network.
4. For actual disaster recovery, stop k3s on the replacement node before
   restoring these files. Re-establish node configuration/networking separately.
   If restoring Sealed Secrets to a fresh cluster instead, restore the exported
   key Secrets before starting/restarting its controller and verify unsealing.
5. Remove the disposable cluster and plaintext recovery files after testing.

`python3 -m unittest discover -s scripts/backup -p 'test_*.py'` covers WAL
snapshot consistency, rotation aborts, pagination, retention and failure gates.
Offline tests do not replace a decrypted restore rehearsal with the real key.
