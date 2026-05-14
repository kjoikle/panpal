#!/usr/bin/env bash
set -euo pipefail

# Minikube deployment script for RecipeApp
# Builds images inside Minikube's Docker daemon and deploys all K8s manifests.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
K8S_DIR="$SCRIPT_DIR"

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# --- 1. Check prerequisites ---
info "Checking prerequisites..."

command -v minikube >/dev/null 2>&1 || error "minikube is not installed. Install it from https://minikube.sigs.k8s.io/docs/start/"
command -v kubectl  >/dev/null 2>&1 || error "kubectl is not installed. Install it from https://kubernetes.io/docs/tasks/tools/"
command -v docker   >/dev/null 2>&1 || error "docker is not installed. Install Docker Desktop or the Docker CLI."

info "All prerequisites found."

# --- 2. Start Minikube if not running ---
if minikube status --format='{{.Host}}' 2>/dev/null | grep -q "Running"; then
    info "Minikube is already running."
else
    info "Starting Minikube..."
    minikube start --memory=4096 --cpus=2
    info "Minikube started."
fi

# --- 3. Enable required addons ---
info "Enabling Minikube addons..."
minikube addons enable ingress
minikube addons enable metrics-server
info "Addons enabled."

# --- 4. Point Docker to Minikube's daemon ---
info "Configuring Docker to use Minikube's daemon..."
eval $(minikube docker-env)

# --- 5. Build Docker images inside Minikube ---
info "Building recipe-service image..."
docker build -t recipe-service:latest "$PROJECT_DIR/services/recipe-service"

info "Building analytics-service image..."
docker build -t analytics-service:latest "$PROJECT_DIR/services/analytics-service"

info "Docker images built successfully."

# --- 6. Apply Kubernetes manifests in dependency order ---
info "Deploying to Kubernetes..."

# Namespace first
info "  Creating namespace..."
kubectl apply -f "$K8S_DIR/namespace.yaml"

# Secrets and ConfigMaps
info "  Applying secrets and configmaps..."
kubectl apply -f "$K8S_DIR/recipe-service/secret.yaml"
kubectl apply -f "$K8S_DIR/recipe-service/configmap.yaml"
kubectl apply -f "$K8S_DIR/analytics-service/secret.yaml"
kubectl apply -f "$K8S_DIR/analytics-service/configmap.yaml"

# Databases (StatefulSets + their Services)
info "  Deploying databases..."
kubectl apply -f "$K8S_DIR/databases/recipe-db.yaml"
kubectl apply -f "$K8S_DIR/databases/analytics-db.yaml"

# Wait for databases to be ready
info "  Waiting for database pods to be ready (this may take a minute)..."
kubectl wait --for=condition=ready pod -l app=recipe-db -n recipeapp --timeout=120s
kubectl wait --for=condition=ready pod -l app=analytics-db -n recipeapp --timeout=120s
info "  Databases are ready."

# Application deployments
info "  Deploying application services..."
kubectl apply -f "$K8S_DIR/recipe-service/deployment.yaml"
kubectl apply -f "$K8S_DIR/analytics-service/deployment.yaml"

# Services
info "  Applying service definitions..."
kubectl apply -f "$K8S_DIR/recipe-service/service.yaml"
kubectl apply -f "$K8S_DIR/analytics-service/service.yaml"

# HPAs
info "  Applying horizontal pod autoscalers..."
kubectl apply -f "$K8S_DIR/recipe-service/hpa.yaml"
kubectl apply -f "$K8S_DIR/analytics-service/hpa.yaml"

# Ingress
info "  Applying ingress..."
kubectl apply -f "$K8S_DIR/ingress.yaml"

# --- 7. Wait for application pods and print status ---
info "Waiting for application pods to be ready..."
kubectl wait --for=condition=ready pod -l app=recipe-service -n recipeapp --timeout=180s
kubectl wait --for=condition=ready pod -l app=analytics-service -n recipeapp --timeout=180s

echo ""
info "========================================="
info "  Deployment complete!"
info "========================================="
echo ""

kubectl get pods -n recipeapp
echo ""

# --- Access instructions ---
info "To access the application, use one of the following methods:"
echo ""
echo "  Option 1 - Minikube Tunnel (recommended):"
echo "    Run:  minikube tunnel"
echo "    Then: curl http://localhost"
echo ""
echo "  Option 2 - Minikube Service:"
echo "    Run:  minikube service recipe-service -n recipeapp"
echo ""
echo "  Option 3 - Add to /etc/hosts:"
echo "    Run:  echo \"\$(minikube ip) recipeapp.example.com\" | sudo tee -a /etc/hosts"
echo "    Then: curl http://recipeapp.example.com"
echo ""
info "Canary release scripts:"
echo ""
echo "  Deploy canary (10% traffic):  ./canary-deploy.sh 10"
echo "  Increase canary traffic:      ./canary-deploy.sh 25"
echo "  Promote canary to stable:     ./canary-promote.sh"
echo "  Rollback canary:              ./canary-rollback.sh"
echo ""
