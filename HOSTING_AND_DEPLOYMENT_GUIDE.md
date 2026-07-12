# Hosting & Deployment Guide - IGCSE AI Tutor

**Recommended Platform:** DigitalOcean  
**Target Scale:** 10-50 users (MVP phase)  
**Estimated Monthly Cost:** $20-40

---

## Executive Summary

The IGCSE AI Tutor application is ready for production deployment. This guide provides step-by-step instructions for deploying to DigitalOcean, the recommended hosting platform for the MVP phase.

### Why DigitalOcean?

| Factor | DigitalOcean | Heroku | AWS | Explanation |
|--------|--------------|--------|-----|-------------|
| **Cost** | $5-15/month | $50-100/month | Highly variable | DigitalOcean offers best value for small apps |
| **Ease** | Good (basic DevOps) | Easiest | Complex | DigitalOcean is beginner-friendly |
| **Scalability** | Easy to scale | Auto-scales | Unlimited | All can scale, DO most cost-efficient |
| **Control** | Full control | Limited | Full control | DO gives good balance of control/simplicity |
| **Recommended** | ✅ YES | ❌ Expensive | ❌ Complex | Best for MVP/early stage |

---

## Phase 1: Prepare for Deployment

### Step 1.1: Create DigitalOcean Account

1. Go to https://www.digitalocean.com/
2. Sign up with email address
3. Verify email
4. Add payment method (credit/debit card)
5. ✅ You'll get $200 free credits for 60 days (as of 2024)

### Step 1.2: Prepare Application Code

```bash
# Review checklist
cd C:\projects\agenticaitutor

# 1. Ensure all code is committed
git status

# 2. Create .gitignore (if not exists)
# Should ignore:
# - /mytutor/ (virtual environment)
# - /data/ (local database)
# - /.env (credentials)
# - __pycache__/
# - *.pyc

# 3. Check requirements.txt exists
ls requirements.txt

# 4. Verify config.py has environment variables
cat src/config.py
```

### Step 1.3: Create requirements.txt

```bash
# Export Python dependencies for production
.\mytutor\Scripts\pip.exe freeze > requirements.txt
```

**Critical Dependencies to Verify:**
- fastapi
- uvicorn
- sqlalchemy
- pydantic
- python-dotenv
- bcrypt
- aiofiles
- httpx

---

## Phase 2: Docker Containerization

### Step 2.1: Create Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8001

# Create data directory
RUN mkdir -p /app/data

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Step 2.2: Create .dockerignore

```
mytutor/
.git/
.gitignore
__pycache__/
*.pyc
*.pyo
.env
data/
.pytest_cache/
*.db
```

### Step 2.3: Test Docker Build Locally (Optional)

```bash
docker build -t igcse-tutor .
docker run -p 8001:8001 igcse-tutor
# Visit http://localhost:8001/health
```

---

## Phase 3: Database Setup

### Step 3.1: Choose Database

**Option A: SQLite (Current - Suitable for MVP)**
- Pros: Simple, no additional setup, file-based
- Cons: Single-user, limited concurrency
- Use for: Testing, MVP phase (up to ~50 users)

**Option B: PostgreSQL (Recommended for Scale)**
- Pros: Multi-user, better concurrency, production-standard
- Cons: Requires managed database service
- Cost: ~$15-30/month on DigitalOcean
- Use for: When scaling beyond 50 users

### For MVP (SQLite):
Keep current setup. Migrate data directory to persistent volume.

### For Production (PostgreSQL):
See instructions in "Scaling" section below.

---

## Phase 4: Environment Configuration

### Step 4.1: Create Production .env File

Create a new `.env.production` file (DO NOT commit to git):

```env
# Database
DATABASE_URL=sqlite:///./data/igcse_tutor.db
# Or for PostgreSQL:
# DATABASE_URL=postgresql://user:password@db_host:5432/igcse_tutor

# FastAPI
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-key-here-64-chars-min

# Email (Optional - for production)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password

# CORS
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# API Keys (if using external services)
OPENAI_API_KEY=your-key-here
```

### Step 4.2: Security Best Practices

- ✅ Use strong SECRET_KEY (at least 64 random characters)
- ✅ Enable HTTPS (DigitalOcean provides free SSL)
- ✅ Use environment variables for ALL secrets
- ✅ Rotate credentials regularly
- ✅ Never commit .env to git
- ✅ Use DigitalOcean App Platform's secret management

---

## Phase 5: Deployment to DigitalOcean

### Option A: DigitalOcean App Platform (Easiest)

This is the recommended approach - it handles most deployment details automatically.

#### Step 5A.1: Connect GitHub Repository

