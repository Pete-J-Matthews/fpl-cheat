# FPL Cheat Makefile
# Simple commands for development and deployment

.PHONY: help install dev prod clean logs stop start

# Default target
help:
	@echo "FPL Cheat - Available Commands:"
	@echo ""
	@echo "  make dev     - Start local development (Docker)"
	@echo "  make prod    - Deploy to Vercel (frontend + backend)"
	@echo "  make logs    - View service logs"
	@echo "  make stop    - Stop all services"
	@echo "  make clean   - Clean up containers and images"
	@echo "  make help    - Show this help message"
	@echo ""

# Install dependencies (if running locally)
install:
	@echo "Installing dependencies..."
	uv sync

# Start local development
dev:
	@echo "Starting local development..."
	./deploy/deploy.sh local

# Deploy to production (Vercel)
prod:
	@echo "Deploying to Vercel..."
	./deploy/deploy.sh prod

# View logs
logs:
	@echo "Viewing service logs..."
	docker compose -f deploy/docker-compose.yml logs -f

# Stop services
stop:
	@echo "Stopping services..."
	docker compose -f deploy/docker-compose.yml down

# Clean up
clean:
	@echo "Cleaning up containers and images..."
	docker compose -f deploy/docker-compose.yml down -v
	docker system prune -f

# Quick start (alias for dev)
start: dev
