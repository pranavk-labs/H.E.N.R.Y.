# Development Guide

## Development Workflow

### Local Development vs Pi Development

**Recommended Approach: Develop Locally, Deploy to Pi**

Develop and test on your local machine, then deploy to Raspberry Pi for hardware-specific testing and production use.

### Getting Started

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd H.E.N.R.Y.
   ```

2. **Set Up Local Development Environment**
   - Create virtual environment
   - Install dependencies
   - Configure environment variables for local development
   - Set up local services (Neo4j, Ollama) or connect to home server
   - Run development server locally

3. **Set Up Pi Deployment**
   - Configure SSH access to Raspberry Pi
   - Set up deployment scripts
   - Configure Pi environment variables
   - Test deployment process

### Local Development Environment

**Recommended Setup:**
- **Local Machine**: Your development computer (Linux, macOS, or Windows)
- Python 3.9+ virtual environment
- Code editor/IDE with Python support
- Git for version control
- Docker (optional, for local Neo4j/Ollama)
- SSH access to Raspberry Pi for deployment

**Local Service Options:**

**Option 1: Use Home Server Services (Recommended)**
- Connect to Neo4j on home server via Tailscale
- Connect to Ollama on home server via Tailscale
- No need to run services locally
- Tests real network connectivity

**Option 2: Run Services Locally**
- Neo4j: Docker or native installation
- Ollama: Local installation
- Better for offline development
- Faster iteration (no network latency)

**Option 3: Mock Services**
- Mock Neo4j client for unit tests
- Mock Ollama client for unit tests
- Fastest for development
- Use for testing logic without services

**Development Tools:**
- Code formatter (black, autopep8)
- Linter (pylint, flake8)
- Type checker (mypy) - optional
- Testing framework (pytest)
- Debugger (pdb, IDE debugger)

## Code Style Guidelines

### Python Code Style

**General Principles:**
- Follow PEP 8 style guide
- Use type hints where helpful
- Write clear, descriptive names
- Keep functions focused and small
- Add docstrings for public functions/classes

**Naming Conventions:**
- Functions and variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

**Code Organization:**
- Group related functionality
- Separate concerns (services, models, routes)
- Use dependency injection
- Keep dependencies minimal

### Project Structure

```
backend/
├── api/              # API routes and endpoints
├── services/         # Business logic services
├── models/           # Data models
├── integrations/     # External service integrations
└── robot/            # Robot control code
```

### Documentation

**Code Documentation:**
- Docstrings for all public functions/classes
- Inline comments for complex logic
- README files for major components
- Update documentation when changing code

## Local Development Setup

### Environment Configuration

Create separate environment files for different environments:

**`.env.local`** (Local Development):
```env
# Application
APP_ENV=development
DEBUG=True

# Services - Option 1: Connect to home server
NEO4J_URI=bolt://home-server-tailscale-ip:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

OLLAMA_BASE_URL=http://home-server-tailscale-ip:11434

# Services - Option 2: Local services
# NEO4J_URI=bolt://localhost:7687
# OLLAMA_BASE_URL=http://localhost:11434

# Audio (mock or skip on local)
AUDIO_ENABLED=False
ROBOT_ENABLED=False

# API
API_HOST=127.0.0.1
API_PORT=8000
```

**`.env.pi`** (Raspberry Pi):
```env
# Application
APP_ENV=production
DEBUG=False

# Services - Connect to home server
NEO4J_URI=bolt://home-server-tailscale-ip:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

OLLAMA_BASE_URL=http://home-server-tailscale-ip:11434

# Audio (enabled on Pi)
AUDIO_ENABLED=True
ROBOT_ENABLED=True

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### Running Services Locally

**Neo4j with Docker:**
```bash
docker run -d \
    --name neo4j-dev \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/devpassword \
    -v neo4j_data:/data \
    neo4j:latest
```

**Ollama Locally:**
```bash
# Install Ollama (see https://ollama.ai)
ollama serve
ollama pull llama3.2:3b  # or your preferred model
```

### Mocking Services for Testing

Create mock implementations for services:

**Mock Neo4j Client:**
```python
# tests/mocks/neo4j_mock.py
class MockNeo4jClient:
    def __init__(self):
        self.graph = {}  # Simple in-memory graph
    
    def execute_query(self, query, params=None):
        # Mock implementation
        return []
```

**Mock Ollama Client:**
```python
# tests/mocks/ollama_mock.py
class MockOllamaClient:
    def generate(self, prompt):
        # Mock response
        return "Mock response"
```

### Running Development Server Locally

