#!/bin/bash
# install-chaos-mesh.sh
# Installs Chaos Mesh on an existing Minikube cluster using Helm.
# Run this once before executing any chaos experiments.
#
# Prerequisites:
#   - Minikube running (minikube start)
#   - kubectl configured to point at Minikube
#   - Helm 3 installed

set -e

echo "=== Installing Chaos Mesh on Minikube ==="

# Verify Minikube is running
if ! minikube status 2>/dev/null | grep -q "Running"; then
  echo "ERROR: Minikube is not running. Start it with: minikube start"
  exit 1
fi

# Add and update the Chaos Mesh Helm repo
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update

# Create namespace (idempotent)
kubectl create namespace chaos-mesh --dry-run=client -o yaml | kubectl apply -f -

# Detect container runtime inside Minikube.
# Recent Minikube versions default to containerd; older ones may use docker.
RUNTIME=$(minikube ssh "sudo crictl info 2>/dev/null" 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',{}).get('runtimeType','containerd').split('.')[-1])" \
  2>/dev/null || echo "containerd")

echo "Detected container runtime: $RUNTIME"

if [ "$RUNTIME" = "docker" ]; then
  SOCKET_PATH="/var/run/docker.sock"
else
  RUNTIME="containerd"
  SOCKET_PATH="/run/containerd/containerd.sock"
fi

# Install (or upgrade) Chaos Mesh
helm upgrade --install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace=chaos-mesh \
  --set chaosDaemon.runtime="$RUNTIME" \
  --set chaosDaemon.socketPath="$SOCKET_PATH" \
  --version 2.6.3 \
  --wait \
  --timeout 5m

echo ""
echo "=== Chaos Mesh installed ==="
echo "Verify:    kubectl get pods -n chaos-mesh"
echo "Dashboard: kubectl port-forward svc/chaos-dashboard 2333:2333 -n chaos-mesh"
echo "           then open http://localhost:2333"
