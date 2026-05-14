#!/usr/bin/env bash
set -euo pipefail

# Canary deployment script for recipe-service
# Usage: ./canary-deploy.sh [weight] [tag]
#   weight: percentage of traffic to route to canary (default: 10)
#   tag:    Docker image tag for the canary build (default: canary)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

WEIGHT="${1:-10}"
TAG="${2:-canary}"

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# --- Validate weight ---
if ! [[ "$WEIGHT" =~ ^[0-9]+$ ]] || [ "$WEIGHT" -lt 0 ] || [ "$WEIGHT" -gt 100 ]; then
    error "Weight must be an integer between 0 and 100. Got: $WEIGHT"
fi

# --- Check prerequisites ---
info "Checking prerequisites..."
command -v minikube >/dev/null 2>&1 || error "minikube is not installed."
command -v kubectl  >/dev/null 2>&1 || error "kubectl is not installed."
command -v docker   >/dev/null 2>&1 || error "docker is not installed."

minikube status --format='{{.Host}}' 2>/dev/null | grep -q "Running" \
    || error "Minikube is not running. Start it with: minikube start"

# --- Verify stable deployment exists ---
info "Verifying stable deployment exists..."
kubectl get deployment recipe-service -n recipeapp >/dev/null 2>&1 \
    || error "Stable recipe-service deployment not found. Run deploy-minikube.sh first."

# --- Point Docker to Minikube's daemon ---
info "Configuring Docker to use Minikube's daemon..."
eval $(minikube docker-env)

# --- Build canary image ---
info "Building recipe-service:${TAG} image..."
docker build -t "recipe-service:${TAG}" "$PROJECT_DIR/services/recipe-service"

# --- Generate canary ingress with specified weight ---
info "Generating canary ingress with ${WEIGHT}% traffic weight..."
sed "s/canary-weight: \"10\"/canary-weight: \"${WEIGHT}\"/" \
    "$SCRIPT_DIR/recipe-service/canary-ingress.yaml" > /tmp/canary-ingress-generated.yaml

# --- Update canary deployment image tag if not default ---
if [ "$TAG" != "canary" ]; then
    info "Updating canary deployment to use tag: ${TAG}..."
    sed "s|recipe-service:canary|recipe-service:${TAG}|g" \
        "$SCRIPT_DIR/recipe-service/canary-deployment.yaml" > /tmp/canary-deployment-generated.yaml
else
    cp "$SCRIPT_DIR/recipe-service/canary-deployment.yaml" /tmp/canary-deployment-generated.yaml
fi

# --- Apply canary resources ---
info "Applying canary deployment..."
kubectl apply -f /tmp/canary-deployment-generated.yaml

info "Applying canary service..."
kubectl apply -f "$SCRIPT_DIR/recipe-service/canary-service.yaml"

info "Applying canary ingress (weight: ${WEIGHT}%)..."
kubectl apply -f /tmp/canary-ingress-generated.yaml

# --- Wait for canary pod to be ready ---
info "Waiting for canary pod to be ready..."
kubectl wait --for=condition=ready pod -l app=recipe-service,version=canary \
    -n recipeapp --timeout=180s

# --- Clean up temp files ---
rm -f /tmp/canary-ingress-generated.yaml /tmp/canary-deployment-generated.yaml

# --- Print status ---
echo ""
info "========================================="
info "  Canary deployment complete!"
info "========================================="
echo ""
info "Canary image:   recipe-service:${TAG}"
info "Traffic weight: ${WEIGHT}%"
echo ""
kubectl get pods -n recipeapp -l version=canary
echo ""

info "Testing instructions:"
echo ""
echo "  Force traffic to canary:"
echo "    curl -H 'X-Canary: always' http://localhost:8000/"
echo ""
echo "  Monitor canary logs:"
echo "    kubectl logs -f -l version=canary -n recipeapp"
echo ""
echo "  Increase canary traffic:"
echo "    ./canary-deploy.sh 25 ${TAG}"
echo ""
echo "  Promote canary to stable:"
echo "    ./canary-promote.sh ${TAG}"
echo ""
echo "  Rollback canary:"
echo "    ./canary-rollback.sh"
echo ""
