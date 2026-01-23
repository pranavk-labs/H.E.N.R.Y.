# H.E.N.R.Y. (Acronym unknown so far)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.9--3.11-blue.svg)](https://www.python.org/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Compatible-red.svg)](https://www.raspberrypi.org/)

A personalized, open-source conversational desk assistant running on Raspberry Pi. H.E.N.R.Y. is your always-on productivity companion that you interact with continuously via voice, featuring a graph-based knowledge system, productivity tools, and a personality all its own.

## About

H.E.N.R.Y. is a Raspberry Pi-based conversational desk assistant that you talk to continuously throughout your work. Unlike traditional assistants, H.E.N.R.Y. maintains a rich, graph-based understanding of your preferences, habits, and context, enabling natural, continuous conversations. Built to run entirely on your home server (Raspberry Pi), it combines productivity tools, home automation integrations, and a physical robot component with wheels for a unique, personalized experience.

**Key Philosophy**: Open source by design, personalized by nature. While the codebase is fully open source, H.E.N.R.Y. learns and adapts to you, creating a unique assistant tailored to your needs.

## Features

### Core Capabilities

-   **Graph-Based Knowledge System**: Maintains a rich, interconnected understanding of your preferences, habits, and context
-   **Continuous Voice Interaction**: Always-on conversational interface optimized for desk use
-   **Productivity Tools**:
    -   Pomodoro timer with voice control
    -   Idea storage and retrieval system
    -   Task management integration
-   **Home Automation**: Seamless integration with your home management system
-   **Physical Robot**: Wheels and sensors for mobility and personality expression
-   **Mobile Companion App**: Remote access and control via Flutter/Swift mobile apps

### Integrations

-   **Beeper/Matrix**: Secure messaging integration
-   **n8n**: Workflow automation and triggers
-   **Home Management Systems**: Smart home device control
-   **Cloud Services**: Optional cloud integration while maintaining local-first architecture

### Personality

H.E.N.R.Y. isn't just functional—it has personality. Through continuous conversation, physical movement, and contextual awareness, H.E.N.R.Y. becomes a true companion for your desk workspace.

## Architecture

H.E.N.R.Y. follows a **distributed architecture** with resource-intensive services on a home server and the voice interface on Raspberry Pi:

```
┌─────────────────────────────────────────────────────────┐
│                   Home Server (Docker)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Backend    │  │   STT        │  │  Graph DB    │  │
│  │   API        │  │   (Whisper)  │  │  (Neo4j)     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │   LLM        │  │  Integrations│                    │
│  │   (Ollama)   │  │  (n8n, etc)  │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
                        ↕ (Tailscale VPN)
┌─────────────────────────────────────────────────────────┐
│              Raspberry Pi (Voice Interface)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Wake Word   │  │  Audio I/O   │  │   TTS        │  │
│  │  Detection   │  │  Recording   │  │   (Piper)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │  Robot       │  │   GUI        │                    │
│  │  Control     │  │  Display     │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
                        ↕
        ┌───────────────────────────────┐
        │   Mobile Companion App        │
        │   (Flutter/Swift)            │
        └───────────────────────────────┘
```

### Components

#### Server (Docker Container)
-   **Backend API** (Python/FastAPI): Core service layer handling all requests
-   **STT Service** (OpenAI Whisper): Speech-to-text transcription (server-side)
-   **LLM Service** (Ollama): Language model for conversational AI
-   **Graph Database** (Neo4j): Knowledge graph storage
-   **Integration Layer**: Webhooks and APIs for external services

#### Raspberry Pi (Voice Client)
-   **Wake Word Detection** (OpenWakeWord): Always-on voice activation
-   **Audio Recording**: Captures voice input with VAD
-   **TTS Service** (Piper): Text-to-speech output
-   **Robot Controller**: GPIO-based motor and sensor control
-   **GUI Display**: Visual feedback and status
-   **Mobile App**: Flutter (cross-platform) and Swift (iOS native) options

## Tech Stack

### Server (Docker)

-   **Language**: Python 3.11
-   **Framework**: FastAPI
-   **Graph Database**: Neo4j
-   **LLM**: Ollama with quantized models (Llama 3.2 3B Q4, Mistral 7B Q4, Qwen 2.5 7B)
-   **Speech-to-Text**: OpenAI Whisper (small model, ~500MB)
-   **Containerization**: Docker with auto-restart
-   **Network**: Tailscale VPN for secure Pi-to-Server communication

### Raspberry Pi (Voice Client)

