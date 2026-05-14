#!/bin/bash
# run-experiment1.sh
#
# Runs the Pod Kill chaos experiment against recipe-service and observes
# Kubernetes self-healing behaviour.
#
# Prerequisites:
#   - Chaos Mesh installed (./install-chaos-mesh.sh)
#   - RBAC configured   (kubectl apply -f rbac.yaml)
#   - Deployment running (kubectl get pods -n recipeapp)

set -e
NAMESPACE=recipeapp
LABEL="app=recipe-service"

echo "========================================================="
echo " Experiment 1: Pod Kill Test"
echo "========================================================="
echo " Target:   recipe-service pod(s) in namespace $NAMESPACE"
echo " Goal:     Verify Kubernetes restarts a pod after a crash"
echo "========================================================="
echo ""

# ── Step 1: Baseline pod state ─────────────────────────────────────────────
echo "[1] Pod state BEFORE experiment:"
kubectl get pods -n "$NAMESPACE" -l "$LABEL" \
  -o custom-columns='NAME:.metadata.name,STATUS:.status.phase,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount,AGE:.metadata.creationTimestamp'
echo ""

# ── Step 2: Inject chaos ───────────────────────────────────────────────────
echo "[2] Applying pod-kill experiment ..."
kubectl apply -f "$(dirname "$0")/experiment1-pod-kill.yaml"
echo ""

# ── Step 3: Watch recovery ─────────────────────────────────────────────────
echo "[3] Watching pod lifecycle for 40 s ..."
echo "    Expected transitions: Running → Terminating → Pending → ContainerCreating → Running"
echo ""

END=$((SECONDS + 40))
while [ $SECONDS -lt $END ]; do
  kubectl get pods -n "$NAMESPACE" -l "$LABEL" \
    --no-headers \
    -o custom-columns='NAME:.metadata.name,STATUS:.status.phase,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount' \
    2>/dev/null || true
  echo "  --- $(date '+%H:%M:%S') ---"
  sleep 5
done
echo ""

# ── Step 4: Final state ────────────────────────────────────────────────────
echo "[4] Pod state AFTER experiment:"
kubectl get pods -n "$NAMESPACE" -l "$LABEL" \
  -o custom-columns='NAME:.metadata.name,STATUS:.status.phase,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount'
echo ""

# ── Step 5: Recent events ──────────────────────────────────────────────────
echo "[5] Kubernetes events for recipe-service pods:"
kubectl get events -n "$NAMESPACE" \
  --field-selector reason=Killing \
  --sort-by='.lastTimestamp' | tail -5 || true
echo ""

# ── Step 6: Clean up ──────────────────────────────────────────────────────
echo "[6] Removing PodChaos resource ..."
kubectl delete -f "$(dirname "$0")/experiment1-pod-kill.yaml" --ignore-not-found
echo ""

echo "========================================================="
echo " Experiment 1 Complete"
echo " Expected result: pod RESTARTS counter incremented by 1"
echo " If still Pending after 40 s: check liveness probe config"
echo "========================================================="
