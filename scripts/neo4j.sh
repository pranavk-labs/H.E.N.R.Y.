#!/bin/bash
# Quick script to manage Neo4j Docker container

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Detect docker compose command (docker-compose or docker compose)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "Error: docker-compose or 'docker compose' not found"
    exit 1
fi

case "${1:-}" in
  start)
    echo "Starting Neo4j..."
    $DOCKER_COMPOSE up -d neo4j
    echo ""
    echo "✓ Neo4j is starting..."
    echo "  Web UI: http://localhost:7474"
    echo "  Bolt URI: bolt://localhost:7687"
    echo "  Username: neo4j"
    echo "  Password: henry123"
    echo ""
    echo "Waiting for Neo4j to be ready..."
    sleep 3
    echo "✓ Neo4j is ready! (It may take a few more seconds to fully initialize)"
    ;;
  stop)
    echo "Stopping Neo4j..."
    $DOCKER_COMPOSE stop neo4j
    echo "✓ Neo4j stopped"
    ;;
  restart)
    echo "Restarting Neo4j..."
    $DOCKER_COMPOSE restart neo4j
    echo "✓ Neo4j restarted"
    ;;
  status)
    $DOCKER_COMPOSE ps neo4j
    ;;
  logs)
    $DOCKER_COMPOSE logs -f neo4j
    ;;
  shell)
    $DOCKER_COMPOSE exec neo4j cypher-shell -u neo4j -p henry123
    ;;
  clean)
    echo "⚠️  This will remove the Neo4j container and all data!"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
      $DOCKER_COMPOSE down -v neo4j
      echo "✓ Neo4j container and volumes removed"
    else
      echo "Cancelled"
    fi
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs|shell|clean}"
    echo ""
    echo "Commands:"
    echo "  start   - Start Neo4j container"
    echo "  stop    - Stop Neo4j container"
    echo "  restart - Restart Neo4j container"
    echo "  status  - Show Neo4j container status"
    echo "  logs    - Show Neo4j logs (follow mode)"
    echo "  shell   - Open Cypher shell"
    echo "  clean   - Remove container and all data (⚠️  destructive)"
    exit 1
    ;;
esac

