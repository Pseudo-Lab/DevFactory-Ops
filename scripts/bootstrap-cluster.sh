#!/bin/bash
# scripts/bootstrap-cluster.sh
# Unified bootstrap script for DevFactory OCI Cluster

set -e

# --- Directory Awareness ---
# Ensure the script runs relative to the repository root even if called from elsewhere
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "📂 Working directory set to: $REPO_ROOT"

# --- Configuration (Environment Variables) ---
: "${K3S_VERSION:=v1.32.12+k3s1}"
: "${HELM_VERSION:=v3.20.0}"
: "${ARGOCD_CHART_VERSION:=9.4.2}"
# LB_IP/DOMAIN should be provided for remote access via OCI Load Balancer or DNS
# : "${LB_IP:=}" 
# : "${DOMAIN:=}"

# Detect Instance Public IP
INSTANCE_IP=$(curl -s ifconfig.me)

# Prepare TLS SAN arguments
TLS_SAN_FLAGS="--tls-san $INSTANCE_IP"
[ -n "$LB_IP" ] && TLS_SAN_FLAGS="$TLS_SAN_FLAGS --tls-san $LB_IP"
[ -n "$DOMAIN" ] && TLS_SAN_FLAGS="$TLS_SAN_FLAGS --tls-san $DOMAIN"

if [ -n "$LB_IP" ] || [ -n "$DOMAIN" ]; then
    echo "ℹ️ Using additional SANs: ${LB_IP:+$LB_IP }${DOMAIN:+$DOMAIN}"
else
    echo "⚠️ LB_IP/DOMAIN not provided. Remote access via LB/Domain might fail TLS verification."
fi

echo "🚀 Starting Unified Cluster Bootstrap..."

# 1. OS Firewall Setup (iptables)
echo "🔒 Configuring OS Firewall..."
sudo iptables -I INPUT 1 -p tcp --dport 6443 -j ACCEPT
sudo iptables -I INPUT 1 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 1 -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 1 -p tcp --dport 30080 -j ACCEPT
sudo iptables -I INPUT 1 -p tcp --dport 30443 -j ACCEPT
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save

# 2. k3s Installation
echo "🎡 Installing k3s (Version: $K3S_VERSION)..."
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="$K3S_VERSION" sh -s - \
    --disable traefik \
    --disable servicelb \
    --write-kubeconfig-mode 644 \
    $TLS_SAN_FLAGS

# 3. Kubeconfig Standard Setup
echo "🔑 Setting up standard Kubeconfig (~/.kube/config)..."
# Determine the real user's home if run with sudo
REAL_USER=${SUDO_USER:-$USER}
USER_HOME=$(eval echo "~$REAL_USER")

mkdir -p "$USER_HOME/.kube"
sudo cp /etc/rancher/k3s/k3s.yaml "$USER_HOME/.kube/config"
sudo chown "$REAL_USER:$REAL_USER" "$USER_HOME/.kube/config"
chmod 600 "$USER_HOME/.kube/config"
export KUBECONFIG="$USER_HOME/.kube/config"

# 4. Shell Persistence (Aliases & Completion)
echo "🐚 Configuring shell persistence (.bashrc)..."
if ! grep -q "KUBECONFIG" "$USER_HOME/.bashrc"; then
    echo "export KUBECONFIG=\$HOME/.kube/config" >> "$USER_HOME/.bashrc"
    echo 'source <(kubectl completion bash)' >> "$USER_HOME/.bashrc"
    echo 'alias k=kubectl' >> "$USER_HOME/.bashrc"
    echo 'complete -F __start_kubectl k' >> "$USER_HOME/.bashrc"
    echo "✅ Added KUBECONFIG, aliases, and completion to .bashrc"
fi

# 5. Wait for k3s to be ready
echo "⏳ Waiting for k3s to be ready..."
until sudo kubectl get nodes | grep -q "Ready"; do
  sleep 2
done

# 6. Helm Installation
if ! command -v helm &> /dev/null; then
    echo "📦 Helm not found, installing version $HELM_VERSION..."
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | DESIRED_VERSION="$HELM_VERSION" bash
else
    echo "✅ Helm is already installed ($(helm version --short))."
fi

# 7. ArgoCD Installation (Bootstrap)
echo "🐙 Installing ArgoCD (Chart Version: $ARGOCD_CHART_VERSION)..."
helm upgrade --install argocd argo-cd \
  --repo https://argoproj.github.io/argo-helm \
  --namespace argocd --create-namespace \
  --version "$ARGOCD_CHART_VERSION" \
  --set server.extraArgs={--insecure}

# 8. Wait for ArgoCD CRDs to be ready
echo "⏳ Waiting for ArgoCD CRDs to be established..."
kubectl wait --for=condition=established --timeout=120s crd/applications.argoproj.io

# 9. Apply Root App (GitOps Start)
echo "🌱 Applying Root Application (GitOps)..."
kubectl apply -f kubernetes/clusters/prod/root-app.yaml

echo "✅ Bootstrap Complete! Check ArgoCD for synchronization status."
echo "🎉 Setup Finished! Please run 'source ~/.bashrc' to apply aliases."