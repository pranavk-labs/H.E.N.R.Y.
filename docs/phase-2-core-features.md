# Phase 2: Core Features

## Objectives and Goals

Phase 2 implements the core functionality of H.E.N.R.Y., focusing on the graph-based knowledge representation system and essential productivity tools. This phase establishes the foundation for intelligent, context-aware interactions.

### Key Objectives

- Implement graph-based knowledge representation system (connecting to Neo4j on home server)
- Create core productivity tools (Pomodoro timer, idea storage)
- Design and implement data models and schemas
- Build API endpoints for core features
- Implement connection management and fallback mechanisms
- Establish service architecture patterns with remote services

## Core Features

### 1. Graph-Based Knowledge Representation System

**Knowledge Graph Schema:**
- **Node Types**: User, Preference, Habit, Idea, Task, Project, Context, Concept, Tag
- **Relationship Types**: HAS_PREFERENCE, HAS_HABIT, CREATED, RELATED_TO, OCCURS_IN, TRIGGERS, PREFERS, TAGGED_WITH
- **Properties**: Support for temporal data, strength/weight values, metadata

**Core Capabilities:**
- Store and retrieve user preferences with strength values
- Link concepts and ideas with relationships
- Track contextual information (time, location, activity)
- Build knowledge graph from user interactions
- Query related concepts and patterns
- Support for temporal queries (when things happen)

### 2. Productivity Tools

**Pomodoro Timer:**
- Start/stop/pause/resume functionality
- Configurable work and break durations
- Session tracking and statistics
- Integration with knowledge graph (track work patterns)
- Voice control support (to be enhanced in Phase 3)

**Idea Storage System:**
- Text-based idea capture
- Tag-based organization
- Search and retrieval capabilities
- Relationship linking between ideas
- Temporal tracking (when ideas were created)
- Integration with knowledge graph for concept extraction

### 3. Data Models and Schemas

**Core Models:**
- User model (extended from Phase 1)
- Idea model (text, tags, metadata, relationships)
- Preference model (type, value, strength)
- Pomodoro session model (status, duration, timestamps)
- Concept model (name, relationships, metadata)

**Database Schema:**
- Constraints for unique identifiers
- Indexes for common queries
- Relationship properties for metadata
- Temporal data support

### 4. API Endpoints

**Knowledge Graph Endpoints:**
- Create/read/update preferences
- Store and retrieve ideas
- Link concepts and ideas
- Query related concepts
- Get user context

**Productivity Endpoints:**
- Pomodoro session management (start, pause, complete, get status)
- Idea management (create, list, search, update, delete)
- Statistics and analytics endpoints

### 5. Local Storage and Synchronization

**Local Cache Service:**
- Cache frequently accessed data
- Offline storage capabilities
- Cache invalidation strategies
- Performance optimization

**Synchronization:**
- Local-first architecture
- Background sync capabilities
- Conflict resolution strategies
- Data consistency checks

### 6. Service Architecture

**Service Layer Pattern:**
- Consistent service interface
- Error handling and logging
- Database abstraction
- Cache integration

**Background Processing:**
- Task queue implementation
- Async processing for heavy operations
- Background knowledge graph updates
- Statistics calculation

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
5. Implement idea storage and retrieval (Cypher queries)
6. Implement concept linking and querying (Cypher queries)
7. Implement context tracking
8. Add local fallback cache (NetworkX) for offline mode
9. Add error handling, logging, and graceful degradation

### Step 3: Productivity Tools - Pomodoro Timer
1. Design Pomodoro data model
2. Create Pomodoro service
3. Implement session lifecycle (start, pause, complete)
4. Add session persistence to knowledge graph
5. Create API endpoints
6. Add statistics tracking

### Step 4: Productivity Tools - Idea Storage
1. Design idea data model
2. Create idea service (integrated with knowledge service)
3. Implement CRUD operations
4. Add tag management
5. Implement search functionality
6. Create API endpoints

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

### Step 8: Testing and Integration
1. Write unit tests for services
2. Write integration tests for API endpoints
3. Test knowledge graph queries
4. Test Pomodoro timer lifecycle
5. Test idea storage and retrieval
6. Performance testing

## Testing Requirements

### Unit Tests
- Knowledge service methods (preferences, ideas, concepts)
- Pomodoro service logic (session management, timing)
- Data model validation
- Cache service operations
- Service error handling

### Integration Tests
- API endpoints with database
- Knowledge graph queries and relationships
- Pomodoro session persistence
- Idea storage and retrieval
- Tag management
- Search functionality

### Performance Tests
- Knowledge graph query performance
- Concurrent API requests
- Cache hit/miss rates
- Database connection pooling

### Manual Testing
- Create and retrieve ideas via API
- Start and complete Pomodoro sessions
- Link concepts and query relationships
- Test search functionality
- Verify data persistence

## Completion Criteria

Phase 2 is complete when:

- [ ] Knowledge graph schema is defined and initialized
- [ ] Knowledge service is implemented with all core methods
- [ ] Preference management is working
- [ ] Idea storage and retrieval is functional
- [ ] Concept linking and querying works
- [ ] Pomodoro timer service is fully functional
- [ ] Pomodoro API endpoints are working
- [ ] Idea API endpoints are working
- [ ] Local cache service is implemented
- [ ] Service architecture patterns are established
- [ ] All API endpoints are documented
- [ ] All tests pass
- [ ] Performance is acceptable for Pi hardware
- [ ] Documentation is updated

## Questions to Answer

1. **Neo4j Connection**: Verify Tailscale connection to home server is stable
2. **Query Performance**: Test query latency over Tailscale (should be <50ms typically)
2. **Idea Storage**: Should ideas support rich text/markdown or plain text only?
3. **Pomodoro Persistence**: How long should Pomodoro sessions be stored? (for statistics)
4. **Cache Strategy**: What data should be cached and for how long?
5. **Search Implementation**: Full-text search in Neo4j or external search engine?
6. **Tag Management**: Hierarchical tags or flat tag system?
7. **Statistics**: What statistics should be tracked for Pomodoro and ideas?
8. **Performance**: What are acceptable response times for queries on Pi hardware?
9. **Offline Support**: How much offline functionality is needed before sync?

## Next Steps

After completing Phase 2, proceed to:

- **[Phase 3: Personality & Voice](phase-3-personality-voice.md)** - Implement conversational interface and personality system
- Enhance knowledge graph with conversation context
- Begin planning voice interaction patterns

## Troubleshooting

### Common Issues

**Knowledge graph queries are slow:**
- Check Tailscale connection latency
- Optimize Cypher queries
- Add appropriate indexes in Neo4j
- Consider caching frequently accessed data on Pi
- Review graph size and complexity
- Check home server performance

**Pomodoro timer not persisting:**
- Check database connection
- Verify session storage in graph
- Check for timezone issues
- Verify transaction handling

**Idea retrieval not working:**
- Verify Tailscale connection to home server
- Check Neo4j connection and authentication
- Verify Neo4j constraints are created on home server
- Check query syntax (Cypher)
- Verify user relationships in graph
- Test connection: `cypher-shell -a bolt://home-server-ip:7687`

**Cache issues:**
- Verify file permissions
- Check disk space
- Review cache expiration logic
- Check cache directory structure
