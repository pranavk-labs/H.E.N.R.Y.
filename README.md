# H.E.N.R.Y. (Acronym unknown so far)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
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

H.E.N.R.Y. follows a hub-and-spoke architecture with the Raspberry Pi as the central hub:

```
┌─────────────────────────────────────────────────────────┐
│              Raspberry Pi (Central Hub)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Backend    │  │  Voice/STT   │  │  Graph DB    │  │
│  │   (Python)   │  │   Service    │  │  (Neo4j)     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Robot       │  │  Integrations│  │  Automation  │  │
│  │  Control     │  │  (n8n, etc)  │  │  Engine      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                        ↕
        ┌───────────────────────────────┐
        │   Mobile Companion App        │
        │   (Flutter/Swift)            │
        └───────────────────────────────┘
```

### Components

-   **Backend API** (Python/FastAPI): Core service layer handling all requests
-   **Voice Service**: Always-on speech-to-text and text-to-speech
-   **LLM Service** (Ollama): Local language model for conversational AI
-   **Graph Database**: NetworkX + SQLite (lightweight, on-Pi) or external Neo4j (optional)
-   **Robot Controller**: GPIO-based motor and sensor control
-   **Integration Layer**: Webhooks and APIs for external services
-   **Mobile App**: Flutter (cross-platform) and Swift (iOS native) options

## Tech Stack

### Backend (Raspberry Pi)

-   **Language**: Python 3.9+
-   **Framework**: FastAPI
-   **Graph Database**: NetworkX + SQLite (primary, on-Pi) or Neo4j (optional, external)
-   **LLM**: Ollama with quantized models (Llama 3.2 3B Q4 or Mistral 7B Q4)
-   **Voice Processing**:
    -   Speech-to-Text: Whisper (offline)
    -   Text-to-Speech: pyttsx3/Coqui TTS
-   **Hardware Control**: RPi.GPIO, gpiozero
-   **Service Management**: systemd

### Mobile Companion

-   **Cross-platform**: Flutter (iOS/Android)
-   **iOS Native**: Swift (optional)
-   **Communication**: WebSocket/HTTP REST API

### Infrastructure

-   **OS**: Raspberry Pi OS (64-bit recommended)
-   **Containerization**: Docker (optional)
-   **Process Management**: systemd
-   **Network**: Local network with optional cloud sync

## Hardware Requirements

### Minimum Requirements

-   **Raspberry Pi**: 4B (8GB RAM recommended) or Pi 5 (4GB minimum, 8GB recommended)
-   **Storage**: 32GB+ microSD card (Class 10 or better)
-   **Audio**: USB microphone or compatible audio HAT
-   **Power**: Official Raspberry Pi power supply (5V, 3A)

### Recommended

-   **Raspberry Pi**: 4B (8GB RAM) or Pi 5 (8GB recommended for LLM)
-   **Storage**: 64GB+ microSD card (Class 10) or USB SSD
-   **Audio**: High-quality USB microphone array
-   **Robot Components**:
    -   Motor controller (e.g., L298N or TB6612FNG)
    -   DC motors with wheels
    -   Ultrasonic sensors (optional)
    -   LED indicators
    -   Battery pack for mobility

## Getting Started

### Prerequisites

1. Raspberry Pi 4B or newer with Raspberry Pi OS installed
2. Python 3.9+ installed
3. Network connection (WiFi or Ethernet)
4. Audio input/output devices configured

### Installation

```bash
# Clone the repository
git clone https://github.com/pranavk-labs/H.E.N.R.Y..git
cd H.E.N.R.Y.

# Install Poetry (if not already installed)
# macOS/Linux: curl -sSL https://install.python-poetry.org | python3 -
# Windows: (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Install dependencies (Poetry creates virtual environment automatically)
poetry install

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database
poetry run python scripts/init_db.py

# Start services
sudo systemctl enable henry.service
sudo systemctl start henry.service
```

### Initial Setup

1. **Configure Audio**: Set up microphone and speaker in Raspberry Pi OS
2. **Network Setup**: Ensure Pi is accessible on your local network
3. **Database Setup**: Initialize graph database (NetworkX + SQLite) or connect to external Neo4j
4. **LLM Setup**: Install Ollama and download quantized model
5. **Voice Training**: Complete initial voice recognition setup
6. **Mobile App**: Connect companion app to Pi's IP address

For detailed setup instructions, see:

-   [Phase 1: Foundation](docs/phase-1-foundation.md) - Complete setup guide
-   [Local Development Guide](docs/local-development.md) - Develop locally, deploy to Pi
-   [Poetry Setup Guide](docs/poetry-setup.md) - Package management with Poetry

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
