# Phase 1: Foundation

## Objectives and Goals

Phase 1 establishes the foundational infrastructure for H.E.N.R.Y., setting up the Raspberry Pi environment, backend API, graph database, and essential services. This phase focuses on creating a solid base for all subsequent development.

### Key Objectives

-   Set up Raspberry Pi OS and configure the development environment
-   Establish the backend API foundation using Python/FastAPI
-   Configure Tailscale VPN connection to home server
-   Set up connection to remote Graph Database (Neo4j on home server)
-   Set up connection to remote LLM service (Ollama on home server)
-   Set up voice/audio input/output infrastructure with wake word detection (essential for primary interaction method)
-   Configure development tools and workflows
-   Establish project structure and code organization

## Core Features

### 1. Raspberry Pi Environment Setup

-   Raspberry Pi OS installation and configuration
-   System updates and essential package installation
-   Audio input/output configuration (microphone and speakers)
-   Network configuration (static IP recommended for home server)
-   GPIO access configuration for future robot features
-   Performance optimization for Pi hardware

### 2. Backend API Foundation

-   FastAPI application structure
-   Basic routing and middleware setup
-   CORS configuration
-   Health check endpoint
-   Environment configuration management (.env files)
-   Service management (systemd integration)

### 3. Tailscale VPN Setup

-   Install Tailscale on Raspberry Pi
-   Authenticate and connect to Tailscale network
-   Verify connection to home server
-   Test network connectivity
-   Configure firewall rules if needed
-   Set up automatic reconnection

### 4. Remote Services Connection Setup

**Graph Database (Neo4j on Home Server):**

-   Neo4j connection client setup
-   Connection to Neo4j via Tailscale (home server IP/domain)
-   Authentication configuration
-   Connection pooling and error handling
-   Health check and reconnection logic
-   Local fallback cache (NetworkX) for offline operation

**LLM Service (Ollama on Home Server):**

-   Ollama client setup
-   Connection to Ollama via Tailscale (home server IP/domain)
-   Model availability check
-   Connection health monitoring
-   Retry logic and error handling

### 5. Audio/Voice Infrastructure

-   Audio device detection and configuration
-   ALSA/PulseAudio setup
-   Audio input/output testing utilities
-   **Wake word detection setup** (HENRY only processes audio when name is called)
-   Audio service foundation (to be expanded in Phase 3)
-   Device selection and switching capabilities

### 6. Development Environment

**Local Development Setup:**

-   Python virtual environment setup (on local machine)
-   Dependency management (requirements.txt)
-   Development server script
-   Environment configuration (.env.local for local, .env.pi for Pi)
-   Local service setup (Neo4j, Ollama) or connection to home server
-   Deployment scripts for pushing to Pi
-   Code organization and project structure
-   Git workflow setup

**Pi Development Setup:**

-   Python virtual environment setup (on Pi)
-   Service configuration
-   Production environment setup

## Execution Strategy

### Step 1: Raspberry Pi OS Setup

1. Flash Raspberry Pi OS (64-bit) to microSD card
2. Initial system configuration (SSH, WiFi, locale)
3. System updates and package installation
4. Audio system configuration and testing
5. Network setup (static IP if needed)
6. GPIO permissions configuration

### Step 2: Project Structure (Local Development)

1. Create directory structure (backend, mobile, docs, scripts, config, tests)
2. Initialize Git repository
3. Install Poetry (if not already installed)
4. Initialize Poetry project: `poetry init` (or create pyproject.toml manually)
5. Add dependencies to pyproject.toml
6. Install dependencies: `poetry install` (creates virtual environment automatically)
7. Set up environment configuration files:
    - `.env.example` - Template
    - `.env.local` - Local development (connect to home server or local services)
    - `.env.pi` - Raspberry Pi production
8. Create deployment scripts (see Development Guide)

### Step 3: Backend API Foundation

1. Create FastAPI application structure
2. Implement basic routing (health check, root endpoint)
3. Set up CORS middleware
4. Create configuration management system
5. Implement logging infrastructure

### Step 5: Graph Database Schema (on Home Server)

1. Access Neo4j on home server (via Tailscale)
2. Design initial schema (nodes, relationships, constraints)
3. Create database initialization script
4. Run initialization on home server
5. Test schema and queries
6. Document schema structure

### Step 6: Audio Infrastructure

1. Configure ALSA/PulseAudio
2. Create audio device detection utilities
3. Implement basic audio service structure
4. **Set up wake word detection** (HENRY only processes when name is called)
5. Create audio testing scripts
6. Document audio configuration

