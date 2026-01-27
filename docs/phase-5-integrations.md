# Phase 5: Integrations

## Objectives and Goals

Phase 5 connects H.E.N.R.Y. with external services and automation systems, enabling it to interact with your digital ecosystem and automate workflows. This phase extends H.E.N.R.Y.'s capabilities beyond the local system.

### Key Objectives

- Integrate with Beeper/Matrix for messaging
- Connect with n8n for workflow automation
- Integrate with home management systems
- Implement webhook and API integration patterns
- Create event-driven architecture for automations
- Enable local network service discovery

## Core Features

### 1. Beeper/Matrix Integration

**Messaging Capabilities:**
- Send and receive messages via Matrix protocol
- Voice-to-message conversion
- Message-to-voice reading
- Notification handling
- Conversation context from messages

**Integration Points:**
- Matrix client setup and authentication
- Message event handling
- Voice command to send messages
- Message notifications via voice
- Message history access

### 2. n8n Workflow Automation

**Workflow Integration:**
- Trigger n8n workflows from H.E.N.R.Y.
- Receive webhooks from n8n
- Execute automation based on voice commands
- Status reporting from workflows
- Workflow result handling

**Integration Patterns:**
- Webhook endpoints for n8n
- API calls to n8n
- Event forwarding to n8n
- Workflow status queries
- Error handling and retries

### 3. Home Management System Integration

**Smart Home Control:**
- Voice control of smart devices
- Status queries for home systems
- Automation triggers
- Scene activation
- Device discovery and management

**Supported Systems:**
- Home Assistant (primary target)
- OpenHAB
- MQTT-based systems
- HTTP API-based systems
- Custom integrations

### 4. Webhook and API Integration

**Webhook Support:**
- Incoming webhook endpoints
- Webhook authentication
- Event processing
- Response handling
- Error handling

**External API Integration:**
- REST API clients
- Authentication handling
- Rate limiting
- Error handling and retries
- Response caching

### 5. Event-Driven Architecture

**Event System:**
- Internal event bus
- Event publishing
- Event subscription
- Event filtering
- Event routing

**Event Types:**
- Voice commands
- Timer events
- External service events
- System events
- User activity events

### 6. Calendar Synchronization

**External Calendar Integration:**
- Google Calendar two-way sync
- Apple Calendar (iCloud) two-way sync
- Import external events to H.E.N.R.Y.
- Export H.E.N.R.Y. events to external calendars
- Automatic sync scheduling (real-time or periodic)
- Conflict resolution for overlapping changes

**Google Calendar Integration:**
- OAuth 2.0 authentication flow
- Incremental sync using sync tokens
- Support for multiple Google calendars
- Event creation, updates, and deletion sync
- Recurring event synchronization
- Google Meet link handling

**Apple Calendar (iCloud) Integration:**
- CalDAV protocol implementation
- App-specific password authentication
- iCalendar format parsing and generation
- Support for multiple iCloud calendars
- RRULE recurring event handling
- ETag-based incremental sync

**Sync Features:**
- Selective sync (choose which calendars to sync)
- Date range filtering (only sync recent/upcoming events)
- Event type filtering (meetings, tasks, etc.)
- Sync status tracking and error reporting
- Manual sync trigger via voice command
- Automatic conflict resolution (last-write-wins or user prompt)

**Implementation Details:**
- Store OAuth tokens encrypted in knowledge graph
- Sync metadata tracking (last_sync_time, sync_token)
- Background sync task scheduler
- Rate limiting to respect API quotas
- Comprehensive error handling and retry logic

### 7. Local Network Service Discovery

**Service Discovery:**
- mDNS/Bonjour support
- Local service advertisement
- Service discovery queries
- Automatic connection
- Service registration

**Network Integration:**
- Local network API access
- Service endpoint discovery
- Automatic IP detection
- Network health monitoring

## Execution Strategy

### Step 1: Integration Architecture Design
1. Design integration service architecture
2. Define integration interface patterns
3. Plan event system design
4. Design error handling strategies
5. Create integration configuration system

