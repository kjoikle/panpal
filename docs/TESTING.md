# Testing Documentation

## Overview

This document describes the test suite for the Django recipe app, including deployment configuration tests.

## Test Structure

Tests are organized in the `recipes/tests/` directory:

```
recipes/tests/
├── __init__.py
├── test_deployment.py    # Deployment configuration tests
└── test_models.py        # Model and integration tests (if exists)
```

## Running Tests

### Run All Tests
```bash
cd django-project
python manage.py test
```

### Run Deployment Tests Only
```bash
cd django-project
python manage.py test recipes.tests.test_deployment
```

### Run with Verbosity
```bash
python manage.py test recipes.tests.test_deployment --verbosity=2
```

## Deployment Configuration Tests

The `test_deployment.py` file contains comprehensive tests to verify the application is properly configured for deployment on Render.

### Test Classes

#### 1. DeploymentSettingsTestCase
Tests deployment-related settings:
- ✅ WhiteNoise middleware configuration
- ✅ Static files storage configuration
- ✅ STATIC_ROOT and STATIC_URL settings
- ✅ ALLOWED_HOSTS environment variable support
- ✅ DEBUG environment variable support
- ✅ SECRET_KEY configuration

**Key Tests:**
- `test_whitenoise_middleware_configured()` - Verifies WhiteNoise is in MIDDLEWARE
- `test_static_files_storage_configured()` - Verifies WhiteNoise storage is set
- `test_static_root_configured()` - Verifies STATIC_ROOT is configured

#### 2. DatabaseConfigurationTestCase
Tests database configuration:
- ✅ Database configuration exists
- ✅ Database engine is set correctly
- ✅ PostgreSQL configuration structure
- ✅ DATABASE_URL environment variable handling

**Key Tests:**
- `test_database_configuration_exists()` - Verifies DATABASES setting exists
- `test_database_engine_configured()` - Verifies engine is PostgreSQL or SQLite
- `test_database_url_handling()` - Verifies DATABASE_URL support

#### 3. StaticFilesCollectionTestCase
Tests static files collection:
- ✅ collectstatic command availability
- ✅ Static files finders configuration

**Key Tests:**
- `test_collectstatic_command_exists()` - Verifies collectstatic command is available
- `test_staticfiles_finders_configured()` - Verifies finders are configured

#### 4. EnvironmentVariablesTestCase
Tests environment variable handling:
- ✅ DATABASE_URL support
- ✅ DEBUG environment variable support
- ✅ ALLOWED_HOSTS environment variable support

**Key Tests:**
- `test_database_url_environment_variable_supported()` - Tests DATABASE_URL handling
- `test_debug_environment_variable_supported()` - Tests DEBUG handling
- `test_allowed_hosts_environment_variable_supported()` - Tests ALLOWED_HOSTS handling

#### 5. ProductionReadinessTestCase
Tests production readiness:
- ✅ Required apps installed
- ✅ Security middleware included
- ✅ CSRF protection enabled
- ✅ Timezone configuration

**Key Tests:**
- `test_installed_apps_include_required()` - Verifies required apps
- `test_middleware_includes_security()` - Verifies security middleware
- `test_csrf_middleware_included()` - Verifies CSRF protection
- `test_timezone_configured()` - Verifies timezone settings

## Test Results

All 20 deployment tests should pass:

```
Ran 20 tests in 0.228s

OK
```

## What These Tests Verify

### ✅ Deployment Configuration
- WhiteNoise middleware is properly configured for static file serving
- Static files storage is set to WhiteNoise
- STATIC_ROOT is configured for collectstatic

### ✅ Environment Variables
- Settings can read from environment variables
- DATABASE_URL is supported (for Render)
- DEBUG and ALLOWED_HOSTS can be set via environment

### ✅ Production Readiness
- Security middleware is enabled
- CSRF protection is enabled
- Required apps are installed
- Timezone is configured

### ✅ Database Configuration
- Database settings are properly structured
- Supports both PostgreSQL and SQLite
- Handles DATABASE_URL from Render

## Continuous Integration

These tests should be run:
1. **Before deployment** - Verify configuration is correct
2. **In CI/CD pipeline** - Automatically test on every commit
3. **After configuration changes** - Ensure nothing broke

## Adding New Tests

When adding new deployment-related features:

1. Add tests to the appropriate test class in `test_deployment.py`
2. Follow the naming convention: `test_<feature_name>`
3. Include a docstring explaining what is being tested
4. Run tests to ensure they pass: `python manage.py test recipes.tests.test_deployment`

## Troubleshooting

### Tests Fail Locally
- Some tests may fail if whitenoise is not installed locally
- This is expected - tests verify configuration, not runtime behavior
- Tests will pass in production where whitenoise is installed

### Import Errors
- Ensure you're running tests from the `django-project` directory
- Verify all dependencies are installed: `pip install -r requirements.txt`

### Database Errors
- Tests use a separate test database
- No need to configure production database for tests
- Test database is created and destroyed automatically

## Related Documentation

- `DEPLOYMENT_CHANGES.md` - Details of deployment configuration changes
- `RENDER_DEPLOYMENT_CHECKLIST.md` - Step-by-step deployment guide
- `DEPLOYMENT.md` - Detailed deployment documentation

