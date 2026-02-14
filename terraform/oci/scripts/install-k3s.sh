#!/bin/bash
# k3s installation script for OCI Instance
# This script is intended to be used as user_data (cloud-init)

set -e

K3S_VERSION="${k3s_version}"

# Check if k3s is already installed
if command -v k3s >/dev/null 2>&1; then
    echo "k3s is already installed. Checking version..."
    current_version=$(k3s --version | awk '{print $3}')
    if [[ "$current_version" == "$K3S_VERSION" ]]; then
        echo "k3s version matches ($K3S_VERSION). Skipping installation."
        exit 0
    fi
    echo "k3s version mismatch (Current: $current_version, Target: $K3S_VERSION). Proceeding with upgrade..."
fi

echo "Starting k3s installation/upgrade (Version: $K3S_VERSION)..."

curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="$K3S_VERSION" sh -s - \
    --disable traefik \
    --disable servicelb \
    --write-kubeconfig-mode 644

echo "k3s installation completed."
