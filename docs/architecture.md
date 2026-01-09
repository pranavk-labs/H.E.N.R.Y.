# Architecture

## System Overview

H.E.N.R.Y. follows a distributed architecture with the Raspberry Pi as the voice interface hub and a home server handling resource-intensive services. The Pi manages voice I/O, robot control, and API gateway functions, while the home server (accessible via Tailscale VPN) runs the LLM (Ollama) and Graph Database (Neo4j). This architecture optimizes resource usage while maintaining local-first, privacy-focused operation.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Raspberry Pi (Assistant Hub)                   │
│                                                             │
│  ┌──────────────┐  ┌──────────────────────────┐           │
│  │   Backend    │  │   Native UI (Python GUI) │           │
│  │   (FastAPI)  │  │   Face + Tools Display   │           │
│  └──────────────┘  └──────────────────────────┘           │
│        │                        ▲                         │
│        │ ToolsService /         │ ScreenManager           │
│        ▼                        │                         │
│  ┌──────────────┐        ┌──────────────┐                  │
│  │  Tools       │        │ Screen       │                  │
│  │  (Timer,     │        │ Manager      │                  │
│  │   Ideas, …)  │        └──────────────┘                  │
│  └──────────────┘                                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Voice/STT   │  │  Knowledge   │  │  Audio I/O   │      │
│  │  Pipeline    │  │  Service     │  │  Service     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                        ↕  (Tailscale VPN)
        ┌──────────────────────────┐
        │       Home Server        │
        │                          │
        │  ┌──────────────┐        │
        │  │  LLM Service │        │
        │  │  (Ollama)    │        │
        │  └──────────────┘        │
        │  ┌──────────────┐        │
        │  │  Graph DB    │        │
        │  │  (Neo4j)     │        │
        │  └──────────────┘        │
        └──────────────────────────┘
