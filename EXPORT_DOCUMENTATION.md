# GroVELLOWS - Export & Deployment Documentation

## 📱 Application Overview

**GroVELLOWS** is an internal German Construction Tender Tracking mobile application built with:
- **Frontend**: Expo React Native (Cross-platform mobile app)
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Theme**: Primary #143250, Secondary #A07D50, Font: Avenir Next LT Pro

---

## 📦 Exporting from Emergent

### Step 1: Export Code to GitHub

1. **From Emergent Dashboard:**
   - Navigate to your project
   - Click on "Save to GitHub" button
   - Authorize Emergent to access your GitHub account
   - Select organization/account
   - Create new repository or select existing one
   - Name it: `grovellows-tender-tracker`
   - Push all code

2. **What Gets Exported:**
   ```
   /
   ├── backend/          # FastAPI server
   │   ├── server.py     # Main API file
   │   ├── requirements.txt
   │   └── .env          # Environment variables (template)
   ├── frontend/         # Expo React Native app
   │   ├── app/          # Screens and navigation
   │   ├── components/   # Reusable components
   │   ├── utils/        # Helper functions
   │   ├── contexts/     # Auth & state management
   │   ├── package.json
   │   └── app.json      # Expo configuration
   └── README.md
   ```

---

## 🚀 Self-Hosting Options

### Option A: Cloud Hosting (Recommended for Production)

#### **Backend Hosting:**

**AWS / DigitalOcean / Azure:**

1. **Setup Server:**
   ```bash
   # SSH into your server
   ssh your-server

   # Install dependencies
   sudo apt update
   sudo apt install python3.11 python3-pip mongodb

   # Clone your repo
   git clone https://github.com/your-org/grovellows-tender-tracker.git
   cd grovellows-tender-tracker/backend
   ```

2. **Install Python Dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Configure Environment:**
   ```bash
   # Edit .env file
   nano .env
   ```

   Add:
   ```env
   MONGO_URL=mongodb://localhost:27017
   DB_NAME=grovellows_production
   SECRET_KEY=your-super-secret-key-change-this
   ```

