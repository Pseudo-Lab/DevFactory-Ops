#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_file="$repo_root/legacy/traefik/cert-redirect.yml"
destination_dir=/opt/traefik/dynamic

# Traefik already watches this directory. Rename atomically so it never sees
# a partially written YAML file; only this service's configuration is changed.
sudo install -d -m 755 "$destination_dir"
temporary_file="$(sudo mktemp "$destination_dir/.cert-redirect.XXXXXX")"
trap 'sudo rm -f "$temporary_file"' EXIT
sudo install -m 644 "$source_file" "$temporary_file"
sudo mv -f "$temporary_file" "$destination_dir/cert-redirect.yml"
echo "Installed cert-redirect.yml; Traefik will reload it automatically."
