# OptiSchema Slim Makefile
# Commands for local development and Docker operations

.PHONY: help dev dev-backend dev-frontend install docker-up docker-down clean logs

help: ## Show this help message
	@echo "OptiSchema Slim - Local-First PostgreSQL Optimization"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies for Backend and Frontend
	@echo "📦 Installing Backend dependencies..."
	cd backend && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
	@echo "📦 Installing Frontend dependencies..."
	cd frontend && npm install
	@echo "✅ Dependencies installed!"

dev-backend: ## Run Backend locally (FastAPI)
	@echo "🚀 Starting Backend on http://localhost:8080..."
	cd backend && ./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload

dev-frontend: ## Run Frontend locally (Next.js)
	@echo "🚀 Starting Frontend on http://localhost:5173..."
	cd frontend && npm run dev

dev: ## Run both Backend and Frontend (requires make -j)
	@echo "🚀 Starting OptiSchema Development Environment..."
	@make -j 2 dev-backend dev-frontend

docker-up: ## Start services with Docker Compose
	@echo "🐳 Starting Docker services..."
	docker compose up -d --build
	@echo "✅ Services started!"
	@echo "📊 Dashboard: http://localhost:3000"
	@echo "🔧 API: http://localhost:8080/docs"

docker-down: ## Stop Docker services
	@echo "🛑 Stopping Docker services..."
	docker compose down
	@echo "✅ Services stopped!"

logs: ## Show Docker logs
	docker compose logs -f

seed-sandbox: ## Seed the sandbox database (requires Docker PG running)
	@echo "🌱 Seeding sandbox database..."
	DATABASE_URL="postgresql://optischema:optischema_pass@localhost:5433/optischema_sandbox" ./backend/venv/bin/python scripts/seed/seed_data.py

load-gen: ## Run the load generator locally
	@echo "📈 Starting load generator..."
	DATABASE_URL="postgresql://optischema:optischema_pass@localhost:5433/optischema_sandbox" ./backend/venv/bin/python scripts/load/generate_load.py

clean: ## Clean up artifacts and caches
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".next" -exec rm -rf {} +
	rm -f backend/optischema.db
	@echo "✅ Cleanup completed!"