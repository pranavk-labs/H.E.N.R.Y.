# Phase 2: Core Features

## Objectives and Goals

Phase 2 implements the core functionality of H.E.N.R.Y., focusing on the graph-based knowledge representation system and essential productivity tools. This phase establishes the foundation for intelligent, context-aware interactions.

### Key Objectives

-   Implement graph-based knowledge representation system (connecting to Neo4j on home server)
-   Create a extensible **tools library** (Pomodoro timer, idea notebook, and future tools) callable from the voice layer
-   Design and implement data models and schemas
-   Build API endpoints for core features
-   Implement connection management and fallback mechanisms
-   Establish service architecture patterns with remote services (Neo4j, Ollama, PostgreSQL on home server)

## Core Features

### 1. Graph-Based Knowledge Representation System

**Knowledge Graph Schema:**

-   **Node Types**: User, Preference, Habit, Idea, Task, Project, Context, Concept, Tag
-   **Relationship Types**: HAS_PREFERENCE, HAS_HABIT, CREATED, RELATED_TO, OCCURS_IN, TRIGGERS, PREFERS, TAGGED_WITH
-   **Properties**: Support for temporal data, strength/weight values, metadata

**Core Capabilities:**

-   Store and retrieve user preferences with strength values
-   Link concepts and ideas with relationships
-   Track contextual information (time, location, activity)
-   Build knowledge graph from user interactions
-   Query related concepts and patterns
-   Support for temporal queries (when things happen)

### 2. Productivity Tools

**Tools Library and Directory:**

-   Define a common **tool interface** (input, output, execution context) for all productivity tools
-   Implement a **tools registry** that discovers and exposes tools (e.g., `TimerTool`, `IdeaTool`) to H.E.N.R.Y.'s voice layer
-   Allow tools to **update the screen manager / GUI** (e.g., active view, status text, timers, idea notebook panes)
-   Allow tools to call into backend services and remote databases (Neo4j for graph, PostgreSQL for structured tool data)
-   Keep tools as **library components first**, with optional thin API endpoints when remote access is useful

**Pomodoro Timer:**

-   Start/stop/pause/resume functionality
-   Configurable work and break durations
-   Session tracking and statistics
-   Integration with knowledge graph (track work patterns)
-   Voice control support (to be enhanced in Phase 3)
-   Implemented as a `TimerTool` in the tools library, invokable directly by the voice/command layer and able to update the GUI

**Idea Storage System:**

-   Text-based idea capture into a **virtual notebook**
-   Ability to iteratively **refine an idea in-place** (frontend-driven UX) before sending it to "build"
-   Backend support for **storing raw ideas plus basic metadata** (e.g., id, created_at, tags, notebook reference)
-   Tag-based organization
-   Search and retrieval capabilities
-   Relationship linking between ideas
-   Temporal tracking (when ideas were created)
-   Integration with knowledge graph for concept extraction
-   No offline mode required; ideas are stored in the online backend only
-   Implemented as an `IdeaTool` in the tools library, which can drive virtual notebook views in the GUI and persist data via backend services

### 3. Data Models and Schemas

**Core Models:**

-   User model (extended from Phase 1)
-   Idea model (text, tags, metadata, relationships)
-   Preference model (type, value, strength)
-   Pomodoro session model (status, duration, timestamps)
-   Concept model (name, relationships, metadata)

**Database Schema:**

-   Constraints for unique identifiers
-   Indexes for common queries
-   Relationship properties for metadata
-   Temporal data support
-   PostgreSQL schema on the home server (via Tailscale) for structured tool data (Pomodoro sessions, idea notebook entries and metadata)

### 4. API Endpoints

**Knowledge Graph Endpoints:**

-   Create/read/update preferences
-   Store and retrieve ideas
-   Link concepts and ideas
-   Query related concepts
-   Get user context

**Productivity Endpoints:**

-   Pomodoro session management (start, pause, complete, get status)
-   Idea management (create, list, search, update, delete)
-   Statistics and analytics endpoints