```

## Component Architecture

### Backend API (FastAPI)

**Responsibilities:**

-   HTTP API endpoints
-   Request routing and validation
-   Service orchestration
-   Error handling

**Key Components:**

-   API routes (REST endpoints)
-   Middleware (CORS, logging)
-   Service layer integration
-   Request/response models

**Note**: Authentication is not required for single-user local system. Can be added later if multi-user or remote access is needed.

### Voice Service

**Responsibilities:**

-   Always-on audio capture for wake word detection
-   Wake word detection (HENRY only processes when name is called)
-   Speech-to-text conversion (activated after wake word)
-   Text-to-speech synthesis
-   Audio processing pipeline
-   Conversation management

**Key Components:**

-   Wake word detection service
-   Audio capture service
-   STT engine integration
-   TTS engine integration
-   Conversation state manager
-   Audio queue manager

### Knowledge & Tools Layer

**Responsibilities:**

-   Graph database operations (Neo4j via `Neo4jClient` with local `GraphFallback` fallback)
-   Knowledge graph queries
-   Idea and preference management
-   Context and relationship management
-   Tool orchestration

**Key Components:**

-   `KnowledgeService` (ideas, preferences, graph ops)
-   `Neo4jClient` (remote graph DB on home server)
-   `GraphFallback` (NetworkX + SQLite cache)
-   `ToolsRegistry` / `ToolsService` (tool lookup + invocation)
-   Tools library (`TimerTool`, `IdeaTool`, future tools)
-   `ScreenManager` (single source of truth for current UI state, used by the native Python GUI and future touchscreen interactions)

### Personality System

**Responsibilities:**

-   Personality trait management
-   Response generation with personality
-   Personality adaptation
-   Context-aware behavior
-   Learning from interactions

**Key Components:**

-   Personality configuration
-   Response generator (integrated with Ollama)
-   Trait selector
-   Adaptation engine
-   Learning system
-   LLM integration (Ollama client)

### Integration Service (Future Phases)

**Responsibilities:**

-   External service connections
-   Webhook handling
-   Event processing
-   API client management
-   Service discovery

**Key Components:**

-   Integration clients
-   Webhook handlers
-   Event bus
-   Service discovery
-   Authentication managers

### Robot Control Service (Future Phases)

**Responsibilities:**

-   Motor control
-   Sensor reading
-   Movement patterns
-   Safety mechanisms
-   GPIO management

**Key Components:**

-   Motor controller
-   Sensor manager
-   Movement executor
-   Safety monitor
-   GPIO service

## Data Flow

### Voice Interaction Flow

```
User Voice → Audio Capture → Wake Word Detection → STT (Whisper) → Intent Recognition →
Knowledge Query → LLM Processing (Ollama) → Personality Injection →
Response Generation → TTS → Audio Output → User
```

**Note**: HENRY only processes audio when wake word is detected (e.g., "Hey HENRY")

### Knowledge Graph Flow

```
User Interaction → Entity Extraction → Knowledge Service →
Graph Query/Update → Context Update → Response Enhancement
```

### Integration Flow

```
External Event → Webhook/API → Integration Service →
Event Bus → Relevant Service → Action/Response
```

## Critical Architectural Decisions

### Graph Database: On-Pi vs External

**Decision: Lightweight Graph Storage on Pi (NetworkX + SQLite)**

**Analysis:**

-   **Neo4j on Pi**: Requires 1-2GB RAM minimum, can be resource-intensive
-   **Single-user system**: Doesn't need enterprise-grade graph database
-   **Pi constraints**: Limited RAM (4-8GB total) must be shared with LLM, STT, and other services

**Solution:**

-   **Primary**: NetworkX (in-memory graph) + SQLite (persistence)
    -   Memory efficient (~200-500MB vs 1-2GB)
    -   Python-native, easy integration
    -   Sufficient for single-user knowledge graph
    -   Fast for small-medium graphs (<100K nodes)
-   **Alternative**: External Neo4j on NAS/PC/second Pi
    -   Better for complex queries
    -   Better for larger graphs
    -   Adds network dependency
    -   More complex deployment

**Migration Path:**

-   Start with NetworkX + SQLite
-   Can migrate to external Neo4j if:
    -   Graph grows beyond NetworkX efficiency
    -   Need complex Cypher queries
    -   Want better query performance
    -   Moving to multi-user system

### LLM: Local (Ollama) vs Cloud

**Decision: Ollama (Local) with Optional Cloud Fallback**

**Analysis:**

**Ollama (Local) - Recommended:**

-   ✅ **Privacy**: All data stays local, no API calls
-   ✅ **Cost**: No per-request costs, one-time setup
-   ✅ **Latency**: Low latency (no network round-trip)
-   ✅ **Offline**: Works without internet
-   ✅ **Control**: Full control over models and behavior
-   ⚠️ **Limitations**:
    -   Limited model size on Pi (3-7B parameters max)
    -   Requires quantization (Q4/Q5)
    -   Slower inference than cloud
    -   Higher memory usage (2-4GB RAM)

**Langchain + Cloud (OpenAI/Anthropic):**

-   ✅ **Quality**: Access to best models (GPT-4, Claude)
-   ✅ **Performance**: Fast inference, no local compute
-   ✅ **Updates**: Always latest models
-   ❌ **Privacy**: Data sent to third parties
-   ❌ **Cost**: Per-request pricing, can add up
-   ❌ **Latency**: Network round-trip adds delay
-   ❌ **Dependency**: Requires internet connection
-   ❌ **Control**: Limited control over model behavior

**Recommended Approach:**

-   **Primary**: Ollama with quantized models (Q4)
    -   Llama 3.2 3B or Mistral 7B Q4
    -   ~2-4GB RAM usage
    -   Good quality for conversational AI
-   **Fallback**: Optional cloud API integration
    -   For complex reasoning tasks
    -   When local model quality insufficient
    -   As backup when Ollama unavailable
-   **Hybrid**: Use local for most operations, cloud for specific complex tasks

**Model Selection for Pi:**

-   **3B models** (Llama 3.2 3B, Phi-3 Mini): Best for 4GB Pi, faster inference
-   **7B models** (Mistral 7B, Llama 3.1 7B): Better quality, needs 8GB Pi
-   **Quantization**: Q4 (4-bit) recommended, Q5 (5-bit) if RAM allows
-   **Avoid**: 13B+ models (too large for Pi), unquantized models (too much RAM)

## Technology Choices Rationale

### Backend: Python/FastAPI

-   **Rationale**: Fast development, excellent libraries, good for Pi hardware
-   **Alternatives Considered**: Node.js, Go
-   **Decision**: Python ecosystem best for ML/AI, audio processing, hardware control

### Graph Database: Lightweight Graph Storage

-   **Rationale**: Neo4j is resource-intensive for Pi (1-2GB RAM minimum). For single-user system, lighter solution preferred.
-   **Primary Option**: NetworkX (in-memory) + SQLite (persistence) - Lightweight, Python-native, sufficient for single-user
-   **Alternative Option**: Neo4j on external device (NAS, PC, or second Pi) - Better for complex queries, but adds network dependency
-   **Decision**: Start with NetworkX + SQLite on Pi. Can migrate to external Neo4j if needed for complex queries or multi-user.
-   **Benefits**: Lower memory footprint (~100-200MB vs 1-2GB), faster startup, simpler deployment
-   **Trade-offs**: Less powerful query language, manual relationship management

### Voice: Whisper (STT)

-   **Rationale**: High accuracy, offline capability, open source
-   **Alternatives Considered**: Cloud STT services, DeepSpeech
-   **Decision**: Whisper offers best balance of accuracy and privacy

### LLM: Ollama (Local)

-   **Rationale**: Local-first, privacy-focused, no ongoing costs, low latency, works offline
-   **Alternatives Considered**: Langchain + Cloud providers (OpenAI, Anthropic), Hugging Face
-   **Decision**: Ollama for primary LLM operations, with optional cloud fallback for complex tasks
-   **Model Selection**: Use quantized models (Q4/Q5) suitable for Pi:
    -   **Recommended**: Llama 3.2 3B (Q4) or Mistral 7B (Q4) - Good balance of quality and performance
    -   **Alternative**: Phi-3 Mini (3.8B Q4) - Very efficient, good for Pi
-   **Resource Usage**: ~2-4GB RAM for Q4 models, ~4-6GB for Q5 models
-   **Hybrid Approach**: Use Ollama for most operations, optional cloud API for:
    -   Complex reasoning tasks (if needed)
    -   When local model quality insufficient
    -   Fallback when Ollama unavailable
-   **Benefits**: Complete privacy, no API costs, works offline, fast response times
-   **Trade-offs**: Limited model size on Pi, requires careful model selection, may need quantization

### Mobile: Flutter

-   **Rationale**: Cross-platform, single codebase, good performance
-   **Alternatives Considered**: React Native, native Swift/Kotlin
-   **Decision**: Flutter provides best cross-platform experience

## Scalability Considerations

### Current Design (Single User)

-   Optimized for single user on Raspberry Pi
-   All services on one device
-   Local network operation

### Future Scaling Options

-   **Multi-user**: Add user management and isolation
-   **Distributed**: Move some services to separate devices
    -   **Graph DB**: Move to external Neo4j on NAS/PC for complex queries
    -   **LLM**: Keep on Pi (Ollama) or move to more powerful device
-   **Cloud Offload**: Move heavy processing to cloud (if desired)
    -   **LLM**: Optional cloud API fallback for complex tasks
    -   **STT**: Keep Whisper local for privacy
-   **Clustering**: Multiple Pi instances (unlikely needed)
-   **Hardware Upgrade**: Pi 5 or more powerful SBC for better LLM performance

## Security Architecture

### Authentication

-   **Not required for single-user local system**
-   Can be added later if multi-user or remote access is needed
-   Optional: Simple API key for mobile app access (if needed)

### Network Security

-   Local network operation (primary)
-   Optional TLS/SSL for remote access
-   Firewall configuration
-   Service isolation

### Data Security

-   Local-first data storage
-   Encrypted sensitive data
-   Secure backup procedures
-   Access logging

## Performance Considerations

### Raspberry Pi Constraints

-   Limited CPU (4-8 cores)
-   Limited RAM (4-8GB) - **Critical constraint for LLM + Graph DB**
-   Limited storage (microSD or USB SSD)
-   Thermal constraints

### Resource Allocation (Recommended for Pi 4 8GB)

-   **LLM (Ollama)**: 3-4GB RAM (Q4 quantized model)
-   **Graph DB (NetworkX)**: 200-500MB RAM (in-memory)
-   **Backend API**: 200-300MB RAM
-   **Voice/STT**: 500MB-1GB RAM (Whisper model)
-   **System/O.S.**: 1-2GB RAM
-   **Total**: ~5-8GB (tight on 4GB Pi, comfortable on 8GB Pi)

### Optimizations

-   Efficient audio processing
-   Optimized database queries (NetworkX operations)
-   Caching strategies
-   Background task throttling
-   Model quantization (STT/TTS/LLM)
-   Graph DB: Use NetworkX + SQLite instead of Neo4j
-   LLM: Use Q4 quantized models, consider smaller models (3B parameters)
-   Memory management: Aggressive cleanup, limit context windows

## Deployment Architecture

### Development

-   Direct development on Pi or remote SSH
-   Hot reload for API
-   Development database
-   Debug logging

### Production

-   systemd services
-   Production database configuration
-   Optimized performance settings
-   Monitoring and logging
-   Backup procedures

## Component Interactions

### Service Communication

-   Direct function calls (same process)
-   Event bus for async communication
-   Database for shared state
-   WebSocket for real-time updates

### External Communication

-   REST API for mobile app
-   WebSocket for real-time sync
-   Webhooks for external services
-   mDNS for service discovery

## Data Architecture

### Knowledge Graph Schema

-   **Storage**: NetworkX graph (in-memory) + SQLite (persistence)
-   **Nodes**: User, Idea, Concept, Preference, Context, etc.
-   **Relationships**: HAS, CREATED, RELATED_TO, OCCURS_IN, etc.
-   **Properties**: Temporal data, strength values, metadata
-   **Persistence**: Serialize NetworkX graph to SQLite periodically
-   **Alternative**: External Neo4j on NAS/PC if complex queries needed

### Local Storage

-   Configuration files (.env)
-   Cache files (local cache)
-   Logs (rotated)
-   Backups (scheduled)

## Failure Handling

### Service Failures

-   Auto-restart via systemd
-   Graceful degradation
-   Error logging
-   Recovery procedures

### Network Failures

-   Offline mode support
-   Queue commands for when online
-   Connection retry logic
-   Status indicators

### Hardware Failures

-   Sensor failure handling
-   Motor failure detection
-   Audio device fallback
-   System health monitoring