4. **Run with Systemd:**
   ```bash
   sudo nano /etc/systemd/system/grovellows-backend.service
   ```

   Content:
   ```ini
   [Unit]
   Description=GroVELLOWS Backend API
   After=network.target

   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/path/to/grovellows-tender-tracker/backend
   ExecStart=/usr/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8001
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Enable service:
   ```bash
   sudo systemctl enable grovellows-backend
   sudo systemctl start grovellows-backend
   ```

5. **Setup Nginx Reverse Proxy:**
   ```bash
   sudo apt install nginx
   sudo nano /etc/nginx/sites-available/grovellows
   ```

   Content:
   ```nginx
   server {
       listen 80;
       server_name api.grovellows.your-company.com;

       location / {
           proxy_pass http://localhost:8001;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

   Enable:
   ```bash
   sudo ln -s /etc/nginx/sites-available/grovellows /etc/nginx/sites-enabled/
   sudo systemctl restart nginx
   ```

#### **Frontend Hosting:**

**Option 1: Build Native Apps (Recommended for Internal Use)**

1. **Build for Android:**
   ```bash
   cd frontend
   eas build --platform android
   ```

2. **Build for iOS:**
   ```bash
   eas build --platform ios
   ```

3. **Distribute:**
   - **Internal Distribution**: Use EAS Build for internal testing
   - **App Stores**: Publish to Google Play / Apple App Store
   - **Enterprise Distribution**: Use your company's enterprise certificates

**Option 2: Expo Go Development**
   - Keep using Expo Go for rapid testing
   - Share QR code with team members

---

### Option B: Docker Deployment (Easier Management)

1. **Create Dockerfile for Backend:**

   `backend/Dockerfile`:
   ```dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY . .

   EXPOSE 8001

   CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
   ```

2. **Create docker-compose.yml:**

   ```yaml
   version: '3.8'

   services:
     mongodb:
       image: mongo:7
       container_name: grovellows-db
       ports:
         - "27017:27017"
       volumes:
         - mongo-data:/data/db
       environment:
         MONGO_INITDB_DATABASE: grovellows_production

     backend:
       build: ./backend
       container_name: grovellows-api
       ports:
         - "8001:8001"
       depends_on:
         - mongodb
       environment:
         - MONGO_URL=mongodb://mongodb:27017
         - DB_NAME=grovellows_production
         - SECRET_KEY=your-secret-key

   volumes:
     mongo-data:
   ```

3. **Deploy:**
   ```bash
   docker-compose up -d
   ```

---

## 🔧 Configuration for Production

### 1. Update API URL in Frontend

`frontend/.env`:
```env
EXPO_PUBLIC_BACKEND_URL=https://api.grovellows.your-company.com
```

### 2. Secure Your Backend

- Change SECRET_KEY in `.env`
- Enable HTTPS with SSL certificate (Let's Encrypt)
- Configure CORS properly for your domain
- Set up MongoDB authentication

### 3. Environment Variables

**Backend (`backend/.env`):**
```env
MONGO_URL=mongodb://username:password@localhost:27017
DB_NAME=grovellows_production
SECRET_KEY=generate-strong-random-key-here
```

**Frontend (`frontend/.env`):**
```env
EXPO_PUBLIC_BACKEND_URL=https://api.grovellows.your-company.com
```

---

## 📱 Building Mobile Apps

### For Android:

1. **Install EAS CLI:**
   ```bash
   npm install -g eas-cli
   ```

2. **Login to Expo:**
   ```bash
   eas login
   ```

3. **Configure Build:**
   ```bash
   cd frontend
   eas build:configure
   ```

4. **Build APK:**
   ```bash
   eas build --platform android --profile production
   ```

5. **Download and distribute** APK to your team

### For iOS:

1. **Requirements:**
   - Apple Developer Account ($99/year)
   - iOS Enterprise Program (for internal distribution)

2. **Build:**
   ```bash
   eas build --platform ios --profile production
   ```

3. **Distribute:**
   - TestFlight (for internal testing)
   - Enterprise distribution
   - App Store (if public)

---

## 🔐 Security Checklist

- [ ] Change all default passwords
- [ ] Generate new SECRET_KEY
- [ ] Enable MongoDB authentication
- [ ] Configure firewall rules
- [ ] Set up HTTPS/SSL
- [ ] Review CORS settings
- [ ] Implement rate limiting
- [ ] Set up backup strategy
- [ ] Configure monitoring and logging

---

## 🗄️ Database Backup

### Automated MongoDB Backup:

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/mongodb"

mongodump --db grovellows_production --out $BACKUP_DIR/$DATE

# Keep only last 7 days
find $BACKUP_DIR -type d -mtime +7 -exec rm -rf {} +
```

Schedule with cron:
```bash
0 2 * * * /path/to/backup.sh
```

---

## 📊 Monitoring & Maintenance

### 1. Application Monitoring

- **Backend**: Use pm2 or systemd for process management
- **Logs**: Centralize logs with tools like Logstash or CloudWatch
- **Uptime**: Set up monitoring with UptimeRobot or Pingdom

### 2. Database Maintenance

```bash
# Check database status
mongo grovellows_production --eval "db.stats()"

# Optimize database
mongo grovellows_production --eval "db.runCommand({compact: 'tenders'})"
```

---

## 🔄 Updating the Application

### Backend Updates:

```bash
cd /path/to/grovellows-tender-tracker
git pull origin main
cd backend
pip install -r requirements.txt
sudo systemctl restart grovellows-backend
```

### Frontend Updates:

```bash
cd frontend
git pull origin main
npm install
# Rebuild app
eas build --platform all
```

---

## 💡 Cost Estimates (Self-Hosting)

### Monthly Costs:

| Service | Provider | Cost |
|---------|----------|------|
| Server (2GB RAM) | DigitalOcean | $12/month |
| Database | Included | $0 |
| SSL Certificate | Let's Encrypt | Free |
| Domain | Namecheap | $10/year |
| **Total** | | **~$12/month** |

### One-Time Costs:

| Item | Cost |
|------|------|
| Apple Developer | $99/year (if iOS) |
| Initial Setup Time | 4-8 hours |

---

## 🆘 Troubleshooting

### Backend Won't Start:

```bash
# Check logs
sudo journalctl -u grovellows-backend -f

# Check if port is in use
sudo lsof -i :8001

# Verify MongoDB is running
sudo systemctl status mongodb
```

### Frontend Build Fails:

```bash
# Clear cache
cd frontend
rm -rf node_modules
npm install

# Update Expo
npm install expo@latest
```

### Database Connection Issues:

```bash
# Test MongoDB connection
mongo --host localhost --port 27017

# Check MongoDB logs
sudo tail -f /var/log/mongodb/mongod.log
```

---

## 📞 Support

For issues or questions after export:

1. **Check logs** first
2. **Review this documentation**
3. **Search GitHub Issues** in your repository
4. **Contact your internal dev team**

---

## ✅ Pre-Export Checklist

- [ ] All features tested and working
- [ ] GDPR compliance verified
- [ ] Sample data removed or replaced with real data
- [ ] Environment variables documented
- [ ] Backup strategy planned
- [ ] Team trained on using the app
- [ ] Server infrastructure ready
- [ ] Domain configured
- [ ] SSL certificate obtained

---

## 🎉 You're Ready!

Your GroVELLOWS app is now fully portable and ready for self-hosting. You own all the code and can deploy it anywhere you choose.

**Next Steps:**
1. Export to GitHub
2. Choose hosting provider
3. Follow deployment guide above
4. Set up monitoring
5. Train your team
6. Start tracking German construction tenders!

---

*Document Version: 1.0*  
*Last Updated: January 2026*  
*App Version: GroVELLOWS v1.0*
