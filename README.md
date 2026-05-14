# PanPal - Recipe App

A Django-based recipe management app built as three independent microservices with Docker, Kubernetes, and canary release support.

## Architecture

The app is split into two services under `django-project/services/`:

- **recipe-service** (port 8000) — Recipe CRUD, user authentication, and the frontend UI
- **analytics-service** (port 8001) — A/B test assignments and event tracking (internal API, not user-facing)
- **scraper-service** (port 8002) - Webscraper service for recipe blog scraping via URL (internal API)

Each service has its own PostgreSQL database (the scraper service is state-less). The recipe service communicates with the analytics service over HTTP using a shared internal key.

## Project Structure

```
panpal/
├── .github/workflows/test.yml      # CI: runs both services' tests in parallel
├── requirements.txt                # Legacy (unused — see per-service requirements below)
├── docs/                           # Documentation
└── django-project/
    ├── docker-compose.yml          # Local development (recommended)
    ├── locust/                     # Load testing scripts
    ├── k8s/                        # Kubernetes manifests and deploy scripts
    │   ├── deploy-minikube.sh      # One-command Minikube deploy
    │   ├── canary-deploy.sh        # Deploy a canary release
    │   ├── canary-promote.sh       # Promote canary to stable
    │   ├── canary-rollback.sh      # Roll back a canary release
    │   ├── recipe-service/         # K8s manifests for recipe service
    │   ├── analytics-service/      # K8s manifests for analytics service
    │   ├── databases/              # PostgreSQL StatefulSets
    │   └── ingress.yaml            # NGINX ingress
    └── services/
        ├── recipe-service/
        │   ├── Dockerfile
        │   ├── requirements.txt
        │   ├── manage.py
        │   ├── seed_data.py
        │   ├── recipeapp/          # Django project settings
        │   └── recipes/            # Recipe app (models, views, templates, tests)
        └── analytics-service/
            ├── Dockerfile
            ├── requirements.txt
            ├── manage.py
            ├── analyticsproject/   # Django project settings
            └── analytics/          # Analytics app (models, views, tests)
```

## Running the App Locally

### Option 1: Docker Compose (Recommended)

Starts both services and both databases with a single command. No other setup needed.

```bash
cd django-project
docker-compose up --build
```

- Recipe app: http://localhost:8000
- Analytics API: http://localhost:8001

To stop: `Ctrl+C`, then `docker-compose down`
To also wipe database volumes: `docker-compose down -v`

> Requires Docker Desktop to be running.

### Option 2: Run Services Manually

If you prefer running without Docker (faster reloads during development), start each service in its own terminal. Both default to SQLite so no database setup is required.

**Terminal 1 — Analytics service:**

```bash
cd django-project/services/analytics-service
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8001
```

**Terminal 2 — Recipe service:**

```bash
cd django-project/services/recipe-service
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

- Recipe app: http://localhost:8000

> The recipe service gracefully handles the analytics service being unavailable, so you can also run just the recipe service on its own.

### Option 3: Kubernetes (Minikube)

For testing the full Kubernetes and canary release infrastructure:

```bash
cd django-project/k8s
./deploy-minikube.sh       # builds images and deploys everything
minikube tunnel            # run in a separate terminal to expose the ingress
```

- App: http://localhost

> Requires Minikube and kubectl to be installed.

## Seed Data

To populate the recipe service database with sample data:

```bash
cd django-project/services/recipe-service
python seed_data.py
```

## Running Tests

Each service has its own test suite. Tests use SQLite by default so no database setup is needed.

```bash
# Recipe service
cd django-project/services/recipe-service
python manage.py test

# Analytics service
cd django-project/services/analytics-service
python manage.py test
```

Run tests using coverage:

```bash
coverage run manage.py test
coverage report
```

Add flag --show-missing to display missing line numbers

See [docs/TESTING.md](docs/TESTING.md) for detailed testing documentation including test structure, what's covered, and troubleshooting.

CI runs both test suites in parallel on every push and pull request to `main`/`master`. See [.github/workflows/test.yml](.github/workflows/test.yml).

## Environment Variables

Each service is configured independently. When using Docker Compose, variables are set in [docker-compose.yml](django-project/docker-compose.yml). When running manually or deploying to a platform, set these per service:

**Recipe service:**
| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | — (falls back to SQLite) |
| `SECRET_KEY` | Django secret key | insecure dev default |
| `DEBUG` | Enable debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `ANALYTICS_SERVICE_URL` | URL of the analytics service | `http://localhost:8001` |
| `INTERNAL_SERVICE_KEY` | Shared key for service-to-service auth | `dev-internal-key` |
| `ANALYTICS_TIMEOUT` | Seconds before analytics call times out | `2` |

**Analytics service:**
| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | — (falls back to SQLite) |
| `SECRET_KEY` | Django secret key | insecure dev default |
| `DEBUG` | Enable debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `INTERNAL_SERVICE_KEY` | Must match the recipe service's key | `dev-internal-key` |

> Never use the default `SECRET_KEY` or `INTERNAL_SERVICE_KEY` values in production.

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for deployment instructions.

For canary releases, use the scripts in `django-project/k8s/`:

```bash
./canary-deploy.sh 10        # deploy canary at 10% traffic
./canary-deploy.sh 25        # ramp up to 25%
./canary-promote.sh          # promote canary to stable
./canary-rollback.sh         # roll back if something goes wrong
```