### Step 7: Service Management (Pi Only)

1. Create systemd service file
2. Configure service to run on boot
3. Set up logging for services
4. Test service startup and shutdown
5. Create service management scripts

**Note**: Service management is only needed on Pi. Local development uses development server.

## Testing Requirements

### Unit Tests

-   Configuration loading and validation
-   Database connection and query execution
-   Audio device detection
-   Wake word detection accuracy

### Integration Tests

-   API health check endpoint
-   Database connectivity and schema initialization
-   Audio input/output functionality
-   Wake word detection and activation flow
-   Service startup and shutdown

### Manual Testing

-   Raspberry Pi boot and service startup
-   Audio recording and playback
-   Network accessibility
-   Database browser access (Neo4j)
-   API endpoint accessibility from mobile/remote devices

## Completion Criteria

Phase 1 is complete when:

-   [ ] Raspberry Pi OS is installed, updated, and configured
-   [ ] Audio input/output devices are working and tested
-   [ ] Poetry is installed and configured
-   [ ] Dependencies are installed via Poetry (pyproject.toml)
-   [ ] FastAPI backend is running and accessible on local network
-   [ ] Tailscale VPN is installed, authenticated, and connected
-   [ ] Connection to home server via Tailscale is verified
-   [ ] Neo4j connection to home server is working
-   [ ] Ollama connection to home server is working
-   [ ] Database schema is initialized on home server Neo4j
-   [ ] Health check endpoint returns successful response
-   [ ] Wake word detection is implemented and working (HENRY only activates when name is called)
-   [ ] Connection health monitoring is implemented
-   [ ] Local fallback cache is implemented
-   [ ] Project structure follows established conventions
-   [ ] Development environment is fully configured
-   [ ] systemd service is configured and tested
-   [ ] All tests pass
-   [ ] Documentation is updated

## Questions to Answer

1. **Home Server Access**: What is the Tailscale IP/domain of the home server?
2. **Neo4j Configuration**: What port is Neo4j running on home server? (default: 7687)
3. **Ollama Configuration**: What port is Ollama running on home server? (default: 11434)
4. **Network Reliability**: How reliable is Tailscale connection? (affects fallback strategy)
5. **Audio Hardware**: What specific microphone/speaker setup will be used? (affects configuration approach)
6. **Wake Word**: What wake word/phrase should trigger HENRY? (e.g., "Hey HENRY", "HENRY", etc.)
7. **Network Setup**: Static IP or DHCP? (Static recommended for home server)
8. **Development Workflow**:
    - **Recommended**: Develop locally, deploy to Pi
    - Local development with connection to home server services
    - Periodic testing on Pi for hardware-specific features
    - See [Development Guide](development-guide.md) for local setup
9. **Service Management**: Any specific logging requirements or monitoring needs?
10. **Security**: What level of security hardening is needed? (firewall, fail2ban, etc.) - Note: Authentication is not required for single-user local system
11. **Backup Strategy**: How should database and configuration be backed up?

## Next Steps

After completing Phase 1, proceed to:

-   **[Phase 2: Core Features](phase-2-core-features.md)** - Implement graph-based knowledge system and productivity tools
-   Review and refine architecture based on initial implementation
-   Begin planning voice interaction system (Phase 3)

## Troubleshooting

### Common Issues

**Audio not working:**

-   Check device permissions and ALSA configuration
-   Verify audio device detection
-   Test with command-line tools (arecord, aplay)

**Tailscale connection issues:**

-   Check Tailscale status: `sudo tailscale status`
-   Verify home server is online and accessible
-   Test connectivity: `ping home-server-ip`
-   Check Tailscale authentication

**Neo4j connection issues:**

-   Verify Neo4j is running on home server
-   Check Tailscale IP/domain is correct
-   Verify port is accessible (default 7687)
-   Check firewall settings on home server
-   Verify credentials in `.env`
-   Test connection from Pi to home server

**Ollama connection issues:**

-   Verify Ollama is running on home server
-   Check Tailscale IP/domain is correct
-   Verify port is accessible (default 11434)
-   Check firewall settings on home server
-   Test connection: `curl http://home-server-ip:11434/api/tags`

**GPIO access denied:**

-   Ensure user is in gpio group
-   May require logout/login

**Performance issues:**

-   Monitor CPU and memory usage
-   Consider USB SSD instead of microSD
-   Disable unnecessary system services
