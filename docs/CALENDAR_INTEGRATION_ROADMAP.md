# Calendar Integration Roadmap

This document tracks the implementation status and roadmap for H.E.N.R.Y.'s calendar functionality.

## Phase 3 (Current) - Internal Calendar System ✅ COMPLETE

The internal calendar system has been fully implemented and is ready for use.

### Implemented Features
- ✅ Event CRUD operations (create, read, update, delete)
- ✅ Recurring events (daily, weekly, monthly, yearly)
- ✅ Event types (event, meeting, task, reminder)
- ✅ Event reminders (minutes before event)
- ✅ Attendee tracking
- ✅ Event search and filtering
- ✅ Smart queries (upcoming events, today's events)
- ✅ Event status tracking (scheduled, cancelled, completed)
- ✅ Recurring event instance generation
- ✅ Knowledge graph storage (Neo4j/fallback)
- ✅ REST API endpoints
- ✅ Voice intent detection
- ✅ Screen manager UI state tracking
- ✅ Comprehensive test suite

### Files Implemented
```
tools/
├── calendar_tool.py          # Main calendar tool (447 lines)
└── calendar_sync.py          # Phase 5 placeholder with implementation notes

backend/services/
├── knowledge_service.py      # Extended with recurring event generation
├── conversation_service.py   # Calendar intent detection
└── screen_manager.py         # Calendar UI state

backend/api/routes/
└── calendar.py               # REST API (273 lines)

tests/
└── test_calendar_tool.py     # Comprehensive tests (398 lines)

docs/
├── calendar_tool_implementation.md  # Full documentation
└── CALENDAR_INTEGRATION_ROADMAP.md  # This file
```

### API Endpoints
```
POST   /calendar/events                      # Create event
GET    /calendar/events                      # List events (with filters)
GET    /calendar/events/upcoming             # Get upcoming events
GET    /calendar/events/today                # Get today's events
GET    /calendar/events/search?q=<query>    # Search events
GET    /calendar/events/{id}                 # Get specific event
PUT    /calendar/events/{id}                 # Update event
DELETE /calendar/events/{id}                 # Delete event
POST   /calendar/events/generate-recurring   # Generate recurring instances
```

### Voice Commands
```
"What's on my calendar today?"
"Show me my upcoming events"
"What meetings do I have?"
```

### Usage Examples

**Python API:**
```python
from tools.calendar_tool import CalendarTool

tool.execute("create", title="Meeting", start_time="2026-01-17T14:00:00Z")
tool.execute("get_today")
tool.execute("get_upcoming", limit=5)
```

**REST API:**
```bash
curl http://localhost:8000/calendar/events/today
curl http://localhost:8000/calendar/events/upcoming?limit=5
```

## Phase 5 - External Calendar Sync 📋 PLANNED

External calendar synchronization will connect H.E.N.R.Y. with Google Calendar and Apple Calendar (iCloud).

### Planned Features
- ⏳ Google Calendar OAuth 2.0 integration
- ⏳ Apple Calendar (iCloud) CalDAV integration
- ⏳ Two-way synchronization
- ⏳ Incremental sync (sync tokens / ETags)
- ⏳ Automatic periodic sync scheduling
- ⏳ Conflict resolution (last-write-wins or user prompt)
- ⏳ Selective sync (choose calendars, date ranges, event types)
- ⏳ Encrypted OAuth token storage
- ⏳ Sync status tracking and error reporting
- ⏳ Voice commands for manual sync triggers

### Implementation Steps

#### 1. Google Calendar Integration
1. Set up Google Cloud Console project
2. Configure OAuth 2.0 credentials
3. Install dependencies:
   ```bash
   poetry add google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```
4. Implement OAuth flow in `tools/calendar_sync.py`
5. Create Google Calendar API client
6. Implement sync logic with sync tokens
7. Handle recurring events (RRULE)
8. Test two-way sync

#### 2. Apple Calendar Integration
1. Set up Apple ID app-specific password
2. Install dependencies:
   ```bash
   poetry add caldav icalendar
   ```
3. Implement CalDAV client in `tools/calendar_sync.py`
4. Create iCalendar parser/generator
5. Implement sync logic with ETags
6. Handle recurring events (RRULE to recurrence_pattern mapping)
7. Test two-way sync

#### 3. Sync Scheduling
1. Choose background task library (APScheduler recommended)
   ```bash
   poetry add apscheduler
   ```
2. Implement sync scheduler
3. Add periodic sync jobs (e.g., every 15 minutes)
4. Add webhook endpoints for real-time sync (optional)
5. Implement retry logic for failed syncs

#### 4. Conflict Resolution
1. Implement last-write-wins strategy (default)
2. Add user prompt option (via voice or GUI)
3. Track modification timestamps
4. Store sync metadata in knowledge graph
5. Test conflict scenarios

#### 5. Security & Token Storage
1. Install encryption library:
   ```bash
   poetry add cryptography
   ```
2. Implement encrypted token storage
3. Store OAuth refresh tokens securely
4. Implement token refresh logic
5. Add token revocation support

#### 6. Voice Commands
Add conversation intents:
- "Sync my calendar"
- "Sync my Google calendar"
- "Sync my Apple calendar"
- "What's my calendar sync status?"

### Files to Implement
```
tools/
└── calendar_sync.py          # Implement CalendarSyncManager

backend/services/
└── sync_scheduler.py         # New: Background sync scheduler

backend/api/routes/
└── calendar.py               # Add OAuth flow endpoints, sync status

backend/services/
└── conversation_service.py   # Add sync voice intents

tests/
└── test_calendar_sync.py     # New: Sync tests
```

### Dependencies to Add
```toml
[tool.poetry.dependencies]
# Google Calendar
google-api-python-client = "^2.0.0"
google-auth-httplib2 = "^0.1.0"
google-auth-oauthlib = "^1.0.0"

# Apple Calendar
caldav = "^1.0.0"
icalendar = "^5.0.0"

# Background Tasks
apscheduler = "^3.10.0"  # or celery for more advanced use

# Encryption
cryptography = "^41.0.0"
```

### Configuration
Add to `.env.local`:
```bash
# Google Calendar
GOOGLE_CALENDAR_ENABLED=true
GOOGLE_OAUTH_CLIENT_ID=<your_client_id>
GOOGLE_OAUTH_CLIENT_SECRET=<your_client_secret>
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/calendar/oauth/callback

# Apple Calendar
APPLE_CALENDAR_ENABLED=true
APPLE_CALDAV_URL=https://caldav.icloud.com/
APPLE_USERNAME=<your_apple_id>
APPLE_APP_PASSWORD=<app_specific_password>

# Sync Settings
CALENDAR_SYNC_INTERVAL_MINUTES=15
CALENDAR_SYNC_DATE_RANGE_DAYS=90
CALENDAR_CONFLICT_RESOLUTION=last_write_wins  # or prompt_user
```

### Testing Strategy
1. **Unit Tests**:
   - OAuth token handling
   - iCalendar parsing/generation
   - Conflict resolution logic
   - Sync token management

2. **Integration Tests**:
   - Google Calendar OAuth flow (with mocked responses)
   - CalDAV operations (with test server)
   - Two-way sync (mock external calendars)
   - Recurring event sync

3. **Manual Tests**:
   - Connect real Google Calendar account
   - Connect real Apple Calendar account
   - Create event in H.E.N.R.Y., verify sync to external
   - Create event externally, verify sync to H.E.N.R.Y.
   - Modify same event in both places, test conflict resolution
   - Create recurring event, verify instances sync correctly

### Estimated Effort
- **Google Calendar**: 3-5 days
- **Apple Calendar**: 3-5 days
- **Sync Scheduling**: 1-2 days
- **Conflict Resolution**: 1-2 days
- **Token Storage**: 1 day
- **Testing**: 2-3 days
- **Total**: 11-18 days

### Success Criteria
Phase 5 calendar sync is complete when:
- [ ] Google Calendar OAuth flow works
- [ ] Two-way sync with Google Calendar is functional
- [ ] Apple Calendar CalDAV connection works
- [ ] Two-way sync with Apple Calendar is functional
- [ ] Periodic sync runs automatically
- [ ] Conflict resolution handles overlapping changes
- [ ] OAuth tokens are stored encrypted
- [ ] Recurring events sync correctly
- [ ] Voice commands trigger manual sync
- [ ] All tests pass
- [ ] Documentation is updated

## References

### Documentation
- [Phase 5 Integration Plan](phase-5-integrations.md) - Overall Phase 5 strategy
- [Calendar Tool Implementation](calendar_tool_implementation.md) - Internal calendar usage
- [Calendar Sync Placeholder](../tools/calendar_sync.py) - Detailed implementation notes

### External Resources
- [Google Calendar API v3 Documentation](https://developers.google.com/calendar/api/v3/reference)
- [CalDAV RFC](https://tools.ietf.org/html/rfc4791)
- [iCalendar RFC](https://tools.ietf.org/html/rfc5545)
- [Apple Calendar Server Documentation](https://developer.apple.com/documentation/calendar)

### Related Issues
- Track implementation progress in GitHub issues with label `phase-5-calendar-sync`
- Break down into smaller issues for each integration step

---

**Current Status**: Phase 3 internal calendar complete ✅
**Next Milestone**: Phase 5 external calendar sync 📋
**Last Updated**: 2026-01-16
