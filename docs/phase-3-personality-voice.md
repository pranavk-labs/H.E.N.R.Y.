# Phase 3: Personality & Voice

## Objectives and Goals

Phase 3 implements the conversational interface and personality system that makes H.E.N.R.Y. a true desk companion. This is the core differentiator - H.E.N.R.Y. is designed for continuous voice interaction throughout your work, not just occasional commands.

### Key Objectives

- Implement always-on voice listening and processing
- Create personality system with traits and behaviors
- Build natural language understanding and response generation
- Establish continuous conversation handling and context management
- Implement voice recognition and synthesis
- Create audio/visual feedback mechanisms
- Design context awareness in conversations

## Core Features

### 1. Always-On Voice Listening

**Wake Word Activation:**
- Always-listening microphone for wake word detection
- HENRY only processes audio when wake word is detected (e.g., "Hey HENRY")
- Low-latency wake word detection pipeline
- Background audio monitoring without full processing
- Energy-efficient listening (optimized for Pi)
- Noise filtering and echo cancellation

**Voice Recognition:**
- Speech-to-text conversion (Whisper or alternative)
- Real-time transcription
- Offline processing capability
- Multi-language support (if needed)
- Accent and voice adaptation

### 2. Personality System

**Personality Traits:**
- Configurable personality characteristics (helpful, witty, professional, etc.)
- Response style variations
- Emotional context awareness
- Learning from user preferences
- Adaptive personality based on context

**Personality Expression:**
- Response tone and style
- Conversation patterns
- Proactive suggestions
- Humor and personality quirks
- Context-appropriate behavior

**Personality Storage:**
- Store personality preferences in knowledge graph
- Track personality interactions
- Learn user preferences for personality traits
- Adapt over time

### 3. Natural Language Understanding

**Intent Recognition:**
- Command classification
- Context extraction
- Entity recognition (names, dates, concepts)
- Ambiguity resolution
- Multi-turn conversation understanding

**Context Management:**
- Conversation history tracking
- Context window management
- Reference resolution ("it", "that", "the previous thing")
- Temporal context awareness
- User state tracking

### 4. Response Generation with LLM

**LLM Integration (Ollama on Home Server):**
- Ollama client setup (connects to home server via Tailscale)
- Model selection (can use larger models on home server: Llama 3.1 8B, Mistral 7B, or larger)
- LLM client integration with remote Ollama
- Connection management and health checks
- Prompt engineering for personality
- Context window management
- Response streaming (if supported by Ollama)
- Local fallback strategy (if home server unavailable)

**Natural Responses:**
- Context-aware response generation via LLM
- Personality-infused prompts and responses
- Multi-modal responses (text + voice)
- Proactive suggestions
- Clarification requests

**Response Types:**
- Direct answers to questions
- Task execution confirmations
- Conversational responses
- Error handling and clarification
- Proactive notifications

**Optional Cloud Fallback:**
- Langchain integration for cloud APIs (optional)
- Fallback to cloud LLM for complex tasks
- Hybrid approach (local primary, cloud fallback)

### 5. Text-to-Speech

**Voice Synthesis:**
- Natural-sounding voice synthesis
- Personality-appropriate voice characteristics
- Adjustable speed and pitch
- Multiple voice options (if desired)
- Offline TTS capability

**Audio Output:**
- Queue management for responses
- Interruption handling
- Audio feedback for actions
- Background music/sounds (optional)

### 6. Conversation Context

**Context Tracking:**
- Current conversation state
- Recent topics and entities
- User activity context
- Time-based context
- Location context (if available)

**Context Integration:**
- Link conversations to knowledge graph
- Store important conversation points
- Extract preferences from conversations
- Build relationships from dialogue

### 7. Visual and Audio Feedback

**Visual Feedback (Native Python GUI + Touchscreen):**
- Full-screen Python GUI (e.g., PySide6 or Kivy) running on the Pi, on a touchscreen display
- Renders H.E.N.R.Y.'s face and tool views based on `ScreenManager.state`
- Indicators for listening/speaking states
- Visualizations for ideas, tasks, and tools
- Conversation history display as needed
- Personality expression through animations and expressions
- Touch interactions mapped to tool actions (e.g., tapping timer controls, selecting ideas), routed through tools/`ToolsService`

**Audio Feedback:**
- Earcons (short sounds) for key events
- Confirmation sounds for actions
- Error tones
- Background ambience (optional)
- Volume and feedback settings

## Execution Strategy

### Step 1: Voice Input Infrastructure
1. Set up always-on audio capture for wake word detection
2. Implement wake word detection (HENRY only processes when name is called)
3. Implement audio buffering and streaming (activated after wake word)
4. Add noise reduction and filtering
5. Optimize for Pi hardware (CPU usage, memory)
6. Test wake word detection accuracy and latency
7. Test audio quality and processing latency

