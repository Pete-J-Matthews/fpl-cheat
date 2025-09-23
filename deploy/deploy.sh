#!/bin/bash

# FPL Cheat Deployment Script
# Usage: ./deploy.sh [local|prod]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Local deployment
deploy_local() {
    print_status "Starting local deployment..."
    
    # Build and start services
    print_status "Building and starting services..."
    docker compose -f deploy/docker-compose.yml up --build -d
    
    # Wait for services to be ready
    print_status "Waiting for services to start..."
    sleep 10
    
    # Check if services are running
    if docker compose -f deploy/docker-compose.yml ps | grep -q "Up"; then
        print_status "✅ Services are running!"
        echo ""
        echo "🌐 Frontend: http://localhost:8501"
        echo "🔧 Backend: http://localhost:8000/health/"
        echo ""
        echo "To stop services: docker compose -f deploy/docker-compose.yml down"
        echo "To view logs: docker compose -f deploy/docker-compose.yml logs -f"
    else
        print_error "Failed to start services. Check logs with: docker compose -f deploy/docker-compose.yml logs"
        exit 1
    fi
}

# Production deployment
deploy_prod() {
    print_status "Starting production deployment to Vercel (single app)..."
    
    # Check if Vercel CLI is installed
    if ! command -v vercel &> /dev/null; then
        print_error "Vercel CLI not found. Please install it:"
        echo "npm i -g vercel"
        exit 1
    fi
    
    # Clean up unnecessary files before deployment
    print_status "Cleaning up unnecessary files before deployment..."
    
    # Remove any cached files
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type d -name ".venv" -exec rm -rf {} +
    find . -type f -name "*.pyc" -exec rm -f {} +
    
    # Deploy the entire project as a single app
    print_status "Deploying to Vercel as a single app..."
    
    # Link to Vercel project (from project root)
    vercel link --yes
    
    # Deploy to production with size optimization
    APP_URL=$(vercel --prod | grep -o 'https://[^[:space:]]*' | head -1)
    
    print_status "🎉 Deployment complete!"
    echo ""
    echo "🌐 App URL: $APP_URL"
    echo "  - Frontend: $APP_URL"
    echo "  - Backend API: $APP_URL/api"
    echo ""
}

# Main script
main() {
    case "${1:-local}" in
        "local")
            check_docker
            deploy_local
            ;;
        "prod")
            deploy_prod
            ;;
        *)
            echo "Usage: $0 [local|prod]"
            echo "  local: Deploy locally with Docker (default)"
            echo "  prod:  Deploy to Vercel (frontend + backend)"
            exit 1
            ;;
    esac
}

main "$@"
