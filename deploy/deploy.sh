#!/bin/bash

# Link Shortener Deployment Script
# Run this on your Oracle Cloud VM

set -e

echo "======================================"
echo "Link Shortener Deployment Script"
echo "======================================"

# Variables
APP_DIR="/home/ubuntu/link-shortener"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running as ubuntu user
if [ "$(whoami)" != "ubuntu" ]; then
    print_error "Please run this script as the ubuntu user"
    exit 1
fi

echo ""
echo "Step 1: Setting up directories..."
mkdir -p $APP_DIR
print_status "Directories created"

echo ""
echo "Step 2: Setting up Python virtual environment..."
cd $BACKEND_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
print_status "Python dependencies installed"

echo ""
echo "Step 3: Setting up environment file..."
if [ ! -f "$BACKEND_DIR/.env" ]; then
    cp $BACKEND_DIR/.env.example $BACKEND_DIR/.env
    print_warning "Created .env from example. Please edit with your credentials!"
    print_warning "Run: nano $BACKEND_DIR/.env"
else
    print_status ".env file exists"
fi

echo ""
echo "Step 4: Setting up MySQL database..."
echo "Please run the following commands manually in MySQL:"
echo ""
echo "  sudo mysql -u root"
echo "  source $BACKEND_DIR/schema.sql"
echo ""
read -p "Press Enter when MySQL is set up..."
print_status "MySQL setup acknowledged"

echo ""
echo "Step 5: Installing frontend dependencies..."
cd $FRONTEND_DIR
npm install --production
print_status "Frontend dependencies installed"

echo ""
echo "Step 6: Setting up systemd service for backend..."
sudo cp $APP_DIR/deploy/systemd/linkshortener-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable linkshortener-backend
sudo systemctl start linkshortener-backend
print_status "Backend service configured and started"

echo ""
echo "Step 7: Setting up PM2 for frontend..."
cd $FRONTEND_DIR
pm2 start ecosystem.config.json
pm2 save
print_status "Frontend started with PM2"

echo ""
echo "Step 8: Setting up Nginx..."
sudo cp $APP_DIR/deploy/nginx/lnk.kasunc.live.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/lnk.kasunc.live.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
print_status "Nginx configured"

echo ""
echo "======================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file: nano $BACKEND_DIR/.env"
echo "2. Set up Cloudflare DNS: lnk.kasunc.live -> your VM IP"
echo "3. Generate Cloudflare Origin Certificate and place in /etc/ssl/cloudflare/"
echo "4. Test the application: https://lnk.kasunc.live"
echo ""
echo "Useful commands:"
echo "  - Check backend: sudo systemctl status linkshortener-backend"
echo "  - Check frontend: pm2 status"
echo "  - View backend logs: sudo journalctl -u linkshortener-backend -f"
echo "  - View frontend logs: pm2 logs link-shortener-frontend"
echo ""
