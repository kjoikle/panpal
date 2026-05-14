# Render Deployment Checklist

## ✅ Pre-Deployment Steps Completed

### 1. Settings Configuration
- ✅ WhiteNoise middleware added to `settings.py`
- ✅ STATIC_ROOT configured
- ✅ STATICFILES_STORAGE set to WhiteNoise
- ✅ ALLOWED_HOSTS uses environment variables
- ✅ DATABASE_URL handling configured
- ✅ DEBUG uses environment variable

### 2. Configuration Files
- ✅ `Procfile` exists and uses `$PORT` variable
- ✅ `requirements.txt` includes all dependencies:
  - Django>=4.2,<5.0
  - psycopg2-binary>=2.9.0
  - python-dotenv>=1.0.0
  - dj-database-url>=1.0.0
  - gunicorn>=20.1.0
  - whitenoise>=6.0.0
- ✅ `render.yaml` created for infrastructure-as-code

### 3. Static Files
- ✅ Static files configuration verified
- ✅ collectstatic command tested

## 📋 Manual Steps to Complete on Render

### Step 1: Push Code to GitHub
```bash
git add .
git commit -m "feat: prepare for Render deployment"
git push origin main
```

### Step 2: Create PostgreSQL Database on Render
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name**: `recipeapp-db`
   - **Database**: `recipeapp_db`
   - **User**: `recipeapp_user` (or default)
   - **Region**: Choose closest to you (e.g., Oregon)
   - **Plan**: Free (for development)
4. Click **"Create Database"**
5. Wait for provisioning (1-2 minutes)

### Step 3: Create Web Service on Render

#### Option A: Using render.yaml (Recommended)
1. Go to Render Dashboard
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository
4. Render will automatically detect `render.yaml` and create services
5. Review and confirm the configuration

#### Option B: Manual Setup
1. Go to Render Dashboard
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `recipeapp`
   - **Region**: Same as database
   - **Branch**: `main`
   - **Root Directory**: (leave empty)
   - **Runtime**: `Python 3`
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt && cd django-project && python manage.py collectstatic --noinput && python manage.py migrate
     ```
   - **Start Command**: 
     ```bash
     cd django-project && gunicorn recipeapp.wsgi:application --bind 0.0.0.0:$PORT
     ```

### Step 4: Configure Environment Variables

In your Web Service → **Environment** tab, add:

| Key | Value | Notes |
|-----|-------|-------|
| `SECRET_KEY` | (Generate new key) | See below |
| `DEBUG` | `False` | Always False in production |
| `ALLOWED_HOSTS` | `your-app-name.onrender.com` | Replace with your actual Render URL |
| `DATABASE_URL` | (Auto-filled) | Automatically set when you link database |

**To generate SECRET_KEY:**
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Link Database:**
1. In Environment tab, scroll to **"Add Environment Variable"**
2. Click **"Link Database"**
3. Select `recipeapp-db`
4. This automatically sets `DATABASE_URL`

### Step 5: Deploy

1. Click **"Save Changes"** in Environment tab
2. Render will automatically start deploying
3. Monitor the build logs in the **"Logs"** tab
4. Wait for deployment to complete (5-10 minutes first time)

### Step 6: Post-Deployment

#### Create Superuser
1. Go to your Web Service → **"Shell"** tab
2. Run:
   ```bash
   cd django-project
   python manage.py createsuperuser
   ```
3. Follow prompts to create admin account
4. Access admin at: `https://your-app.onrender.com/admin/`

#### Verify Deployment
- ✅ Homepage loads: `https://your-app.onrender.com/`
- ✅ Static files load (CSS, images)
- ✅ Database connection works
- ✅ Admin panel accessible
- ✅ Can create/view recipes

## 🔍 Troubleshooting

### Build Fails
- Check build logs in Render Dashboard → Logs tab
- Verify all dependencies in `requirements.txt`
- Ensure Python version matches (3.11.0 in render.yaml)

### Static Files Not Loading
- Verify `collectstatic` ran in build logs
- Check WhiteNoise middleware is in settings.py
- Ensure STATIC_ROOT is set correctly

### Database Connection Errors
- Verify DATABASE_URL is set (should be auto-filled)
- Check database is linked to web service
- Ensure migrations ran successfully

### 500 Internal Server Error
- Check runtime logs in Render Dashboard
- Verify DEBUG=False and ALLOWED_HOSTS includes your URL
- Ensure SECRET_KEY is set

## 📝 Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `SECRET_KEY` | Yes | Django secret key | (auto-generated) |
| `DEBUG` | Yes | Debug mode | `False` |
| `ALLOWED_HOSTS` | Yes | Allowed domains | `recipeapp.onrender.com` |
| `DATABASE_URL` | Yes | Database connection | (auto-filled by Render) |
| `PYTHON_VERSION` | Optional | Python version | `3.11.0` |

## 🎯 Next Steps After Deployment

1. Test all functionality on production
2. Set up custom domain (optional)
3. Configure email settings (if needed)
4. Set up monitoring/error tracking (optional)
5. Review and optimize performance

## 📚 Resources

- [Render Django Documentation](https://render.com/docs/deploy-django)
- [Render Environment Variables](https://render.com/docs/environment-variables)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)