```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Load local environment
export $(cat .env.local | xargs)  # Linux/macOS
# or use python-dotenv to load automatically

# Run development server
python scripts/dev_server.py
# or
uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000
```

## Deployment to Raspberry Pi

### Deployment Strategies

**Option 1: Git-Based Deployment (Recommended)**
```bash
# On Pi
cd ~/H.E.N.R.Y.
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart henry.service
```

**Option 2: Rsync Deployment**
```bash
# From local machine
rsync -avz --exclude 'venv' --exclude '__pycache__' \
    --exclude '.git' \
    ./ pi@raspberry-pi-ip:~/H.E.N.R.Y./
```

**Option 3: Docker Deployment (if using containers)**
```bash
# Build on local machine
docker build -t henry:latest .

# Push to registry or copy to Pi
docker save henry:latest | ssh pi@raspberry-pi-ip docker load
```

### Deployment Script

Create `scripts/deploy.sh`:
```bash
#!/bin/bash
# Deployment script for Raspberry Pi

PI_USER="pi"
PI_HOST="raspberry-pi-ip"  # or use Tailscale IP
PI_PATH="~/H.E.N.R.Y."

echo "Deploying to Raspberry Pi..."

# Sync files (excluding venv, cache, etc.)
rsync -avz --delete \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    --exclude '.env' \
    ./ ${PI_USER}@${PI_HOST}:${PI_PATH}/

# Run deployment commands on Pi
ssh ${PI_USER}@${PI_HOST} << 'ENDSSH'
cd ~/H.E.N.R.Y.
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart henry.service
ENDSSH

echo "Deployment complete!"
```

### Environment-Specific Configuration

Use environment detection in code:

```python
# backend/config/settings.py
import os
from pathlib import Path

def get_env_file():
    """Determine which .env file to use"""
    if Path('.env.local').exists() and os.getenv('APP_ENV') != 'production':
        return '.env.local'
    elif Path('.env.pi').exists():
        return '.env.pi'
    else:
        return '.env'

class Settings(BaseSettings):
    # ... settings ...
    
    class Config:
        env_file = get_env_file()
```

## Testing Strategies

### Test Types

**Unit Tests:**
- Test individual functions/methods
- Mock external dependencies
- Fast execution
- High coverage target

**Integration Tests:**
- Test component interactions
- Test with real database (local Neo4j or home server)
- Test API endpoints
- Test service integrations
- Can use local services or connect to home server

**End-to-End Tests:**
- Test complete user flows
- Test voice interaction pipeline
- Test mobile app integration
- Manual testing for complex scenarios

### Testing Tools

- **pytest**: Primary testing framework
- **pytest-asyncio**: For async tests
- **pytest-mock**: For mocking
- **TestClient**: FastAPI testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_knowledge_service.py

# Run with coverage
pytest --cov=backend tests/

# Run specific test
pytest tests/test_knowledge_service.py::test_add_idea
```

## Git Workflow

### Branch Strategy

**Main Branches:**
- `main`: Production-ready code
- `develop`: Development integration branch

**Feature Branches:**
- `feature/feature-name`: New features
- `fix/bug-name`: Bug fixes
- `docs/documentation-name`: Documentation updates

### Commit Messages

**Format:**
```
type(scope): brief description

Detailed explanation if needed
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Tests
- `chore`: Maintenance

**Examples:**
```
feat(knowledge): add concept linking functionality

fix(pomodoro): correct session persistence issue

docs(api): update API endpoint documentation
```

### Pull Request Process

1. Create feature branch from `develop`
2. Make changes and commit
3. Write/update tests
4. Update documentation
5. Push branch and create PR
6. Code review
7. Merge to `develop`
8. Deploy to test environment
9. Merge to `main` when ready

## Debugging Tips

### Common Debugging Techniques

**Logging:**
- Use structured logging
- Appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- Include context in log messages
- Use log rotation

**Python Debugger:**
```python
import pdb; pdb.set_trace()  # Breakpoint
```

**IDE Debugging:**
- Set breakpoints in IDE
- Step through code
- Inspect variables
- Evaluate expressions

### Debugging Voice Issues

**Audio Debugging:**
- Test audio devices independently
- Check audio buffer sizes
- Monitor CPU usage during audio processing
- Test with different audio inputs

**STT Debugging:**
- Test STT with known audio files
- Check transcription accuracy
- Review STT model performance
- Test with different accents/noise levels

### Debugging Database Issues

**Neo4j Debugging:**
- Use Neo4j Browser to inspect data
- Test queries directly in browser
- Check query performance
- Review transaction handling

### Debugging Service Issues

