#!/usr/bin/env bash
set -euo pipefail

OUT=${1:-kubeconfig-jenkins.yaml}
MINIKUBE_IP=$(minikube ip)

kubectl config view --flatten --minify --context=minikube > "$OUT"
sed -i.bak -E "s|server: https://[^ ]+|server: https://${MINIKUBE_IP}:8443|" "$OUT" && rm -f "$OUT.bak"

echo "Wrote $OUT (server: https://${MINIKUBE_IP}:8443)"
