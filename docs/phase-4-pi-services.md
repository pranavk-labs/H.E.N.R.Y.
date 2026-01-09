# Phase 4: Pi Services

## Objectives and Goals

Phase 4 focuses on optimizing and managing services running on the Raspberry Pi for always-on operation. This phase ensures H.E.N.R.Y. runs reliably, efficiently, and can handle continuous operation without manual intervention, **with the native Python GUI (running on the Pi's touchscreen) as the primary face and control surface**.

### Key Objectives

- Implement robust service architecture for always-on operation
- Optimize resource usage for Pi hardware constraints (no LLM/Graph DB on Pi)
- Set up service management and monitoring
- Implement connection management for remote services (Ollama, Neo4j)
- Implement background task processing
- Create real-time conversation handling architecture
- Ensure service reliability and recovery (including remote service connections)

## Core Features

### 1. Service Architecture

**Core Services on Pi:**
- API service (FastAPI backend)
- Voice service (always-on listening and processing)
- Knowledge service client (connects to Neo4j on home server)
- LLM service client (connects to Ollama on home server)
- Integration service (external service connections)
- Robot control service (for Phase 6)
- Background task processor
- Connection manager (Tailscale, Neo4j, Ollama)

**Services on Home Server:**
- Neo4j database
- Ollama LLM service

**Service Communication:**
- Inter-service messaging (on Pi)
- Remote service communication (via Tailscale to home server)
- Event-driven architecture
- Service health monitoring (local and remote)
- Service dependency management
- Connection health checks and retry logic

### 2. Always-On Operation

**Continuous Operation:**
- Service auto-restart on failure
- Graceful shutdown handling
- Resource cleanup on restart
- State persistence
- Recovery from crashes

**Service Management:**
- systemd service configuration
- Service dependencies
- Startup ordering
- Health checks
- Automatic recovery

### 3. Resource Optimization

**CPU Optimization:**
- Process priority management
- CPU affinity settings
- Background task throttling
- Efficient audio processing
- Model optimization (STT/TTS)

**Memory Management:**
- Memory usage monitoring
- Cache size limits
- Buffer management
- Memory leak prevention
- Garbage collection tuning

**Storage Optimization:**
- Log rotation
- Database cleanup
- Cache management
- Temporary file cleanup
- Backup management

### 4. Background Task Processing

**Task Queue:**
- Async task processing
- Priority queue support
- Task retry logic
- Task scheduling
- Background knowledge graph updates

**Background Jobs:**
- Statistics calculation
- Data cleanup
- Cache warming
- Health checks
- Backup operations

### 5. Real-Time Conversation Handling

**Conversation Pipeline:**
- Low-latency audio processing
- Real-time transcription
- Immediate response generation
- Streaming audio output
- Interruption handling

**Concurrency:**
- Multi-threaded audio processing
- Async API handling
- Parallel service operations
- Thread pool management

### 6. Monitoring and Logging

**System Monitoring:**
- CPU and memory usage tracking
- Service health monitoring
- Audio processing metrics
- API performance metrics
- Error rate tracking

**Logging:**
- Structured logging
- Log levels and filtering
- Log rotation
- Error tracking
- Debug logging

## Execution Strategy

### Step 1: Service Architecture Design
1. Define service boundaries and responsibilities (Pi vs home server)
2. Design inter-service communication patterns (on Pi)
3. Design remote service communication (Tailscale to home server)
4. Create service interface definitions
5. Design event system
6. Plan service dependencies (including remote services)
7. Design connection management and fallback strategies

### Step 2: Service Management Setup
1. Create systemd service files for each service
2. Configure service dependencies
3. Set up auto-restart policies
4. Implement health check endpoints
5. Create service management scripts
6. Test service startup and shutdown

### Step 3: Resource Optimization
1. Profile current resource usage on Pi (no LLM/Graph DB on Pi)
2. Optimize CPU-intensive operations (STT, TTS, audio processing)
3. Implement memory management (STT models, caches)
4. Set up storage cleanup routines
5. Configure process priorities
6. Test resource usage under load
7. Monitor remote service connection overhead

### Step 4: Connection Management
1. Design connection manager for remote services
2. Implement Tailscale connection monitoring
3. Implement Neo4j connection health checks
4. Implement Ollama connection health checks
5. Create automatic reconnection logic
6. Implement graceful degradation (offline mode)
7. Add connection status monitoring
8. Test connection failure scenarios

### Step 5: Background Task System
1. Design task queue architecture
2. Implement task queue service
3. Create background job scheduler
4. Implement task retry logic (including remote service calls)
5. Add task monitoring
6. Test background processing

### Step 6: Real-Time Processing
1. Optimize audio processing pipeline
2. Implement streaming transcription
3. Create low-latency response system
4. Optimize conversation handling
5. Test real-time performance
6. Measure and optimize latency

### Step 7: Monitoring and Logging
1. Set up structured logging
2. Implement health monitoring
3. Create metrics collection
4. Set up log rotation
5. Add error tracking
6. Create monitoring dashboard (optional)

### Step 8: Reliability and Recovery
1. Implement graceful shutdown
2. Add state persistence
3. Create recovery mechanisms
4. Test failure scenarios
5. Implement automatic recovery
6. Document recovery procedures

### Step 8: Testing and Optimization
1. Load testing
2. Stress testing
3. Long-running stability tests
4. Resource usage optimization
5. Performance benchmarking
6. Documentation

## Testing Requirements

### Unit Tests
- Service startup and shutdown
- Task queue operations
- Resource management functions
- Health check logic
- Recovery mechanisms

### Integration Tests
- Service communication
- Background task execution
- Service restart scenarios
- Resource cleanup
- State persistence

### Performance Tests
- CPU usage under load
- Memory usage over time
- Audio processing latency
- API response times
- Concurrent request handling

### Stress Tests
- Extended operation (24+ hours)
- High conversation volume
- Resource exhaustion scenarios
- Service failure recovery
- Network interruption handling

### Manual Testing
- Service startup on boot
- Service restart behavior
- Resource usage monitoring
- Background task execution
- Long-term stability

## Completion Criteria

Phase 4 is complete when:

- [ ] All services are configured as systemd services
- [ ] Services auto-start on boot
- [ ] Services auto-restart on failure
- [ ] Resource usage is optimized for Pi hardware
- [ ] Background task system is working
- [ ] Real-time conversation handling is optimized
- [ ] Monitoring and logging are implemented
- [ ] Services run stably for extended periods
- [ ] Recovery mechanisms work correctly
- [ ] Performance meets requirements
- [ ] All tests pass
- [ ] Documentation is updated

## Questions to Answer

1. **Service Architecture**: Monolithic or microservices? (Monolithic likely better for Pi)
2. **Process Management**: systemd only or containerization? (systemd simpler for Pi)
3. **Resource Limits**: What are acceptable CPU/memory usage limits on Pi? (No LLM/Graph DB on Pi)
4. **Remote Service Reliability**: How to handle home server downtime? (fallback strategies)
5. **Connection Monitoring**: How frequently to check remote service health?
6. **Background Tasks**: How many concurrent background tasks?
7. **Monitoring**: Local monitoring only or remote monitoring?
8. **Logging**: How long to keep logs? What log level in production?
9. **Recovery**: Automatic recovery for all failures or manual intervention for some?
10. **Performance Targets**: What are acceptable latency targets? (audio processing, API responses, remote service calls)
11. **Uptime Requirements**: What is acceptable uptime? (99%? 99.9%?)
12. **Backup Frequency**: How often should backups run? What should be backed up?

## Next Steps

After completing Phase 4, proceed to:

- **[Phase 5: Integrations](phase-5-integrations.md)** - Connect with external services
- **[Phase 6: Robot Features](phase-6-robot-features.md)** - Add physical robot capabilities
- Continue monitoring and optimization
- Plan for scaling if needed

## Troubleshooting

### Common Issues

**High resource usage:**
- Profile services to find bottlenecks (on Pi)
- Optimize heavy operations (STT, TTS, audio processing)
- Reduce background task frequency
- Review STT/TTS model sizes
- Check remote service connection overhead
- Monitor Tailscale connection performance

**Service crashes:**
- Check logs for errors
- Review resource limits
- Test individual services
- Check service dependencies

**Memory leaks:**
- Profile memory usage over time
- Review caching strategies
- Check for unclosed connections
- Review buffer management

**Slow performance:**
- Check CPU throttling (thermal)
- Review process priorities
- Optimize database queries
- Check for blocking operations