### Step 2: Speech-to-Text Integration
1. Choose and integrate STT engine (Whisper recommended)
2. Implement real-time transcription
3. Add offline processing support
4. Optimize model size for Pi (quantized models)
5. Implement streaming transcription
6. Add error handling and fallbacks

### Step 2.5: LLM Setup (Ollama on Home Server)
1. Verify Ollama is installed and running on home server
2. Check available models on home server (via Tailscale)
3. Select appropriate model (can use larger models: 7B-13B or even 70B if server has RAM)
4. Create Ollama client service (connects via Tailscale)
5. Test connection to Ollama on home server
6. Implement connection health checks and retry logic
7. Create prompt templates
8. Test response generation over Tailscale
9. Measure latency and optimize if needed
10. Implement local fallback (simple responses or queue for later)

### Step 3: Personality System Design
1. Define personality trait system
2. Create personality configuration
3. Design response style templates
4. Implement personality selection logic
5. Create personality storage in knowledge graph
6. Build personality adaptation mechanisms

### Step 4: Natural Language Understanding
1. Implement intent classification
2. Create entity extraction system
3. Build context extraction pipeline
4. Implement reference resolution
5. Add ambiguity handling
6. Create conversation state management

### Step 5: Response Generation with LLM
1. Integrate Ollama client (remote) with response system
2. Design prompt templates with personality
3. Implement context-aware prompt construction
4. Add personality injection into prompts
5. Create response generation pipeline (Remote LLM → personality → formatting)
6. Implement streaming responses (if supported by Ollama)
7. Add response caching for common queries (on Pi)
8. Implement connection error handling and fallback
9. Create proactive suggestion system
10. Implement error response handling
11. Build response queue management (for offline scenarios)
12. Optional: Add cloud LLM fallback integration

### Step 6: Text-to-Speech Integration
1. Choose and integrate TTS engine (pyttsx3, Coqui TTS, or cloud)
2. Configure voice characteristics
3. Implement response queue
4. Add interruption handling
5. Optimize for natural conversation flow
6. Test audio quality

### Step 7: Conversation Management
1. Implement conversation state tracking
2. Create context window management
3. Build conversation history storage
4. Link conversations to knowledge graph
5. Implement context-aware responses
6. Add conversation analytics

### Step 8: Integration and Testing
1. Integrate voice pipeline with API
2. Connect to knowledge graph services
3. Integrate with productivity tools
4. End-to-end conversation testing
5. Performance optimization
6. Latency testing and optimization

## Testing Requirements

### Unit Tests
- Audio capture and processing
- STT accuracy and latency
- Intent classification accuracy
- Entity extraction
- Response generation logic
- TTS output quality

### Integration Tests
- End-to-end voice conversation flow
- Context management across turns
- Knowledge graph integration
- Personality consistency
- Error handling and recovery

### Performance Tests
- Voice processing latency
- CPU and memory usage
- Concurrent conversation handling
- Audio buffer management
- Response time measurements

### Manual Testing
- Natural conversation flow
- Personality expression
- Context understanding
- Multi-turn conversations
- Error recovery
- Background noise handling

## Completion Criteria

Phase 3 is complete when:

- [x] Wake word detection is working (HENRY only activates when name is called) *(implemented in `AudioService` with OpenWakeWord and custom model support)*
- [x] Always-on voice listening for wake word is working *(implemented in `AudioService.start_listening` using PyAudio streaming)*
- [ ] Speech-to-text is functional with acceptable accuracy *(service interface to be wired to concrete engine such as Whisper in a later iteration)*
- [x] Personality system is implemented and configurable *(see `PersonalityService`, backed by `KnowledgeService` preferences)*
- [x] Natural language understanding works for core intents *(minimal rules-based NLU in `ConversationService` for Pomodoro and idea capture)*
- [x] Response generation includes personality *(personality-aware system prompt + response decoration via `PersonalityService`)*
- [ ] Text-to-speech is working with natural voice *(stubbed for now; concrete TTS engine to be selected)*
- [x] Conversation context is tracked and used *(per-user conversation history in `ConversationService` with bounded context window)*
- [x] Multi-turn conversations work correctly *(tested via `tests/test_conversation_service.py` and `tests/test_conversation_api.py`)*
- [x] Knowledge graph integration is functional *(personality preferences persisted via `KnowledgeService.set_preference`)*
- [ ] Performance is acceptable on Pi hardware *(measure and tune once deployed on target Pi)*
- [x] Error handling and recovery works *(Ollama client health + retry logic, conversation fallbacks)*
- [x] All tests pass *(Phase 3 tests run via `scripts/test_phase3.sh`)*
- [x] Documentation is updated *(this document + README run instructions updated)*

## Running the Phase 3 Stack (Backend + GUI)

### Local development

1. **Start the backend API** (with conversation + productivity routes):

   ```bash
   cd /home/pi/H.E.N.R.Y.  # or your project root
   poetry run python scripts/dev_server.py
   # Backend will listen on http://127.0.0.1:8000 by default
   ```

