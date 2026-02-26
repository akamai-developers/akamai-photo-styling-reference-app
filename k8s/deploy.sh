#!/usr/bin/env bash
set -euo pipefail

# Deploy photo-styling app to LKE cluster
# Requires: DOCKERHUB_USER, HF_TOKEN, and KUBECONFIG to be set

if [ -z "${DOCKERHUB_USER:-}" ]; then
  echo "Error: DOCKERHUB_USER is not set"
  echo "Usage: export DOCKERHUB_USER=your-dockerhub-username"
  exit 1
fi

if [ -z "${HF_TOKEN:-}" ]; then
  echo "Error: HF_TOKEN is not set"
  echo "Usage: export HF_TOKEN=hf_your_token_here"
  exit 1
fi

if [ -z "${KUBECONFIG:-}" ]; then
  echo "Error: KUBECONFIG is not set"
  echo "Usage: export KUBECONFIG=\$(pwd)/terraform/kubeconfig.yaml"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Deploying with DOCKERHUB_USER=${DOCKERHUB_USER}"
echo "Using KUBECONFIG=${KUBECONFIG}"

for f in "$SCRIPT_DIR"/*.yaml; do
  envsubst < "$f"
  echo "---"
done | kubectl apply -f -

echo ""
echo "Waiting for external IP..."
kubectl get svc app-service -n photo-styling