-   **Language**: Python 3.9, 3.10, or 3.11 (required for OpenWakeWord's tflite-runtime dependency)
-   **Voice Processing**:
    -   Wake Word Detection: OpenWakeWord (local, always-on)
    -   Speech-to-Text: Remote (sends audio to server)
    -   Text-to-Speech: Piper TTS (local)
-   **Hardware Control**: RPi.GPIO, gpiozero
-   **Service Management**: systemd
-   **OS**: Raspberry Pi OS (64-bit recommended)

### Mobile Companion

-   **Cross-platform**: Flutter (iOS/Android)
-   **iOS Native**: Swift (optional)
-   **Communication**: WebSocket/HTTP REST API

### Infrastructure

-   **Networking**: Tailscale VPN mesh network
-   **Deployment**: Automated scripts for both server and Pi
-   **Monitoring**: Docker healthchecks and systemd

## Hardware Requirements

### Server Requirements

-   **CPU**: Multi-core processor (4+ cores recommended)
-   **RAM**: 8GB minimum, 16GB+ recommended (for Whisper + Ollama)
-   **Storage**: 20GB+ for Docker images and models
-   **Network**: Reliable internet connection for Tailscale
-   **OS**: Any Linux distribution with Docker support

### Raspberry Pi Requirements

#### Minimum
-   **Model**: Raspberry Pi 4B (4GB RAM) or Pi 5
-   **Storage**: 16GB+ microSD card (Class 10 or better)
-   **Audio**: USB microphone or compatible audio HAT
-   **Power**: Official Raspberry Pi power supply (5V, 3A)

#### Recommended
-   **Model**: Raspberry Pi 4B (8GB RAM) or Pi 5 (8GB)
-   **Storage**: 32GB+ microSD card (Class 10) or USB SSD
-   **Audio**: High-quality USB microphone array
-   **Display**: Small HDMI display for GUI (optional)
-   **Robot Components** (optional):
    -   Motor controller (e.g., L298N or TB6612FNG)
    -   DC motors with wheels
    -   Ultrasonic sensors
    -   LED indicators
    -   Battery pack for mobility

## Getting Started

### Prerequisites

#### Server
1. Linux machine with Docker and Docker Compose installed
2. At least 8GB RAM, 16GB+ recommended
3. Network connection
4. Tailscale installed and configured (optional but recommended)

#### Raspberry Pi
1. Raspberry Pi 4B or newer with Raspberry Pi OS installed
2. Python 3.9, 3.10, or 3.11 (not 3.12+ due to OpenWakeWord dependency)
3. Network connection (WiFi or Ethernet)
4. Audio input/output devices configured
5. Tailscale installed and configured

### Quick Start

#### 1. Local Development Setup

```bash
# Clone the repository
git clone https://github.com/pranavk-labs/H.E.N.R.Y..git
cd H.E.N.R.Y.

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies for local development
poetry install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your configuration

# Run development server (local mode)
poetry run python scripts/dev_server.py
```

#### 2. Server Deployment (Docker)

```bash
# Configure server environment
cp .env.server.example .env.server
# Edit .env.server with your configuration:
#   - Set STT_ENGINE=whisper
#   - Configure Neo4j connection
#   - Configure Ollama URL

# Update deployment configuration
cp .env.deploy.example .env.deploy
# Edit .env.deploy with your server details:
#   - SERVER_USER, SERVER_HOST, SERVER_PATH

# Deploy to server
bash scripts/deploy_to_server.sh

# The script will:
# - Copy files to server
# - Build Docker image
# - Start container with auto-restart
# - Run health checks
```

#### 3. Raspberry Pi Deployment

```bash
# Configure Pi environment
# Create .env.pi on your Pi with:
#   - STT_ENGINE=remote
#   - STT_SERVER_URL=http://your-server-ip:8000
#   - AUDIO_ENABLED=True

# Update deployment configuration (if not already done)
cp .env.deploy.example .env.deploy
# Edit .env.deploy with your Pi details:
#   - PI_USER, PI_HOST, PI_PATH

# Deploy to Pi
bash scripts/deploy_to_pi.sh

# The script will:
# - Copy files to Pi
# - Install dependencies (without server extras)
# - Set up systemd service
# - Start the voice interface
```

### Initial Setup

1. **Tailscale VPN** (recommended): Set up Tailscale on both server and Pi for secure communication
2. **Server Setup**:
   - Install Neo4j database
   - Install and configure Ollama with your preferred model
   - Configure `.env.server` with connection details
3. **Pi Audio Setup**: Configure microphone and speaker in Raspberry Pi OS
4. **Deploy**: Run deployment scripts for server, then Pi
5. **Test**: Trigger wake word and verify audio → server → response flow

For detailed setup instructions, see:
-   [Architecture Documentation](docs/architecture.md) - System design
-   [Development Guide](docs/development-guide.md) - Development workflow
-   [Deployment Guide](docs/phase-8-deployment.md) - Production deployment

## Project Structure

```
H.E.N.R.Y./
├── backend/              # Python backend services
│   ├── api/             # FastAPI application
│   ├── services/        # Core services (voice, knowledge, etc.)
│   ├── models/          # Data models
│   ├── integrations/    # External service integrations
│   └── robot/           # Robot control code
├── mobile/              # Mobile companion apps
│   ├── flutter/         # Flutter app
│   └── swift/           # Swift iOS app
├── docs/                # Documentation
│   ├── phase-*.md       # Phase-based development guides
│   ├── architecture.md  # System architecture
│   └── development-guide.md
├── scripts/             # Utility scripts
├── config/              # Configuration files
└── tests/               # Test suites
```

## Documentation

Comprehensive documentation is organized by development phases:

-   **[Phase 1: Foundation](docs/phase-1-foundation.md)** - Project setup, Pi configuration, backend foundation
-   **[Phase 2: Core Features](docs/phase-2-core-features.md)** - Graph knowledge system, productivity tools
-   **[Phase 3: Personality & Voice](docs/phase-3-personality-voice.md)** - Conversational interface, personality system
-   **[Phase 4: Pi Services](docs/phase-4-pi-services.md)** - Service architecture, always-on systems
-   **[Phase 5: Integrations](docs/phase-5-integrations.md)** - Beeper, n8n, home automation
-   **[Phase 6: Robot Features](docs/phase-6-robot-features.md)** - Physical components, movement, sensors
-   **[Phase 7: Companion App](docs/phase-7-companion-app.md)** - Mobile app development
-   **[Phase 8: Deployment](docs/phase-8-deployment.md)** - Production deployment, optimization
-   **[Architecture](docs/architecture.md)** - System design and architecture
-   **[Development Guide](docs/development-guide.md)** - Development workflow and guidelines

## Contributing

H.E.N.R.Y. is open source and welcomes contributions! However, keep in mind that this project is designed to be personalized—your contributions will help make H.E.N.R.Y. better for everyone while remaining customizable for individual use.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Contribution Guidelines

-   Follow the code style guidelines in [Development Guide](docs/development-guide.md)
-   Write tests for new features
-   Update documentation as needed
-   Ensure Raspberry Pi compatibility
-   Consider personalization hooks for new features

## Roadmap

### Phase 1: Foundation ✅

-   [x] Project setup and architecture
-   [x] Raspberry Pi OS configuration
-   [x] Backend API foundation
-   [x] Graph database setup

### Phase 2: Core Features 🚧

-   [ ] Graph-based knowledge system
-   [ ] Productivity tools (Pomodoro, idea storage)
-   [ ] Core API endpoints

### Phase 3: Personality & Voice 🚧

-   [ ] Conversational interface
-   [ ] Personality system
-   [ ] Voice recognition and synthesis
-   [ ] Context management

### Phase 4: Pi Services 📋

-   [ ] Service architecture
-   [ ] Always-on voice listening
-   [ ] Resource optimization

### Phase 5: Integrations 📋

-   [ ] Beeper/Matrix integration
-   [ ] n8n automation
-   [ ] Home management systems

### Phase 6: Robot Features 📋

-   [ ] Motor control
-   [ ] Sensor integration
-   [ ] Physical personality expression

### Phase 7: Companion App 📋

-   [ ] Flutter mobile app
-   [ ] Swift iOS app
-   [ ] Remote synchronization

### Phase 8: Deployment 📋

-   [ ] Production deployment guide
-   [ ] Performance optimization
-   [ ] Monitoring and maintenance

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

-   Built with ❤️ for personal productivity and home automation
-   Inspired by the need for privacy-focused, self-hosted assistants
-   Thanks to the open-source community for amazing tools and libraries

## Contact & Support

-   **Repository**: [GitHub](https://github.com/pranavk-labs/H.E.N.R.Y.)
-   **Issues**: [GitHub Issues](https://github.com/pranavk-labs/H.E.N.R.Y./issues)

---

**Note**: H.E.N.R.Y. is designed to run on your home network. While cloud services can be integrated, the core philosophy is local-first, giving you full control over your data and privacy.
