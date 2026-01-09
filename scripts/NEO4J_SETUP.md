# Neo4j Docker Setup

Quick setup guide for running Neo4j in Docker for H.E.N.R.Y. development.

## Quick Start

### Using the helper script (recommended):

```bash
# Start Neo4j
./scripts/neo4j.sh start

# Stop Neo4j
./scripts/neo4j.sh stop

# View logs
./scripts/neo4j.sh logs

# Check status
./scripts/neo4j.sh status

# Open Cypher shell
./scripts/neo4j.sh shell
```

### Using Docker Compose directly:

```bash
# Start Neo4j
docker-compose up -d neo4j

# Stop Neo4j
docker-compose stop neo4j

# View logs
docker-compose logs -f neo4j

# Remove container and data (⚠️  destructive)
docker-compose down -v neo4j
```

## Default Credentials

- **Web UI**: http://localhost:7474
- **Bolt URI**: `bolt://localhost:7687`
- **Username**: `neo4j`
- **Password**: `henry123`

## Configuration

The Neo4j container is configured in `docker-compose.yml`. To change the password:

1. Edit `docker-compose.yml` and change `NEO4J_AUTH=neo4j/henry123` to your desired password
2. Update your `.env.local` file with the matching password:
   ```
   NEO4J_PASSWORD=henry123
   ```

## Testing Connection

After starting Neo4j, test the connection:

```bash
# Test Neo4j health
poetry run python scripts/test_neo4j_api.py --health

# Test direct Neo4j operations
poetry run python scripts/test_neo4j_api.py --direct

# Test Graph API (requires API server running)
poetry run python scripts/test_neo4j_api.py --api
```

## Data Persistence

Neo4j data is stored in Docker volumes:
- `neo4j_data` - Database files
- `neo4j_logs` - Log files
- `neo4j_import` - Import directory
- `neo4j_plugins` - Plugins directory

Data persists even if you stop/restart the container. To completely remove all data:

```bash
./scripts/neo4j.sh clean
```

## Troubleshooting

### Container won't start
- Check if ports 7474 or 7687 are already in use:
  ```bash
  lsof -i :7474
  lsof -i :7687
  ```

### Can't connect
- Make sure the container is running: `docker-compose ps neo4j`
- Check logs: `./scripts/neo4j.sh logs`
- Verify credentials in `.env.local` match `docker-compose.yml`

### Reset password
If you need to reset the password:
1. Stop the container: `./scripts/neo4j.sh stop`
2. Remove the container: `docker-compose rm neo4j`
3. Update password in `docker-compose.yml`
4. Start again: `./scripts/neo4j.sh start`