### 5. Local Storage and Synchronization

**Cache Service:**

-   Cache frequently accessed data for performance
-   Cache invalidation strategies
-   Performance optimization (no offline persistence required)

**Synchronization (online-only):**

-   Network-efficient architecture
-   Background sync capabilities if additional services are introduced
-   Conflict resolution strategies
-   Data consistency checks

### 6. Service Architecture

**Service Layer Pattern:**

-   Consistent service interface
-   Error handling and logging
-   Database abstraction
-   Cache integration

**Tools Architecture:**

-   Tools directory with clearly defined, pluggable tools (e.g., `TimerTool`, `IdeaTool`) following a shared interface
-   Central **tools registry/service** responsible for discovering, registering, and invoking tools
-   Integration points for the **voice pipeline** (wake word → NLU → tool invocation)
-   Hooks for the **screen manager / GUI** so tools can declaratively request UI changes
-   Access to backend services (Neo4j, Ollama, PostgreSQL) through injected service clients rather than direct network calls

**Background Processing:**

-   Task queue implementation
-   Async processing for heavy operations
-   Background knowledge graph updates
-   Statistics calculation

## Execution Strategy

### Step 1: Knowledge Graph Schema Design

1. Define all node types and their properties
2. Define all relationship types and their properties
3. Design constraints and indexes for Neo4j
4. Create schema initialization script (runs on home server)
5. Test schema creation and queries via Tailscale connection
6. Document schema structure

### Step 2: Knowledge Service Implementation

1. Create knowledge service class with Neo4j client
2. Implement connection management (Tailscale to home server)
3. Add connection health checks and retry logic
4. Implement preference management methods (Cypher queries)
5. Implement idea storage and retrieval (Cypher queries) suitable for virtual notebook flows
6. Implement concept linking and querying (Cypher queries)
7. Implement context tracking
8. Add caching for performance (no offline mode)
9. Add error handling, logging, and graceful degradation

### Step 3: Productivity Tools - Pomodoro Timer

1. Design Pomodoro data model (including PostgreSQL tables for session storage on the home server)
2. Implement `TimerTool` in the tools library (shared tool interface + registry registration)
3. Create Pomodoro service for lower-level persistence/logic
4. Implement session lifecycle (start, pause, complete)
5. Add session persistence to knowledge graph and PostgreSQL as appropriate
6. (Optional) Create API endpoints as thin wrappers around the timer tool/service
7. Add statistics tracking

### Step 4: Productivity Tools - Idea Storage

1. Design idea data model (graph-level in Neo4j plus PostgreSQL tables for notebook entries and metadata)
2. Implement `IdeaTool` in the tools library (integrated with knowledge service and tools registry)
3. Create idea service for persistence and graph/PostgreSQL coordination
4. Implement CRUD operations
5. Add tag management
6. Implement search functionality (graph, PostgreSQL, or combined)
7. (Optional) Create API endpoints as thin wrappers around the idea tool/service

### Step 5: API Endpoints

1. Create knowledge graph routes
2. Create productivity routes
3. Add authentication middleware
4. Implement request validation
5. Add error handling
6. Create API documentation

### Step 6: Local Storage and Cache

1. Design cache service interface
2. Implement local file-based cache
3. Add cache expiration logic
4. Integrate cache with services
5. Add cache management endpoints

### Step 7: Service Architecture

1. Establish base service class pattern
2. Implement consistent error handling
3. Add logging infrastructure
4. Create background task queue
5. Implement async processing patterns
6. Implement tools registry and base tool abstractions
7. Wire tools into the voice pipeline and screen manager / GUI integration points

### Step 8: Testing and Integration

1. Write unit tests for services
2. Write integration tests for API endpoints
3. Test knowledge graph queries
4. Test Pomodoro timer lifecycle
5. Test idea storage and retrieval
6. Performance testing

## Testing Requirements

### Unit Tests

-   Knowledge service methods (preferences, ideas, concepts)
-   Pomodoro service logic (session management, timing)
-   Data model validation
-   Cache service operations
-   Service error handling
-   Tools library (tool base class, registry, and `TimerTool` / `IdeaTool` behavior)

