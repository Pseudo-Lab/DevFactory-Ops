# Shared PostgreSQL

Argo CD manages PostgreSQL 15.16 in namespace `shared-postgresql`. The internal
Service is `shared-postgresql.shared-postgresql.svc.cluster.local:5432`.
The newsletter API and hackathon API/migration hook use their existing accounts
and Sealed Secrets. The image digest matches the former ARM64 Docker instance;
this migration does not upgrade PostgreSQL or merge GetCloser data.

The single StatefulSet Pod uses its own 5Gi local-path PVC. Its StorageClass
reclaims with `Retain`, StatefulSet PVC retention is `Retain/Retain`, and the
namespace, StatefulSet, PVC and StorageClass opt out of Argo pruning/deletion.
Local-path capacity is a declaration, not a disk quota; it does not provide HA
or an independent backup. Monitor disk usage and plan any volume growth.

The DB permits TCP 5432 from newsletter API Pods and hackathon API/migration
Pods only. It has no public listener. Credentials are sealed with the existing
controller. The newsletter's host backup script must use the k3s Pod after the
application cutover; retention and encryption policy remain unchanged.

For migration, restore encrypted logical dumps into the independent target
while Docker still serves production. Preserve all databases, roles, ownership,
ACLs, sequences and large objects. Compare schemas and data before switching.
For the final copy, block source connections and stop source writes, repeat the
dump/restore and comparison, then switch caller Secrets. Do not change live
PGDATA with a filesystem copy or allow both instances to accept production writes.

Verify Argo reconciliation, actual caller connection targets, the migration
hook, public service paths and owned synthetic fixtures after cutover. Keep the
Docker container and data for recovery; stopping it does not authorize deleting
its data. After target production writes, returning only the connection URL to
the old source loses new data. Recovery then requires a write freeze and reverse
data synchronization or a repair on the new target.
