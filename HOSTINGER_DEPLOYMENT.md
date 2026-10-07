# HBC Django Site - Hostinger Deployment Guide

## Prerequisites
- Hostinger account with SSH access enabled
- Domain or Hostinger subdomain
- MySQL database created in Hostinger panel

## Step-by-Step Deployment

### 1. Clone Repository on Hostinger Server

```bash
# SSH into your Hostinger account
ssh username@your-hostinger-server.com

# Navigate to public_html or your desired directory
cd public_html

# Clone the repository
git clone https://github.com/OgalTom/HBC-DJANGO_SITE.git
cd HBC-DJANGO_SITE
```

### 2. Create Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install required packages
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Hostinger credentials
nano .env
```

**Important values to update in .env:**
- `DJANGO_SECRET_KEY` - Generate a secure key: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- `DB_NAME` - Your Hostinger MySQL database name
- `DB_USER` - Your Hostinger MySQL username
- `DB_PASSWORD` - Your Hostinger MySQL password
- `DB_HOST` - Usually `localhost` or your Hostinger MySQL host
- `ALLOWED_HOSTS` - Your domain (e.g., `yourdomain.com,www.yourdomain.com`)
- `DEBUG=False` - Always False in production

### 5. Create MySQL Database (if not already created)

In Hostinger control panel:
1. Go to Databases → MySQL
2. Create new database
3. Create database user
4. Grant all privileges to that database

### 6. Run Django Migrations

```bash
cd job
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

### 7. Create Superuser (Admin Account)

```bash
python manage.py createsuperuser
# Follow prompts to create admin account
```

### 8. Configure Web Server (Apache/Nginx)

#### For Apache (Most common on Hostinger):

1. Go to Hostinger control panel → Public_html
2. Create `.htaccess` file in your app root:

```apache
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteBase /
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    RewriteRule ^(.*)$ /index.html [L]
</IfModule>
```

2. Update `.htaccess` to route to WSGI:

```apache
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteBase /
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    RewriteRule ^(.*)$ wsgi.py/$1 [L]
</IfModule>
```

#### Alternative: Use Gunicorn with Supervisor

1. Install Supervisor:
```bash
pip install supervisor
```

2. Create supervisor config file:
```bash
sudo nano /etc/supervisor/conf.d/hbc_django.conf
```

Content:
```ini
[program:hbc_django]
directory=/path/to/HBC-DJANGO_SITE/job
command=/path/to/HBC-DJANGO_SITE/venv/bin/gunicorn job.wsgi:application --bind 127.0.0.1:8000
autostart=true
autorestart=true
stderr_logfile=/var/log/hbc_django.err.log
stdout_logfile=/var/log/hbc_django.out.log
```

3. Start supervisor:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start hbc_django
```

### 9. Configure Static & Media Files

In Hostinger control panel:
1. Go to File Manager
2. Create `staticfiles` and `media` folders in your project root
3. Set permissions to 755

### 10. Test Deployment

```bash
# Test with development server
cd job
python manage.py runserver 0.0.0.0:8000

# Visit: http://your-domain:8000
```

### 11. Enable HTTPS

1. Go to Hostinger control panel → SSL/TLS
2. Install Free SSL (Let's Encrypt)
3. Update `ALLOWED_HOSTS` in `.env` to include both www and non-www versions

### 12. Set Up Cron Jobs (Optional)

For scheduled tasks, add to Hostinger Cron Jobs:

```bash
# Run every day at 2 AM
0 2 * * * cd /path/to/HBC-DJANGO_SITE/job && /path/to/venv/bin/python manage.py maintenance_task
```

## Troubleshooting

### 500 Internal Server Error
```bash
# Check error logs
tail -f /path/to/HBC-DJANGO_SITE/error.log

# Check Django logs
cd job && python manage.py shell
```

### Database Connection Error
```bash
# Test MySQL connection
mysql -h localhost -u your_user -p your_database
```

### Static Files Not Loading
```bash
# Re-collect static files
python manage.py collectstatic --noinput --clear
```

### Permission Denied Errors
```bash
# Fix permissions
chmod -R 755 /path/to/HBC-DJANGO_SITE
chmod -R 777 /path/to/HBC-DJANGO_SITE/media
chmod -R 777 /path/to/HBC-DJANGO_SITE/staticfiles
```

## Environment Variables Reference

| Variable | Purpose | Example |
|----------|---------|---------|
| `DEBUG` | Debug mode (False in production) | `False` |
| `DJANGO_SECRET_KEY` | Django secret key | `random-secret-key` |
| `DB_NAME` | MySQL database name | `hbc_django_db` |
| `DB_USER` | MySQL username | `hbc_user` |
| `DB_PASSWORD` | MySQL password | `SecurePassword123` |
| `DB_HOST` | MySQL host | `localhost` |
| `ALLOWED_HOSTS` | Allowed domain names | `yourdomain.com,www.yourdomain.com` |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth client ID | `xxx.apps.googleusercontent.com` |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth secret | `xxx` |
| `GOOGLE_OAUTH_REDIRECT_URI` | Google OAuth callback URL | `https://yourdomain.com/auth/google/callback` |

## Admin Access

After deployment, access admin panel:
```
https://yourdomain.com/admin/
```

Use the superuser credentials created in Step 7.

## Support

For Hostinger-specific issues:
- Hostinger Help Center: https://support.hostinger.com
- Django Documentation: https://docs.djangoproject.com
