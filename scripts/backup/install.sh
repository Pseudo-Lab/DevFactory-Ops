#!/usr/bin/env bash
set -euo pipefail
# Run as root with a public-recipient config and an age v1.2.1 binary.
test "$EUID" -eq 0
test "$#" -eq 2
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
config=$(realpath -- "$1")
age_binary=$(realpath -- "$2")
test "$("$age_binary" --version)" = v1.2.1
install -d -m 0755 /opt/ops-cluster-backup /var/lib/node_exporter/textfile_collector
install -d -m 0700 /etc/ops-cluster-backup /var/lib/ops-cluster-backup
install -m 0600 "$config" /etc/ops-cluster-backup/config.json
install -m 0755 "$age_binary" /opt/ops-cluster-backup/age
install -m 0644 "$source_dir/backup.py" "$source_dir/requirements.txt" /opt/ops-cluster-backup/
python3 -m venv /opt/ops-cluster-backup/venv
/opt/ops-cluster-backup/venv/bin/pip install --disable-pip-version-check --no-input -r /opt/ops-cluster-backup/requirements.txt
install -m 0644 "$source_dir/ops-cluster-backup.service" "$source_dir/ops-cluster-backup.timer" /etc/systemd/system/
systemd-analyze verify /etc/systemd/system/ops-cluster-backup.service /etc/systemd/system/ops-cluster-backup.timer
systemctl daemon-reload
# First run, off-host restore verification, and timer activation are explicit steps.
