#!/usr/bin/env bash
set -euo pipefail

# Canary rollback script for recipe-service
# Removes all canary resources, returning 100% traffic to stable.
# Usage: ./canary-rollback.sh

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# --- Check prerequisites ---
command -v kubectl >/dev/null 2>&1 || error "kubectl is not installed."

# --- Remove canary resources ---
info "Rolling back canary deployment..."

kubectl delete ingress recipeapp-ingress-canary -n recipeapp --ignore-not-found
info "Canary ingress removed."

kubectl delete service recipe-service-canary -n recipeapp --ignore-not-found
info "Canary service removed."

kubectl delete deployment recipe-service-canary -n recipeapp --ignore-not-found
info "Canary deployment removed."

echo ""
info "========================================="
info "  Canary rollback complete!"
info "========================================="
echo ""
info "All canary resources have been removed."
info "100% of traffic is now routed to the stable deployment."
echo ""
kubectl get pods -n recipeapp -l app=recipe-service
echo ""
