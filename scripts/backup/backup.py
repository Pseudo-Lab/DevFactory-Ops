"""Host-only k3s SQLite backup. No uploads/PVC data; age identity stays off-host."""

import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tarfile
import tempfile
import time
import uuid


STATE = Path("/var/lib/ops-cluster-backup")
METRICS = Path("/var/lib/node_exporter/textfile_collector/ops_cluster_backup.prom")
CONFIG = Path("/etc/ops-cluster-backup/config.json")
DB = Path("/var/lib/rancher/k3s/server/db/state.db")
TOKEN = Path("/var/lib/rancher/k3s/server/token")
NAME = re.compile(r"cluster/\d{8}T\d{6}Z-[0-9a-f]{32}\.tar\.gz\.age\Z")
KEEP = 5
MAX_BYTES = 8_000_000_000


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def keys():
    result = subprocess.run(
        ["/usr/local/bin/k3s", "kubectl", "get", "secrets", "-n", "kube-system",
         "-l", "sealedsecrets.bitnami.com/sealed-secrets-key", "-o", "json"],
        capture_output=True, check=True, timeout=30,
    )
    data = json.loads(result.stdout)
    if not data["items"]:
        raise RuntimeError("No sealing keys found")
    if any(not item.get("data", {}).get(field)
           for item in data["items"] for field in ("tls.key", "tls.crt")):
        raise RuntimeError("Incomplete sealing key material")
    # Export only fields needed to recreate the keys; discard live ownership metadata.
    return {"apiVersion": "v1", "kind": "List", "items": [
        {"apiVersion": "v1", "kind": "Secret", "type": item["type"],
         "metadata": {"name": item["metadata"]["name"], "namespace": "kube-system",
                      "labels": item["metadata"].get("labels", {})}, "data": item["data"]}
        for item in sorted(data["items"], key=lambda item: item["metadata"]["name"])
    ]}


def snapshot(directory):
    token = TOKEN.read_bytes()
    if not token.strip():
        raise RuntimeError("Empty server token")
    sealing_keys = keys()
    destination = directory / "state.db"
    deadline = time.monotonic() + 180

    def progress(status, remaining, total):
        if time.monotonic() > deadline:
            raise TimeoutError("SQLite snapshot deadline exceeded")

    source = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=5)
    target = sqlite3.connect(str(destination))
    try:
        source.backup(target, pages=1024, progress=progress, sleep=0.05)
        if target.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise RuntimeError("SQLite integrity check failed")
    finally:
        source.close()
        target.close()
    if token != TOKEN.read_bytes() or sealing_keys != keys():
        raise RuntimeError("Recovery token or sealing keys changed during snapshot")
    (directory / "server-token").write_bytes(token)
    (directory / "sealed-secrets.json").write_text(json.dumps(sealing_keys))
    files = ["state.db", "server-token", "sealed-secrets.json"]
    version = subprocess.run(["/usr/local/bin/k3s", "--version"],
                             capture_output=True, check=True, text=True, timeout=10).stdout
    manifest = {"schema": 1, "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "k3s_version": version, "excluded": ["PVC data", "hackathon uploads", "external databases"],
                "files": {name: {"bytes": (directory / name).stat().st_size,
                                 "sha256": sha256(directory / name)} for name in files}}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2))
    archive = directory / "backup.tar.gz"
    with tarfile.open(archive, "w:gz", compresslevel=6) as output:
        for name in [*files, "manifest.json"]:
            output.add(directory / name, arcname=name, recursive=False)
    return archive


def list_objects(client, namespace, bucket):
    objects = []
    start = None
    while True:
        page = client.list_objects(namespace, bucket, fields="name,size,etag", start=start).data
        objects.extend(page.objects)
        start = page.next_start_with
        if not start:
            return objects


def verify_object(client, namespace, bucket, name, etag, expected=None):
    response = client.get_object(namespace, bucket, name, if_match=etag)
    try:
        declared = response.headers.get("opc-meta-sha256")
        if not declared or (expected is not None and declared != expected):
            raise RuntimeError("Backup checksum metadata missing or mismatched")
        digest = hashlib.sha256()
        for chunk in response.data.raw.stream(1024 * 1024, decode_content=False):
            digest.update(chunk)
        if digest.hexdigest() != declared:
            raise RuntimeError("Downloaded backup checksum mismatch")
    finally:
        response.data.close()


