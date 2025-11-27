#!/bin/sh

# Exit on any error
set -e

# Default environment
ENVIRONMENT=${1:-development}

echo "🚀 Starting File Vault Application..."
echo "📋 Environment: $ENVIRONMENT"

# Set Django settings module based on environment
export DJANGO_SETTINGS_MODULE="core.settings.$ENVIRONMENT"

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Setting up environment file..."
    if [ -f "venv/env/$ENVIRONMENT.env" ]; then
        cp "venv/env/$ENVIRONMENT.env" .env
        echo "✅ Copied $ENVIRONMENT.env to .env"
    else
        echo "❌ Environment file venv/env/$ENVIRONMENT.env not found!"
        echo "Available environments: development, production, testing"
        exit 1
    fi
else
    echo "✅ Using existing .env file"
fi

# Ensure media directory exists and has proper permissions
echo "📁 Setting up media directory..."
mkdir -p media/uploads
chmod -R 755 media

# Run migrations
echo "🔄 Running migrations..."
python manage.py makemigrations
python manage.py migrate

# Start server
echo "🌐 Starting server on http://localhost:8000..."
echo "📡 API endpoints available at http://localhost:8000/api/"
echo "🛑 Press Ctrl+C to stop the server"
echo ""

python manage.py runserver 0.0.0.0:8000 