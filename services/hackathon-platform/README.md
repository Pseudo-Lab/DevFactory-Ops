# Hackathon Platform production operations

Production runs in K3s namespace `hackathon-platform`. Argo CD reconciles
`services/hackathon-platform/overlays/prod` from this repository's `main`.
Application `main` CI publishes ARM64 API/web images and updates both image tags
here. Prepare storage and a verified database backup before merging application
changes that require migrations.

## GitOps-managed resources

- Static local PV/PVC `hackathon-platform-uploads`: 50Gi, bound to `soo-server`,
  host directory `/var/lib/hackathon-platform/uploads`, mounted at
  `/data/hackathon-uploads` in API and migration/maintenance containers.
- PV reclaim policy `Retain`; both PV and PVC opt out of Argo pruning and
  application deletion. Removing manifests does not authorize deleting files.
- App reservation budget 45,000,000,000 bytes; minimum filesystem free space
  10,000,000,000 bytes. Local PV capacity is a declaration, **not a filesystem
  quota or dedicated disk**. Monitor the shared host filesystem.
- One API replica/process, memory request/limit 1GiB, UID/GID 10001.
- This app's Ingress permits 5m bodies, disables request buffering, and uses
  300-second upstream read/send timeouts. Preserve the `/api` prefix.
- Sync order: PV/PVC (-3), configuration/secrets (-2), migration Sync hook (-1),
  API (0), web (1), Ingress (2). The hook uses the same image as the API and runs
  `alembic -c /app/alembic.ini upgrade head`. Failure prevents later waves.

## Server-local preparation

These are host maintenance operations, not an alternative deployment path:

```bash
sudo install -d -o 10001 -g 10001 -m 0750 /var/lib/hackathon-platform/uploads
df -h /var/lib/hackathon-platform/uploads
```

Verify create, fsync, and delete as UID/GID 10001 before attaching the volume.
The local PV requires this node and directory to survive; moving the workload
to another node requires a planned data migration. Files are private application
data; never add a static web route to the directory.

The existing PostgreSQL 15 database `hackathon_platform` is hosted by
`devfactory-postgres`; credentials remain in the existing SealedSecret.
Before schema changes, save a custom-format `pg_dump` with restrictive file
permissions under `/var/backups/hackathon-platform/<UTC timestamp>/`, record its
SHA-256, and verify `pg_restore` into an isolated database. Use `--no-owner
--no-privileges` only for the isolated rehearsal; an actual recovery must retain
or explicitly restore production ownership and grants. Never restore over the
live database as a verification step. Record schema revision, event states,
and row counts before/after migration. Same-host backups do not cover host/disk
loss; independent database and upload backups require separate storage.

## Upload rollout and verification

For the upload release, the starting revision is `0007_roster_manager_role`;
the migration hook applies `0008_devday_uploads` followed by
`0009_event_submission_settings`. Keep existing events and submissions intact.
`devday-seoul-2026` must remain draft; do not recreate or activate it.

Check Argo sync/health, PVC Bound, API live/ready, web health, and actual container
image digests. Use a separate test event and temporary event-scoped account to
verify event registration, submission settings, CSV roster/team confirmation,
chunk retry, finalization, replacement, authorized download, and deadline guards.
Compare downloaded SHA-256 before and after recreating the API Pod. A Pod restart
is an operational verification; deployment configuration still comes from Git.
Mark test events completed and disable test accounts; preserve their audit trail.
Small-file functional checks do not establish 40-team/20GB peak capacity.

## Team-track migration (0010)

K3s verification at 2026-10-05 21:06 KST confirmed Ops commit `1b933ff`
Synced/Healthy, a successful migration hook and revision `0010_team_tracks`.
All 29 table row counts and existing-data fingerprints were preserved, excluding
the new nullable `teams.track` column and expected revision change. Existing 26
teams have NULL tracks; DevDay remains draft. API/web health checks passed.

Verified database backup:
`soo-server:/var/backups/hackathon-platform/20261005T091354Z/hackathon_platform.dump`,
SHA-256 `70197650d9022e291a28e9e07b11fd091f2dc485dfe576a8723220efbec6d2c5`.
The same directory contains `BACKUP-RECORD.txt` and `recover-to-new-db.sh`.
The 20:47 KST pre-migration comparison is recorded in
`/var/backups/hackathon-platform/20261005T114741Z/baseline-comparison.json`.
This backup covers the database only, not uploaded file bodies.

Application main `eea9fed3ee574f5a933fcc81046628d545a07c47` includes 0010;
the migration hook now uses the image's own migration files. The temporary
pre-merge ConfigMap and mounts are removed. Keep the upload mount and migration
hook; never downgrade schema. Image publication and Ops tag updates alone do not
confirm rollout: check Argo sync/health and running API/web image IDs.

DevDay's requested fields are repo/log/PDF required and demo off. At the last
DB check all four were required (settings version 1); use the application's
versioned settings operation to adjust them, preserving existing submissions
and draft status. Verify uploads/downloads, track save/filter and PDF presentation
controls in a separate test event after rollout.

## Maintenance and rollback

Run maintenance in the GitOps-managed API container so it uses the same database,
configuration, UID and mounted volume:

```bash
kubectl -n hackathon-platform exec deploy/hackathon-platform-api -- \
  python -m hackathon_platform_api.cli cleanup-upload-files
```

`--retire-expired` also retires unsubmitted uploads at least one hour after their
event deadline. It is an explicit operation; no scheduled cleanup is installed.
Never manually remove submitted files or immutable metadata to recover space.

To stop new file writes, remove `UPLOAD_ROOT` through a GitOps change while
retaining the new API, schema, PV/PVC, and existing files. Do not downgrade the
schema or blindly restore an older API: older versions permit URL-only writes
that bypass the new required-file rules.