### Integration Tests

-   API endpoints with database
-   Knowledge graph queries and relationships
-   Pomodoro session persistence
-   Idea storage and retrieval
-   Tag management
-   Search functionality
-   End-to-end tool invocation flows (voice/command layer → tools registry → tool → backend/GUI)

### Performance Tests

-   Knowledge graph query performance
-   Concurrent API requests
-   Cache hit/miss rates
-   Database connection pooling

### Manual Testing

-   Create and retrieve ideas via API
-   Start and complete Pomodoro sessions
-   Link concepts and query relationships
-   Test search functionality
-   Verify data persistence

## Completion Criteria

Phase 2 is complete when:

-   [x] Knowledge graph schema is defined and initialized (implicit via node creation; labels: Idea, Preference, User; relationships: HAS_PREFERENCE)
-   [x] Knowledge service is implemented with all core methods (KnowledgeService with ideas, preferences, graph operations)
-   [x] Preference management is working (set_preference, get_preferences implemented)
-   [x] Idea storage and retrieval is functional (create, get, list, update, delete, search all working)
-   [x] Concept linking and querying works (via graph relationships; \_create_relationship, \_get_neighbors implemented)
-   [x] Pomodoro timer tool is fully functional (TimerTool with start, pause, resume, complete, status, list)
-   [x] Pomodoro API endpoints are working (all 7 endpoints: start, pause, resume, complete, get, list)
-   [x] Idea API endpoints are working (all 6 endpoints: create, list, search, get, update, delete)
-   [x] Local cache service is implemented (CacheService with TTL support)
-   [x] Service architecture patterns are established (ToolsService, KnowledgeService, ToolsRegistry)
-   [x] All API endpoints are documented (FastAPI auto-docs at /docs)
-   [x] All tests pass (27 tests passing)
-   [x] Performance is acceptable for Pi hardware (async operations, local fallback, efficient queries)
-   [x] Documentation is updated (tools/README.md, API docs, test scripts)

## Questions to Answer

1. **Neo4j Connection**: Verify Tailscale connection to home server is stable
2. **Query Performance**: Test query latency over Tailscale (should be <50ms typically)
3. **Idea Storage**: Should ideas support rich text/markdown or plain text only?
4. **Pomodoro Persistence**: How long should Pomodoro sessions be stored? (for statistics)
5. **Cache Strategy**: What data should be cached and for how long?
6. **Search Implementation**: Full-text search in Neo4j or external search engine?
7. **Tag Management**: Hierarchical tags or flat tag system?
8. **Statistics**: What statistics should be tracked for Pomodoro and ideas?
9. **Performance**: What are acceptable response times for queries on Pi hardware?
10. **Service Integration**: What other services (if any) should be integrated into the idea "build" flow?

## Next Steps

After completing Phase 2, proceed to:

-   **[Phase 3: Personality & Voice](phase-3-personality-voice.md)** - Implement conversational interface and personality system
-   Enhance knowledge graph with conversation context
-   Begin planning voice interaction patterns

## Troubleshooting

### Common Issues

**Knowledge graph queries are slow:**

-   Check Tailscale connection latency
-   Optimize Cypher queries
-   Add appropriate indexes in Neo4j
-   Consider caching frequently accessed data on Pi
-   Review graph size and complexity
-   Check home server performance

**Pomodoro timer not persisting:**

-   Check database connection
-   Verify session storage in graph
-   Check for timezone issues
-   Verify transaction handling

**Idea retrieval not working:**

-   Verify Tailscale connection to home server
-   Check Neo4j connection and authentication
-   Verify Neo4j constraints are created on home server
-   Check query syntax (Cypher)
-   Verify user relationships in graph
-   Test connection: `cypher-shell -a bolt://home-server-ip:7687`

**Cache issues:**

-   Verify file permissions
-   Check disk space
-   Review cache expiration logic
-   Check cache directory structure