1. Log into DigitalOcean dashboard
2. Click "Create" → "Apps"
3. Select "GitHub"
4. Authorize DigitalOcean to access GitHub
5. Select your `agenticaitutor` repository
6. Choose branch: `master` or `main`

#### Step 5A.2: Configure App

1. **Service Name:** `igcse-tutor-api`
2. **Build Command:** `pip install -r requirements.txt`
3. **Run Command:** `uvicorn src.main:app --host 0.0.0.0 --port 8080`
4. **Port:** 8080 (DigitalOcean will expose as HTTPS)
5. **Instance Type:** Basic (shared CPU)
6. **Instance Count:** 1

#### Step 5A.3: Add Environment Variables

In the App Platform dashboard:
1. Click "Settings" → "Environment"
2. Add each variable from `.env.production`:
   - `ENVIRONMENT=production`
   - `DEBUG=false`
   - `SECRET_KEY=...`
   - `SMTP_HOST=smtp.gmail.com`
   - etc.

#### Step 5A.4: Set Up Database Volume

1. Click "Resources"
2. Click "Create a new Database"
3. Choose:
   - Type: PostgreSQL (for production) OR SQLite (for MVP)
   - Name: `igcse-tutor-db`
4. DigitalOcean automatically configures DATABASE_URL
5. ✅ Persists data across deployments

#### Step 5A.5: Deploy

1. Click "Deploy App"
2. Wait for deployment (~2-3 minutes)
3. DigitalOcean assigns you a URL: `https://igcse-tutor-api-xxxxx.ondigitalocean.app`
4. ✅ App is now live!

---

### Option B: Droplet Deployment (More Control)

For users who prefer traditional server setup.

#### Step 5B.1: Create Droplet

1. DigitalOcean Dashboard → "Create" → "Droplets"
2. Choose:
   - OS: Ubuntu 22.04 LTS
   - Size: Basic ($5-6/month for MVP)
   - Region: Closest to your users
   - Authentication: SSH key (recommended)

#### Step 5B.2: Connect via SSH

```bash
ssh root@your_droplet_ip
```

#### Step 5B.3: Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install Python 3.11
apt install python3.11 python3.11-venv python3-pip -y

# Install PostgreSQL (optional, for production database)
apt install postgresql postgresql-contrib -y

# Install Nginx (reverse proxy)
apt install nginx -y

# Install supervisor (process management)
apt install supervisor -y

# Install git
apt install git -y
```

#### Step 5B.4: Clone Repository

```bash
cd /home
git clone https://github.com/yourusername/agenticaitutor.git
cd agenticaitutor
```

#### Step 5B.5: Set Up Python Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Step 5B.6: Configure Environment

```bash
# Create .env file with production settings
nano .env

# Add content from Step 4.1 above
# Ctrl+O → Enter → Ctrl+X to save
```

#### Step 5B.7: Configure Supervisor

Create `/etc/supervisor/conf.d/igcse-tutor.conf`:

```ini
[program:igcse-tutor]
directory=/home/agenticaitutor
command=/home/agenticaitutor/venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8001
autostart=true
autorestart=true
stderr_logfile=/var/log/igcse-tutor.err.log
stdout_logfile=/var/log/igcse-tutor.out.log
user=root
```

Then:
```bash
supervisorctl reread
supervisorctl update
supervisorctl start igcse-tutor
```

#### Step 5B.8: Configure Nginx

Create `/etc/nginx/sites-available/igcse-tutor`:

```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Then:
```bash
ln -s /etc/nginx/sites-available/igcse-tutor /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

#### Step 5B.9: Enable HTTPS with Let's Encrypt

```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d your_domain.com
# Follow prompts to get free SSL certificate
```

---

## Phase 6: Post-Deployment Verification

### Checklist

- [ ] Application is running (Health check: `GET /health` returns `{"status":"healthy"}`)
- [ ] Dashboard loads (GET `/dashboard` returns HTML)
- [ ] Database is persisted (data survives restart)
- [ ] HTTPS is enabled (padlock in browser)
- [ ] Email works (test notification sending)
- [ ] Admin dashboard accessible (login works)
- [ ] Logs are accessible (for debugging)
- [ ] Backups are configured

### Testing After Deployment

```bash
# Test health endpoint
curl https://your-app.ondigitalocean.app/health

# Test dashboard
curl -I https://your-app.ondigitalocean.app/dashboard

# Check logs (DigitalOcean App Platform)
# Dashboard → Logs tab