### Step 2: Beeper/Matrix Integration
1. Set up Matrix client library
2. Implement authentication
3. Create message sending functionality
4. Implement message receiving and handling
5. Add voice commands for messaging
6. Integrate with conversation system
7. Test message flow

### Step 3: n8n Integration
1. Set up n8n webhook endpoints
2. Create n8n API client
3. Implement workflow triggering
4. Add webhook receiving
5. Create workflow status queries
6. Integrate with voice commands
7. Test workflow execution

### Step 4: Home Management Integration
1. Choose primary home automation system
2. Implement API client for chosen system
3. Create device discovery
4. Implement device control
5. Add status queries
6. Create voice commands for home control
7. Test device interactions

### Step 5: Webhook System
1. Design webhook endpoint structure
2. Implement webhook authentication
3. Create webhook processing pipeline
4. Add webhook response handling
5. Implement webhook management API
6. Test webhook flow

### Step 6: Event System
1. Design event bus architecture
2. Implement event publishing
3. Create event subscription system
4. Add event filtering
5. Implement event routing
6. Integrate with services
7. Test event flow

### Step 7: Calendar Synchronization
1. Implement Google Calendar OAuth 2.0 flow
2. Create Google Calendar API client
3. Implement incremental sync with sync tokens
4. Add Apple Calendar CalDAV client
5. Implement iCalendar parsing and generation
6. Create sync scheduling system (APScheduler or Celery)
7. Implement conflict resolution logic
8. Add encrypted token storage
9. Create sync status tracking
10. Add voice commands for sync operations
11. Test two-way sync with both providers
12. Test recurring event synchronization
13. Test conflict resolution scenarios

### Step 8: Service Discovery
1. Implement mDNS/Bonjour support
2. Create service advertisement
3. Add service discovery queries
4. Implement automatic connection
5. Add service health checks
6. Test discovery and connection

### Step 9: Integration Testing
1. Test all integrations end-to-end
2. Test error handling
3. Test network interruption scenarios
4. Test authentication and security
5. Performance testing
6. Documentation

## Testing Requirements

### Unit Tests
- Integration client methods
- Webhook processing
- Event system operations
- Service discovery functions
- Authentication handling
- Calendar sync token handling
- iCalendar parsing and generation
- Conflict resolution logic
- Encrypted token storage/retrieval

### Integration Tests
- Beeper/Matrix message flow
- n8n workflow execution
- Home automation device control
- Webhook receiving and processing
- Event publishing and subscription
- Google Calendar OAuth flow
- Google Calendar two-way sync
- Apple Calendar CalDAV operations
- Calendar incremental sync
- Recurring event synchronization

### End-to-End Tests
- Voice command → Integration → Result
- External event → H.E.N.R.Y. response
- Workflow automation triggers
- Service discovery and connection
- Error recovery scenarios

### Manual Testing
- Send/receive messages via Matrix
- Trigger n8n workflows via voice
- Control home devices via voice
- Receive webhooks from external services
- Test service discovery
- Test network interruption recovery
- Connect Google Calendar account via OAuth
- Sync events between H.E.N.R.Y. and Google Calendar
- Connect Apple Calendar via CalDAV
- Sync events between H.E.N.R.Y. and iCloud
- Create recurring event and verify instances sync
- Test conflict resolution (modify same event in both places)
- Trigger manual sync via voice command

## Completion Criteria

Phase 5 is complete when:

- [ ] Beeper/Matrix integration is working
- [ ] n8n integration is functional
- [ ] Home management system integration works
- [ ] Webhook system is implemented
- [ ] Event-driven architecture is working
- [ ] Google Calendar sync is functional (OAuth + two-way sync)
- [ ] Apple Calendar sync is functional (CalDAV + two-way sync)
- [ ] Calendar sync scheduling is working (automatic periodic sync)
- [ ] Calendar conflict resolution is implemented
- [ ] Service discovery is functional
- [ ] All integrations have error handling
- [ ] Voice commands work for all integrations
- [ ] Authentication and security are implemented
- [ ] OAuth tokens are stored encrypted
- [ ] All tests pass
- [ ] Documentation is updated