**Service Debugging:**
- Check service logs
- Verify service status
- Test service endpoints
- Check service dependencies
- Review resource usage

## Common Issues and Solutions

### Audio Issues

**Problem**: Audio not working
- **Solution**: Check ALSA configuration, verify device permissions, test with command-line tools

**Problem**: High latency
- **Solution**: Optimize buffer sizes, check CPU usage, review processing pipeline

**Problem**: Poor audio quality
- **Solution**: Check microphone quality, adjust gain, review audio processing

### Database Issues

**Problem**: Slow queries
- **Solution**: Add indexes, optimize query patterns, review database configuration

**Problem**: Connection failures
- **Solution**: Check Neo4j service status, verify credentials, check network

### Performance Issues

**Problem**: High CPU usage
- **Solution**: Profile code, optimize heavy operations, review model sizes

**Problem**: Memory leaks
- **Solution**: Review caching, check for unclosed connections, profile memory usage

**Problem**: Slow API responses
- **Solution**: Optimize database queries, add caching, review service architecture

### Service Issues

**Problem**: Service won't start
- **Solution**: Check logs, verify configuration, check dependencies, test manually

**Problem**: Service crashes
- **Solution**: Review error logs, check resource limits, test individual components

## Local vs Pi Development

### Local Development Advantages

- **Faster iteration**: No network latency, faster compilation
- **Better tooling**: Full IDE support, debuggers, profilers
- **Easier testing**: Mock services, faster test runs
- **No hardware constraints**: Test without Pi limitations
- **Better development experience**: Native OS, better performance

### When to Test on Pi

- **Hardware-specific features**: Audio I/O, GPIO, robot control
- **Performance testing**: Real resource constraints
- **Integration testing**: Full system with real services
- **Production-like testing**: Before final deployment

### Development Workflow

1. **Develop Locally**
   - Write code on local machine
   - Run unit tests with mocks
   - Test API endpoints locally
   - Use local services or connect to home server

2. **Test on Pi (Periodically)**
   - Deploy to Pi for hardware testing
   - Test audio/voice features
   - Test robot control
   - Performance testing

3. **Deploy to Production**
   - Final testing on Pi
   - Production deployment

## Raspberry Pi Specific Considerations

### Development on Pi

**Remote Development:**
- Use SSH for remote access
- Use VS Code Remote or similar
- Test directly on Pi hardware
- Monitor resource usage

**Performance:**
- Be aware of Pi limitations
- Optimize for Pi hardware
- Test with realistic loads
- Monitor thermal throttling

### Local Development with Pi Services

**Connecting to Home Server from Local:**
- Install Tailscale on local machine
- Connect to same Tailscale network as Pi
- Use home server services (Neo4j, Ollama) for development
- Test real network connectivity

### Hardware Testing

**GPIO Testing:**
- Test GPIO operations carefully
- Use appropriate voltage levels
- Test with actual hardware
- Handle errors gracefully

**Audio Testing:**
- Test with actual audio devices
- Consider Pi audio limitations
- Test with different devices
- Optimize for Pi audio hardware

## Code Review Guidelines

### What to Review

**Functionality:**
- Does code work as intended?
- Are edge cases handled?
- Are errors handled properly?

**Code Quality:**
- Is code readable and maintainable?
- Are best practices followed?
- Is code style consistent?

**Testing:**
- Are tests adequate?
- Do tests pass?
- Is coverage sufficient?

**Documentation:**
- Is code documented?
- Are changes documented?
- Is README updated?

### Review Process

1. Review code changes
2. Test functionality if possible
3. Check for potential issues
4. Provide constructive feedback
5. Approve or request changes

## Best Practices

### General

- Write clear, readable code
- Keep functions focused
- Use meaningful names
- Add comments for complex logic
- Write tests for new features
- Update documentation

### Performance

- Profile before optimizing
- Cache expensive operations
- Use async where appropriate
- Optimize database queries
- Monitor resource usage

### Security

- Never commit secrets
- Use environment variables
- Validate all inputs
- Handle errors securely
- Keep dependencies updated

### Maintenance

- Keep dependencies updated
- Remove unused code
- Refactor when needed
- Update documentation
- Review and improve code

## Resources

### Documentation
- [Phase Documentation](.) - Development phase guides
- [Local Development Guide](local-development.md) - Complete local development setup
- [Architecture](architecture.md) - System architecture
- [API Documentation](api-docs.md) - API reference (if created)

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [Raspberry Pi GPIO](https://www.raspberrypi.org/documentation/usage/gpio/)
- [Whisper Documentation](https://github.com/openai/whisper)

