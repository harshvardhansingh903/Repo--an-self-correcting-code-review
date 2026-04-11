#!/bin/bash
# deploy.sh - Deployment script for Code Review Agent

set -e

echo "🚀 Code Review Agent - Deployment Script"
echo "========================================"

# Check prerequisites
check_prereqs() {
    echo "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker not found. Please install Docker."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose not found. Please install Docker Compose."
        exit 1
    fi
    
    echo "✅ Docker and Docker Compose found"
}

# Load environment
load_env() {
    if [ -f .env ]; then
        echo "Loading .env configuration..."
        set -a
        source .env
        set +a
    else
        echo "❌ .env file not found. Please configure .env with your credentials."
        exit 1
    fi
    
    # Validate required vars
    required_vars=("GITHUB_TOKEN" "OPENAI_API_KEY" "GITHUB_WEBHOOK_SECRET")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "❌ Missing required environment variable: $var"
            exit 1
        fi
    done
    
    echo "✅ Environment variables loaded"
}

# Build images
build() {
    echo "Building Docker images..."
    docker-compose build --no-cache
    echo "✅ Images built successfully"
}

# Start services
start() {
    echo "Starting services..."
    docker-compose up -d
    echo "✅ Services started"
    
    # Wait for database
    echo "Waiting for database to be ready..."
    sleep 5
    
    # Initialize database
    echo "Initializing database..."
    docker-compose exec -T agent python -c "
from src.db.models import init_database
import asyncio
asyncio.run(init_database())
print('✅ Database initialized')
"
}

# Run tests
test() {
    echo "Running tests..."
    docker-compose exec -T agent pytest -v
    echo "✅ All tests passed"
}

# Show status
status() {
    echo "Service Status:"
    docker-compose ps
    echo ""
    echo "Agent logs:"
    docker-compose logs agent --tail=10
}

# Stop services
stop() {
    echo "Stopping services..."
    docker-compose down
    echo "✅ Services stopped"
}

# Clean up
clean() {
    echo "Cleaning up..."
    docker-compose down -v
    echo "✅ Cleanup complete"
}

# Main
case "${1:-start}" in
    check)
        check_prereqs
        ;;
    build)
        check_prereqs
        load_env
        build
        ;;
    start)
        check_prereqs
        load_env
        build
        start
        status
        ;;
    test)
        check_prereqs
        test
        ;;
    status)
        status
        ;;
    stop)
        stop
        ;;
    clean)
        clean
        ;;
    restart)
        stop
        start
        status
        ;;
    logs)
        docker-compose logs -f agent
        ;;
    *)
        echo "Usage: $0 {check|build|start|test|status|stop|clean|restart|logs}"
        exit 1
        ;;
esac