## Questions to Answer

1. **Beeper/Matrix**: Which Matrix server to use? (Beeper, self-hosted, public server)
2. **n8n**: Self-hosted n8n or cloud? What workflows are priority?
3. **Home Automation**: Which system is primary? (Home Assistant, OpenHAB, MQTT, etc.)
4. **Webhook Security**: What authentication method? (API keys, tokens, signatures)
5. **Event System**: In-memory or persistent event bus?
6. **Service Discovery**: Required or optional? (for mobile app connection)
7. **Integration Priority**: Which integrations are most important?
8. **Error Handling**: How to handle integration failures? (retry, notify, degrade gracefully)
9. **Rate Limiting**: What rate limits for external APIs?
10. **Privacy**: What data is shared with external services? What stays local?
11. **Calendar Sync**: Which calendar service to prioritize first? (Google or Apple)
12. **Calendar Sync Frequency**: Real-time (webhook-based) or periodic (e.g., every 15 minutes)?
13. **Calendar Conflict Resolution**: Automatic (last-write-wins) or prompt user?
14. **Calendar Scope**: Sync all calendars or just primary calendar?
15. **Calendar Date Range**: How far back and forward to sync? (e.g., 30 days past, 90 days future)
16. **Background Tasks**: Use APScheduler, Celery, or simple cron?
17. **Token Storage**: Store in knowledge graph or separate encrypted file?

## Next Steps

After completing Phase 5, proceed to:

- **[Phase 6: Robot Features](phase-6-robot-features.md)** - Add physical robot capabilities
- **[Phase 7: Companion App](phase-7-companion-app.md)** - Build mobile companion app
- Enhance integrations based on usage
- Add more integration options

## Troubleshooting

### Common Issues

**Integration authentication failures:**
- Check credentials and tokens
- Verify authentication method
- Review token expiration
- Check API permissions

**Network connectivity issues:**
- Verify network configuration
- Check firewall settings
- Test service endpoints
- Review DNS resolution

**Webhook not receiving:**
- Check webhook URL accessibility
- Verify authentication
- Review webhook endpoint configuration
- Check network routing

**Service discovery not working:**
- Verify mDNS/Bonjour is enabled
- Check network configuration
- Review firewall settings
- Test service advertisement

**Calendar sync issues:**
- Check OAuth token validity (Google)
- Verify app-specific password (Apple)
- Review API quota and rate limits
- Test network connectivity to calendar services
- Check sync token validity
- Verify calendar permissions

**Sync conflicts:**
- Check conflict resolution settings
- Review last_sync_time metadata
- Verify event modification timestamps
- Test conflict resolution logic

**Recurring events not syncing:**
- Verify RRULE parsing
- Check recurrence_pattern mapping
- Test instance generation logic
- Verify sync token includes recurring events

## Implementation References

### Calendar Sync
The calendar synchronization feature has been prepared for Phase 5 implementation:

- **Placeholder Module**: `tools/calendar_sync.py` contains detailed implementation notes
- **Required Dependencies**:
  - Google Calendar: `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`
  - Apple Calendar: `caldav`, `icalendar`
  - Background Tasks: `APScheduler` or `Celery`
  - Encryption: `cryptography` for token storage
- **Architecture Notes**: See `tools/calendar_sync.py` for detailed OAuth flows, CalDAV setup, and sync strategies
- **Calendar Tool**: The internal calendar system is already implemented in `tools/calendar_tool.py`
- **Knowledge Graph**: Calendar events are stored as `CalendarEvent` nodes with full CRUD support
- **API Endpoints**: REST API for calendar operations at `/calendar/*`
- **Documentation**: See `docs/calendar_tool_implementation.md` for internal calendar usage

The internal calendar system is fully functional and ready for external sync integration in Phase 5.

