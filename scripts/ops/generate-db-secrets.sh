#!/bin/bash

# =================================================================#
# DevFactory DB Secret Generation Script
#
# Usage:
#   export DB_URL='postgresql://...'
#   export IP_SALT='...'
#   ./scripts/ops/generate-db-secrets.sh [namespace] [output_path]
# =================================================================#

# --- Directory Awareness ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

# Load local secrets if they exist
ENV_FILE="$SCRIPT_DIR/secrets.env"
if [ -f "$ENV_FILE" ]; then
    echo "💡 Loading secrets from $ENV_FILE"
    # shellcheck source=/dev/null
    source "$ENV_FILE"
fi

NAMESPACE=${1:-"apps-homepage"}
OUTPUT_PATH=${2:-"services/homepage/overlays/prod/sealed-secret.yaml"}

# Check environment variables
if [ -z "$DB_URL" ] || [ -z "$IP_SALT" ]; then
    echo "❌ Error: DB_URL and IP_SALT environment variables must be set."
    echo "Example:"
    echo "  export DB_URL='postgresql://postgres.xxx:pwd@host:6543/postgres'"
    echo "  export IP_SALT='your-secret-salt'"
    exit 1
fi

echo "🔐 Generating SealedSecret for namespace: $NAMESPACE..."

# Create temporary K8s Secret and Seal it
kubectl create secret generic devfactory-db-secrets \
    --namespace "$NAMESPACE" \
    --from-literal=database-url="$DB_URL" \
    --from-literal=ip-salt="$IP_SALT" \
    --dry-run=client -o yaml | \
    kubeseal --controller-name=sealed-secrets --format yaml > "$OUTPUT_PATH"

echo "✅ Successfully created: $OUTPUT_PATH"
echo "---------------------------------------------------"
echo "Next step: git add $OUTPUT_PATH && git commit ..."
