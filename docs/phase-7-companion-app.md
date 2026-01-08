# Phase 7: Companion App

## Objectives and Goals

Phase 7 develops the mobile companion app that allows remote access and control of H.E.N.R.Y. when you're away from your desk. The mobile app serves as a secondary interface, with voice being the primary interaction method when at the desk.

### Key Objectives

- Build Flutter cross-platform mobile app (iOS/Android)
- Create Swift iOS native app option
- Implement real-time synchronization with Pi
- Enable remote control and monitoring
- Add push notifications
- Design mobile-specific UI/UX

## Core Features

### 1. Mobile App Architecture

**App Structure:**
- Authentication and connection to Pi
- Real-time data synchronization
- Offline capability
- Local caching
- Background updates

**Platform Support:**
- Flutter app (iOS and Android)
- Swift iOS app (native option)
- Consistent feature set across platforms
- Platform-specific optimizations

### 2. Connection and Synchronization

**Pi Connection:**
- Local network discovery (mDNS)
- Manual IP/URL configuration
- Tailscale connection option (if mobile device on Tailscale network)
- Connection status monitoring
- Auto-reconnect on network change
- Secure connection (TLS/SSL)

**Data Synchronization:**
- Real-time updates via WebSocket
- REST API for commands
- Conflict resolution
- Sync status indicators
- Background sync

### 3. Core App Features

**Remote Control:**
- Voice command sending (text input)
- Pomodoro timer control
- Idea creation and viewing
- Robot control (if applicable)
- System status viewing

**Monitoring:**
- H.E.N.R.Y. status
- Active conversations
- System health
- Recent activity
- Statistics and insights

**Notifications:**
- Pomodoro timer alerts
- Message notifications (if Matrix integrated)
- System alerts
- Custom notifications
- Notification preferences

### 4. Mobile-Specific Features

**UI/UX:**
- Mobile-optimized interface
- Touch-friendly controls
- Swipe gestures
- Dark/light theme
- Responsive design

**Platform Features:**
- iOS: Widget support, Siri shortcuts
- Android: Widget support, quick actions
- Push notifications
- Background app refresh
- App shortcuts

### 5. Offline Support

**Offline Capabilities:**
- View cached data
- Queue commands for when online
- Offline mode indicator
- Sync when connection restored
- Local data storage

## Execution Strategy

### Step 1: App Architecture Design
1. Choose primary framework (Flutter recommended)
2. Design app structure and navigation
3. Plan state management approach
4. Design API communication layer
5. Plan offline storage strategy

### Step 2: Flutter App Development
1. Set up Flutter project
2. Create project structure
3. Implement authentication
4. Create API client
5. Implement WebSocket connection
6. Build core UI components
7. Implement main features
8. Add offline support
9. Test on iOS and Android

### Step 3: Swift iOS App (Optional)
1. Set up Swift project
2. Create project structure
3. Implement authentication
4. Create API client
5. Implement WebSocket connection
6. Build native UI
7. Implement core features
8. Add iOS-specific features
9. Test on iOS devices

### Step 4: Connection and Discovery
1. Implement local network discovery (mDNS)
2. Create manual connection UI
3. Implement connection management
4. Add connection status indicators
5. Implement auto-reconnect
6. Test connection scenarios

### Step 5: Real-Time Synchronization
1. Implement WebSocket client
2. Create message protocol
3. Implement real-time updates
4. Add sync status indicators
5. Handle connection interruptions
6. Test synchronization

### Step 6: Core Features Implementation
1. Voice command interface (text input)
2. Pomodoro timer UI and control
3. Idea management UI
4. Robot control UI (if applicable)
5. Status and monitoring screens
6. Test all features

### Step 7: Notifications
1. Set up push notification service (if needed)
2. Implement local notifications
3. Create notification handlers
4. Add notification preferences
5. Test notifications
6. Integrate with Pi events

### Step 8: Polish and Testing
1. UI/UX refinement
2. Performance optimization
3. Error handling
4. Accessibility features
5. Comprehensive testing
6. Documentation

## Testing Requirements

### Unit Tests
- API client methods
- State management logic
- Data synchronization
- Offline storage
- Notification handling

### Integration Tests
- Connection to Pi
- Real-time synchronization
- Feature functionality
- Offline mode
- Error handling

### Platform Tests
- iOS device testing
- Android device testing
- Different screen sizes
- Network conditions
- Battery usage

### Manual Testing
- Connect to Pi from mobile
- Send voice commands
- Control Pomodoro timer
- Create and view ideas
- Receive notifications
- Test offline mode
- Test on different networks

## Completion Criteria

Phase 7 is complete when:

- [ ] Flutter app is functional on iOS and Android
- [ ] Swift iOS app is functional (if implemented)
- [ ] Connection to Pi works (discovery and manual)
- [ ] Real-time synchronization is working
- [ ] All core features are implemented
- [ ] Notifications are working
- [ ] Offline support is functional
- [ ] UI/UX is polished
- [ ] Performance is acceptable
- [ ] All tests pass
- [ ] Documentation is updated

## Questions to Answer

1. **Primary Framework**: Flutter only or also Swift? (Flutter recommended for cross-platform)
2. **Connection Method**: mDNS discovery, manual IP, or both?
3. **Security**: TLS/SSL required? Certificate pinning?
4. **Push Notifications**: Local only or cloud push service? (Firebase, APNs)
5. **Offline Support**: How much functionality offline?
6. **UI Design**: Custom design or Material/Cupertino?
7. **Features Priority**: Which features are most important for mobile?
8. **Platform Support**: iOS and Android equally, or prioritize one?
9. **App Store**: Plan to publish or personal use only?
10. **Update Mechanism**: Auto-update, manual, or app store only?

## Next Steps

After completing Phase 7, proceed to:

- **[Phase 8: Deployment](phase-8-deployment.md)** - Production deployment
- App store submission (if publishing)
- User feedback and iteration
- Additional mobile features

## Troubleshooting

### Common Issues

**Connection issues:**
- Check network configuration
- Verify Pi is accessible
- Check firewall settings
- Test mDNS discovery
- Review connection code

**Synchronization problems:**
- Check WebSocket connection
- Verify message protocol
- Review sync logic
- Test network interruptions
- Check error handling

**Performance issues:**
- Optimize API calls
- Review state management
- Check memory usage
- Optimize UI rendering
- Profile app performance

**Platform-specific issues:**
- Review platform-specific code
- Check permissions
- Verify platform APIs
- Test on physical devices
- Review platform guidelines