2. **In a second terminal, start the Phase 3 GUI** (tkinter-based, polling `ScreenManager.state` via the API):

   ```bash
   cd /home/pi/H.E.N.R.Y.
   API_BASE_URL="http://127.0.0.1:8000" poetry run python scripts/henry_gui.py
   ```

   - The GUI will:
     - Show the current `active_view` (e.g., `pomodoro`, `ideas`, `idle`)
     - Display `status_text` (e.g., "Pomodoro started", "Idea captured")
     - Render a JSON view of `timer_state` and `idea_view`

3. **Drive tools and conversation through the API**:

   - Call the **conversation endpoint**:

     ```bash
     curl -X POST "http://127.0.0.1:8000/conversation/chat" \
       -H "Content-Type: application/json" \
       -d '{"text": "Start a pomodoro timer", "user_id": "dev"}'
     ```

   - The GUI should update to the `pomodoro` view and show timer state.

4. **Run Phase 3 tests**:

   ```bash
   cd /home/pi/H.E.N.R.Y.
   bash scripts/test_phase3.sh
   ```

   This runs:

   - `tests/test_personality_service.py`
   - `tests/test_conversation_service.py`
   - `tests/test_conversation_api.py`

### Optional: Full dev stack with one command

For rapid local development, you can start **backend + GUI + voice loop** together:

```bash
cd /home/pi/H.E.N.R.Y.
bash scripts/dev_run_all.sh
```

This will:

- Run the FastAPI dev server (`scripts/dev_server.py`)
- Launch the Phase 3 GUI (`scripts/henry_gui.py`)
- Start the voice loop (`scripts/voice_loop.py`), which:
  - Listens for the wake word via `AudioService`
  - When triggered, prompts you in the terminal to type what you said (STT stub)
  - Sends that text into `ConversationService`
  - Speaks/logs the response via `TextToSpeechService`

## Questions to Answer

1. **Wake Word**: What wake word/phrase should trigger HENRY? (e.g., "Hey HENRY", "HENRY", etc.) - **Required**: HENRY only processes audio when wake word is detected
2. **STT Engine**: Whisper (offline, accurate) vs cloud services (better accuracy, requires internet)?
3. **Model Size**: Full Whisper model or quantized/smaller version? (trade-off between accuracy and performance)
4. **LLM Choice**: Ollama on home server (recommended) or Langchain + Cloud?
5. **Ollama Model on Home Server**: Which model? (Can use larger models: 7B-13B or even 70B depending on server RAM)
6. **Connection Latency**: What is acceptable latency for LLM responses? (Tailscale typically <50ms, but LLM inference adds time)
7. **Cloud Fallback**: Should we implement optional cloud LLM fallback? (adds complexity but provides backup)
7. **TTS Engine**: Offline (pyttsx3, Coqui) or cloud (better quality, requires internet)?
8. **Personality Default**: What should the default personality be? (helpful assistant, witty companion, professional, etc.)
9. **Context Window**: How many conversation turns should be kept in context? (affects memory usage, especially with LLM)
10. **LLM Memory**: How much RAM can we allocate to Ollama? (affects model choice and quantization)
11. **Proactive Behavior**: How proactive should H.E.N.R.Y. be? (suggestions, reminders, etc.)
12. **Multi-language**: Support for multiple languages or English only initially?
13. **Voice Characteristics**: Male/female voice, speed, pitch preferences?
14. **Privacy**: Should conversations be stored? How long? What level of detail?

## Next Steps

After completing Phase 3, proceed to:

- **[Phase 4: Pi Services](phase-4-pi-services.md)** - Optimize services for always-on operation
- **[Phase 5: Integrations](phase-5-integrations.md)** - Connect with external services
- Refine personality based on usage patterns
- Enhance conversation capabilities

## Troubleshooting

### Common Issues

**High CPU usage:**
- Optimize STT model size
- Reduce audio processing frequency
- Use hardware acceleration if available
- Optimize audio buffer sizes
- Optimize LLM inference (smaller model, better quantization)
- Reduce LLM context window size

**High memory usage:**
- LLM runs on home server, not Pi (no Pi memory concern)
- Monitor Pi memory for other services (STT, TTS, API)
- Reduce context window for LLM if needed (affects quality)
- Check home server memory usage if LLM is slow

**LLM connection issues:**
- Verify Tailscale connection to home server
- Check Ollama is running on home server
- Test connection: `curl http://home-server-ip:11434/api/tags`
- Verify firewall settings on home server
- Check Ollama port (default 11434)
- Implement retry logic and fallback

**Audio latency:**
- Check audio buffer configuration
- Optimize processing pipeline
- Consider dedicated audio processing thread
- Review system resource usage

**STT accuracy issues:**
- Improve microphone quality/positioning
- Add noise reduction
- Fine-tune STT model
- Consider user-specific adaptation

**Personality inconsistency:**
- Review personality selection logic
- Check context management
- Verify personality storage
- Test across different scenarios

