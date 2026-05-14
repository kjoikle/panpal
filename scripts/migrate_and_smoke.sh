#!/usr/bin/env bash
set -euo pipefail

# Simple script to run Django migrations and perform a small ORM smoke-test
# Usage:
#   DATABASE_URL=postgres://... ./scripts/migrate_and_smoke.sh
# If DATABASE_URL is not provided the project will use the default SQLite DB.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT_DIR/.venv"
PY="$VENV/bin/python"
MANAGE="$ROOT_DIR/django-project/manage.py"

if [ ! -x "$PY" ]; then
  echo "Virtualenv python not found at $PY"
  echo "Create a venv and install requirements:"
  echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

echo "Using python: $PY"

if [ -n "${DATABASE_URL-}" ]; then
  echo "DATABASE_URL is set; using provided database."
else
  echo "No DATABASE_URL set; using default (SQLite) for local dev."
fi

echo "Running migrations..."
"$PY" "$MANAGE" migrate --noinput

echo "Running ORM smoke-test: creating a test user, tag, recipe and a step (idempotent)"
"$PY" "$MANAGE" shell <<'PY'
from django.contrib.auth import get_user_model
from recipes.models import Tag, Recipe, Step
User = get_user_model()

# Create or get user
u, created = User.objects.get_or_create(username='smoketest', defaults={'email':'smoke@example.com'})
if created:
    u.set_password('smokepassword')
    u.save()

# Create or get a tag
t, _ = Tag.objects.get_or_create(name='smoke-test')

# Create or get a recipe
r, rc = Recipe.objects.get_or_create(title='Smoke Test Recipe', defaults={'description':'Created by smoke test', 'author':u})
r.tags.add(t)

# Create a step
Step.objects.get_or_create(recipe=r, step_number=1, defaults={'instruction_text':'Do the smoke test step.'})

from django.db import connection
def table_count():
  # Try information_schema (Postgres); if not available (SQLite), fall back to sqlite_master
  with connection.cursor() as cur:
    try:
      cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s;", ['public'])
      return cur.fetchone()[0]
    except Exception:
      cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
      return cur.fetchone()[0]

print('SMOKE_OK: counts -> users=%s tags=%s recipes=%s steps=%s tables=%s' % (
  User.objects.count(), Tag.objects.count(), Recipe.objects.count(), Step.objects.count(), table_count()))
PY

echo "Smoke test finished."