# Check logs (Droplet)
tail -f /var/log/igcse-tutor.out.log
```

---

## Phase 7: Monitoring & Maintenance

### Recommended Monitoring

1. **DigitalOcean Monitoring**
   - CPU usage
   - Memory usage
   - Disk space
   - Network traffic
   - Uptime checks

2. **Application Logging**
   - Track errors and warnings
   - Monitor API response times
   - Alert on injection attempts

3. **Database Monitoring**
   - Query performance
   - Backup status
   - Connection count

### Maintenance Tasks

**Daily:**
- Monitor uptime
- Check error logs
- Verify backups

**Weekly:**
- Review security logs for attacks
- Check disk usage
- Update security patches

**Monthly:**
- Database maintenance
- Performance review
- User statistics review

---

## Phase 8: Scaling Beyond MVP

### When to Scale

Scale from SQLite to PostgreSQL when:
- User base exceeds 50 active users
- Concurrent requests exceed 5 simultaneous
- Database file size exceeds 100MB
- Response times degrade

### Scaling Steps

1. **Migrate Database**
   ```bash
   # Export SQLite to PostgreSQL
   # (Tools available online for this)
   ```

2. **Update DATABASE_URL**
   ```env
   DATABASE_URL=postgresql://user:password@db_host:5432/igcse_tutor
   ```

3. **Increase App Instance Count**
   - DigitalOcean App Platform: "Scale" → increase instances to 2-3
   - Droplet: Use load balancer in front of multiple app instances

4. **Add CDN for Static Files**
   - DigitalOcean Spaces (S3-compatible)
   - CloudFlare (free tier available)

5. **Database Replication**
   - Set up read replicas for reporting queries
   - Automatic failover for high availability

---

## Cost Breakdown

### MVP Phase (DigitalOcean App Platform)

| Component | Cost | Notes |
|-----------|------|-------|
| App Platform | $5-12/month | Shared CPU, 512MB RAM |
| Database | $0/month | SQLite (file-based) |
| Storage | $0.20/GB | For data volume |
| **Total** | **$5-15/month** | **Includes free SSL/HTTPS** |

### Production Phase (with PostgreSQL)

| Component | Cost | Notes |
|-----------|------|-------|
| App Platform | $12-25/month | Scales with traffic |
| PostgreSQL | $15-60/month | Managed database |
| Storage | $1-5/month | 100GB database |
| Backups | $1-3/month | Automatic daily |
| **Total** | **$30-95/month** | **For 100-500 users** |

---

## Troubleshooting

### Application Not Starting

```bash
# Check logs
DigitalOcean Dashboard → Apps → Logs

# Common issues:
# 1. Missing dependencies: pip install -r requirements.txt
# 2. Database not initialized: src/database/db_init.py runs on startup
# 3. Port already in use: Change to 8080
```

### Database Connection Issues

```bash
# Test connection
psql postgresql://user:password@host:5432/dbname

# Check DATABASE_URL environment variable
echo $DATABASE_URL
```

### Performance Issues

```bash
# Check CPU/Memory in DigitalOcean monitoring
# If CPU > 80%: Upgrade instance size
# If Memory > 90%: Check for memory leaks in logs

# Check application metrics
GET /health (should be < 100ms)
```

---

## Next Steps

1. **Immediate:**
   - [ ] Create DigitalOcean account
   - [ ] Set up GitHub integration
   - [ ] Deploy app
   - [ ] Test endpoints
   - [ ] Verify database

2. **Within 1 week:**
   - [ ] Configure custom domain
   - [ ] Set up monitoring
   - [ ] Enable SSL certificate
   - [ ] Create backup plan

3. **Before user launch:**
   - [ ] Test end-to-end flows
   - [ ] Configure email (SMTP)
   - [ ] Set up admin access
   - [ ] Document for support team

4. **Post-launch:**
   - [ ] Monitor performance
   - [ ] Gather user feedback
   - [ ] Plan scaling if needed
   - [ ] Implement subscription system

---

## Support & Resources

### DigitalOcean Documentation
- App Platform: https://docs.digitalocean.com/products/app-platform/
- Droplets: https://docs.digitalocean.com/products/droplets/
- Databases: https://docs.digitalocean.com/products/databases/

### FastAPI Deployment
- FastAPI Docs: https://fastapi.tiangolo.com/deployment/

### Python Production
- Gunicorn: https://gunicorn.org/ (alternative to uvicorn)
- Poetry: https://python-poetry.org/ (dependency management)

---

## Summary

The IGCSE AI Tutor is ready for production deployment. **DigitalOcean App Platform is the recommended hosting solution** for the MVP phase, offering:

✅ Easy deployment from GitHub  
✅ Automatic SSL/HTTPS  
✅ Affordable pricing ($5-15/month)  
✅ Scalable architecture  
✅ Built-in monitoring  
✅ $200 free credit for 60 days  

**Estimated time to deployment:** 15-30 minutes  
**Technical complexity:** Low (App Platform) to Medium (Droplet)  

Ready to deploy! 🚀

