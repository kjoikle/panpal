#!/usr/bin/env bash
set -euo pipefail

# Canary promotion script for recipe-service
# Promotes the canary image to stable and removes canary resources.
# Usage: ./canary-promote.sh [tag]
#   tag: Docker image tag of the canary build to promote (default: canary)

TAG="${1:-canary}"

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# --- Check prerequisites ---
command -v minikube >/dev/null 2>&1 || error "minikube is not installed."
command -v kubectl  >/dev/null 2>&1 || error "kubectl is not installed."
command -v docker   >/dev/null 2>&1 || error "docker is not installed."

minikube status --format='{{.Host}}' 2>/dev/null | grep -q "Running" \
    || error "Minikube is not running."

# --- Verify canary deployment exists ---
kubectl get deployment recipe-service-canary -n recipeapp >/dev/null 2>&1 \
    || error "No canary deployment found. Nothing to promote."

# --- Point Docker to Minikube's daemon ---
info "Configuring Docker to use Minikube's daemon..."
eval $(minikube docker-env)

# --- Re-tag canary image as latest ---
info "Re-tagging recipe-service:${TAG} as recipe-service:latest..."
docker tag "recipe-service:${TAG}" "recipe-service:latest"

# --- Trigger rolling update of stable deployment ---
info "Triggering rolling update of stable deployment..."
kubectl rollout restart deployment/recipe-service -n recipeapp
kubectl rollout status deployment/recipe-service -n recipeapp --timeout=180s

# --- Remove canary resources ---
info "Removing canary resources..."
kubectl delete deployment recipe-service-canary -n recipeapp --ignore-not-found
kubectl delete service recipe-service-canary -n recipeapp --ignore-not-found
kubectl delete ingress recipeapp-ingress-canary -n recipeapp --ignore-not-found

echo ""
info "========================================="
info "  Canary promoted to stable!"
info "========================================="
echo ""
info "The canary image (recipe-service:${TAG}) is now serving all traffic as stable."
echo ""
kubectl get pods -n recipeapp -l app=recipe-service
echo ""