def upload_and_prune(client, config, encrypted):
    namespace, bucket = config["namespace"], config["bucket"]
    settings = client.get_bucket(namespace, bucket).data
    if settings.public_access_type != "NoPublicAccess" or settings.versioning != "Disabled":
        raise RuntimeError("Backup bucket must be private with versioning Disabled")
    before = list_objects(client, namespace, bucket)
    size = encrypted.stat().st_size
    if sum(item.size for item in before) + size > MAX_BYTES:
        raise RuntimeError("Upload would exceed the 8 GB backup budget")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"cluster/{stamp}-{uuid.uuid4().hex}.tar.gz.age"
    checksum = sha256(encrypted)
    with encrypted.open("rb") as data:
        result = client.put_object(namespace, bucket, name, data, content_length=size,
                                   if_none_match="*", opc_meta={"sha256": checksum},
                                   content_type="application/octet-stream")
    try:
        verify_object(client, namespace, bucket, name, result.headers["etag"], checksum)
    except Exception:
        # Remove only this failed upload, never an older recovery point.
        try:
            client.delete_object(namespace, bucket, name, if_match=result.headers["etag"])
        except Exception:
            pass  # Preserve the verification failure; monitoring still marks the run failed.
        raise
    objects = list_objects(client, namespace, bucket)
    backups = sorted((item for item in objects if NAME.fullmatch(item.name)),
                     key=lambda item: item.name, reverse=True)
    if not backups or backups[0].name != name:
        raise RuntimeError("Unexpected concurrent writer or clock change; no pruning")
    # Every retained object must be readable and intact before any older one is deleted.
    for item in backups[:KEEP]:
        if item.name != name:
            verify_object(client, namespace, bucket, item.name, item.etag)
    for item in backups[KEEP:]:
        client.delete_object(namespace, bucket, item.name, if_match=item.etag)
    remaining = list_objects(client, namespace, bucket)
    return {"object": name, "sha256": checksum, "backup_bytes": size,
            "stored_bytes": sum(item.size for item in remaining),
            "retained": sum(bool(NAME.fullmatch(item.name)) for item in remaining)}


def metrics(success, result=None):
    state_file = STATE / "status.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    state.update({"last_attempt": time.time(), "success": int(success)})
    if success:
        state.update(result)
        state["last_success"] = state["last_attempt"]
    temporary = STATE / "status.tmp"
    temporary.write_text(json.dumps(state, indent=2))
    temporary.replace(state_file)
    lines = {"last_success_timestamp_seconds": state.get("last_success", 0),
             "last_attempt_timestamp_seconds": state["last_attempt"],
             "success": state["success"], "stored_bytes": state.get("stored_bytes", 0),
             "backup_bytes": state.get("backup_bytes", 0), "retained": state.get("retained", 0)}
    target = METRICS.with_suffix(".tmp")
    target.write_text("".join(f"ops_cluster_backup_{name} {value}\n" for name, value in lines.items()))
    target.chmod(0o644)
    target.replace(METRICS)


def main():
    import oci

    os.umask(0o077)
    with (STATE / "backup.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            metrics(False)
            config = json.loads(CONFIG.read_text())
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            client = oci.object_storage.ObjectStorageClient(
                {"region": config["region"]}, signer=signer, timeout=(10, 90),
                retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
            with tempfile.TemporaryDirectory(prefix="snapshot-", dir="/run/ops-cluster-backup") as temporary:
                directory = Path(temporary)
                archive = snapshot(directory)
                encrypted = directory / "backup.tar.gz.age"
                subprocess.run(["/opt/ops-cluster-backup/age", "--encrypt", "--recipient",
                                config["recipient"], "--output", str(encrypted), str(archive)],
                               check=True, capture_output=True, timeout=120)
                result = upload_and_prune(client, config, encrypted)
            metrics(True, result)
            print(json.dumps({"status": "verified", **result}), flush=True)
        except Exception as error:
            metrics(False)
            # Avoid logging command output or response bodies containing recovery material.
            print(f"Backup failed: {type(error).__name__}", flush=True)
            raise SystemExit(1)


if __name__ == "__main__":
    main()
