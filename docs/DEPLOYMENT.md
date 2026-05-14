# Deploying to Render

This guide walks you through deploying your Django recipe app to Render.

## Prerequisites

1. A GitHub account with your code pushed to a repository
2. A Render account (sign up at [render.com](https://render.com))

## Step-by-Step Deployment

### 1. Prepare Your Repository

Make sure all your changes are committed and pushed to GitHub:

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main  # or your branch name
```

### 2. Create a PostgreSQL Database on Render

1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"PostgreSQL"**
3. Configure the database:
   - **Name**: `recipeapp-db` (or your preferred name)
   - **Database**: `recipeapp_db`
   - **User**: Leave default or customize
   - **Region**: Choose closest to your users
   - **PostgreSQL Version**: Latest stable
   - **Plan**: Free tier is fine for development
4. Click **"Create Database"**
5. Wait for the database to be provisioned (takes 1-2 minutes)
6. **Important**: Note the **Internal Database URL** - you'll need this later

### 3. Create a Web Service on Render

1. In Render Dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository:
   - Click **"Connect account"** if not already connected
   - Select your repository
   - Click **"Connect"**
3. Configure the service:
   - **Name**: `recipeapp` (or your preferred name)
   - **Region**: Same as your database
   - **Branch**: `main` (or your deployment branch)
   - **Root Directory**: Leave empty (root of repo)
   - **Runtime**: `Python 3`
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt && cd django-project && python manage.py collectstatic --noinput && python manage.py migrate
     ```
   - **Start Command**: 
     ```bash
     cd django-project && gunicorn recipeapp.wsgi --bind 0.0.0.0:$PORT
     ```
   - **Plan**: Free tier is fine for development

### 4. Configure Environment Variables

In your Web Service settings, add these environment variables:

1. Click on your Web Service → **"Environment"** tab
2. Add the following variables:

   | Key | Value | Notes |
   |-----|-------|-------|
   | `SECRET_KEY` | Generate a new key | See below for how to generate |
   | `DEBUG` | `False` | Always False in production |
   | `ALLOWED_HOSTS` | `your-app-name.onrender.com` | Replace with your actual Render URL |
   | `DATABASE_URL` | (Auto-filled) | Render automatically provides this from your PostgreSQL service |

   **To generate SECRET_KEY:**
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

3. **Link the Database:**
   - Scroll down to **"Add Environment Variable"**
   - Click **"Link Database"**
   - Select your PostgreSQL database
   - This automatically sets `DATABASE_URL`

### 5. Deploy

1. Click **"Save Changes"** in the Environment tab
2. Go to the **"Manual Deploy"** section (or Render will auto-deploy)
3. Click **"Deploy latest commit"**
4. Wait for the build to complete (5-10 minutes on first deploy)

### 6. Verify Deployment

1. Once deployment is complete, click on your service URL
2. You should see your recipe app homepage
3. Test creating a recipe, viewing recipes, etc.

## Troubleshooting

### Build Fails

- **Check build logs**: Click on your service → "Logs" tab
- **Common issues**:
  - Missing dependencies in `requirements.txt`
  - Python version mismatch
  - Static files collection errors

### Database Connection Errors

- Verify `DATABASE_URL` is set correctly
- Ensure database is linked to your web service
- Check that migrations ran successfully

### Static Files Not Loading

- Verify `collectstatic` ran in build command
- Check that `STATIC_ROOT` is set in `settings.py`
- Ensure WhiteNoise middleware is configured

### 500 Internal Server Error

- Check application logs in Render dashboard
- Verify `DEBUG=False` and `ALLOWED_HOSTS` includes your Render URL
- Ensure `SECRET_KEY` is set

### View Logs

- **Build logs**: Service → "Logs" tab → "Build Logs"
- **Runtime logs**: Service → "Logs" tab → "Live Logs"

## Post-Deployment

### Create a Superuser

To access Django admin, create a superuser:

1. In Render Dashboard, go to your Web Service
2. Click **"Shell"** tab
3. Run:
   ```bash
   cd django-project
   python manage.py createsuperuser
   ```
4. Follow prompts to create admin user
5. Access admin at: `https://your-app.onrender.com/admin/`

### Seed Initial Data (Optional)

If you want to populate the database with sample recipes:

1. Open Shell in Render Dashboard
2. Run:
   ```bash
   cd django-project
   python seed_data.py
   ```

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Django secret key (generate new for production) |
| `DEBUG` | Yes | Set to `False` in production |
| `ALLOWED_HOSTS` | Yes | Comma-separated list of allowed domains |
| `DATABASE_URL` | Yes | Automatically provided by Render when database is linked |

## Cost Notes

- **Free Tier**: 
  - Web services spin down after 15 minutes of inactivity
  - Database has 90-day retention limit
  - Good for development/testing
- **Paid Plans**: 
  - Always-on services
  - Better performance
  - No spin-down delays

## Additional Resources

- [Render Django Documentation](https://render.com/docs/deploy-django)
- [Render Environment Variables](https://render.com/docs/environment-variables)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)

