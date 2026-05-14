#!/bin/bash
# run-experiment2.sh
#
# Injects 3 000 ms of network latency between recipe-service and analytics-service,
# then verifies that recipe-service degrades gracefully (still serves requests)
# and logs timeout warnings as expected.
#
# Prerequisites:
#   - Chaos Mesh installed (./install-chaos-mesh.sh)
#   - RBAC configured   (kubectl apply -f rbac.yaml)
#   - Both services running (kubectl get pods -n recipeapp)

set -e
NAMESPACE=recipeapp
RECIPE_LABEL="app=recipe-service"
ANALYTICS_LABEL="app=analytics-service"

echo "========================================================="
echo " Experiment 2: Network Latency Test"
echo "========================================================="
echo " Latency injected: 3 000 ms (ANALYTICS_TIMEOUT = 2 000 ms)"
echo " Direction:        recipe-service → analytics-service"
echo " Duration:         120 s (auto-removed)"
echo "========================================================="
echo ""

# ── Step 1: Get recipe-service URL ────────────────────────────────────────
RECIPE_URL=$(minikube service recipe-service -n "$NAMESPACE" --url 2>/dev/null | head -1)
if [ -z "$RECIPE_URL" ]; then
  echo "[!] Could not auto-detect service URL. Using kubectl port-forward fallback."
  echo "[!] In a second terminal run: kubectl port-forward svc/recipe-service 8000:8000 -n $NAMESPACE"
  RECIPE_URL="http://localhost:8000"
fi
echo "[0] Recipe service URL: $RECIPE_URL"
echo ""

# ── Step 2: Baseline timing ───────────────────────────────────────────────
echo "[1] Baseline response time (before latency injection):"
curl -s -o /dev/null -w "  Status: %{http_code} | Time: %{time_total}s\n" \
  --max-time 10 "$RECIPE_URL/" \
  || echo "  (Could not reach service — verify port-forward is active)"
echo ""

# ── Step 3: Inject network latency ───────────────────────────────────────
echo "[2] Applying 3 000 ms latency on recipe-service → analytics-service ..."
kubectl apply -f "$(dirname "$0")/experiment2-network-latency.yaml"
echo ""

sleep 5   # allow tc rules to propagate

# ── Step 4: Probe recipe-service under chaos ──────────────────────────────
echo "[3] Probing recipe-service during latency injection (5 requests):"
echo "    Main page requests should still succeed (~2 s slower due to analytics timeout)."
echo ""
for i in $(seq 1 5); do
  printf "  Request %d: " "$i"
  curl -s -o /dev/null -w "Status: %{http_code} | Time: %{time_total}s\n" \
    --max-time 30 "$RECIPE_URL/" \
    || echo "ERROR — service not reachable"
  sleep 3
done
echo ""

# ── Step 5: Check logs for timeout warnings ───────────────────────────────
echo "[4] Analytics timeout warnings in recipe-service logs:"
kubectl logs -n "$NAMESPACE" -l "$RECIPE_LABEL" --tail=30 2>/dev/null \
  | grep -i "analytics\|unreachable\|timeout\|WARNING" \
  || echo "  (No matching log lines found — try checking logs manually)"
echo ""

# ── Step 6: Confirm analytics-service is reachable on its own ─────────────
echo "[5] Analytics-service pod health (should be Running — latency is one-way):"
kubectl get pods -n "$NAMESPACE" -l "$ANALYTICS_LABEL" --no-headers \
  -o custom-columns='NAME:.metadata.name,STATUS:.status.phase,READY:.status.containerStatuses[0].ready'
echo ""

# ── Step 7: Wait for auto-expiry or clean up manually ────────────────────
echo "[6] Waiting for chaos duration to expire (remaining ~90 s) ..."
sleep 90

echo "[7] Confirming NetworkChaos resource removed (auto-expired):"
kubectl get networkchaos -n "$NAMESPACE" 2>/dev/null | grep -v "No resources" \
  || echo "  NetworkChaos resource no longer present — experiment complete"
kubectl delete -f "$(dirname "$0")/experiment2-network-latency.yaml" --ignore-not-found
echo ""

# ── Step 8: Post-chaos baseline ───────────────────────────────────────────
echo "[8] Response time AFTER latency removal (should return to baseline):"
curl -s -o /dev/null -w "  Status: %{http_code} | Time: %{time_total}s\n" \
  --max-time 10 "$RECIPE_URL/" \
  || echo "  (Could not reach service)"
echo ""

echo "========================================================="
echo " Experiment 2 Complete"
echo " Expected: recipe-service served all requests (possibly"
echo "           with ~2 s overhead from analytics timeout)."
echo " Check logs for: 'Analytics service unreachable for'"
echo " assignments/impressions — confirms graceful degradation."
echo "========================================================="
