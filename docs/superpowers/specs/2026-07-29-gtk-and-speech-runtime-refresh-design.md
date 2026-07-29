# HENRY GTK And Speech Runtime Refresh Design

## Goal

Refresh HENRY in two places:

- Replace the current Tkinter canvas UI with a better-looking GTK4/libadwaita desktop app.
- Replace the current voice pipeline default with a real local voice-agent runtime while preserving HENRY's existing tool calls.

This should run from the home server when GPU is useful, support CPU fallback, and expose controls to start, stop, preload, and unload models so HENRY does not pin VRAM unnecessarily.

## Current State

The UI is implemented with Tkinter in `app/gui.py` and canvas widgets in `app/ui/*`. It polls the FastAPI backend for UI state and receives voice status from `VoiceLoop`.

The voice flow is:

`wake word -> VAD recording -> STT -> ConversationService -> Ollama tool calling -> TTS`

Tool execution is already centralized through:

- `ConversationService`
- `OllamaClient.chat_with_tools`
- `ToolsService`
- `tools/*`

That boundary should stay intact.

## Research Summary

GTK path:

- Use PyGObject with GTK4 as the native Python GTK binding.
- Use libadwaita for a modern GNOME-style application shell, adaptive layouts, header bars, status rows, and controls.
- Avoid Toga for this refresh because its GTK4 backend is still marked experimental and adds an abstraction layer HENRY does not need.
- Avoid Dear PyGui because it is better for high-performance tools/dashboards than native Linux companion UI.

Speech path:

- Do not switch directly to a pure end-to-end s2s model for the first implementation.
- Use `huggingface/speech-to-speech` as the voice-agent runtime because it exposes an OpenAI Realtime-compatible server, supports local STT/LLM/TTS components, and keeps streamed text/tool-call orchestration available.
- Keep Ollama as the default LLM/tool brain where practical because HENRY already has working Ollama tool schemas.
- Treat Moshi and MiniCPM-o as future experiments. They are real speech-native/omni models, but current tool-call support and Ollama audio support are not strong enough for HENRY's productivity tool use.

## Architecture

### GTK App

Add a new GTK entrypoint and app package:

- `app/gtk_app.py`
- `app/gtk_ui/`

The GTK app will:

- Poll the existing FastAPI UI/state APIs first.
- Display HENRY's primary face/status/transcript view.
- Provide tabs or navigation for timer, todos, ideas, calendar, and runtime controls.
- Show voice/runtime state: stopped, starting, ready, listening, processing, speaking, error.
- Provide runtime buttons: start voice runtime, stop voice runtime, preload LLM, unload LLM.

The old Tkinter app stays available during migration.

### Voice Runtime Service

Add a backend service that controls model/runtime lifecycle:

- `backend/services/voice_runtime_service.py`
- `backend/api/routes/voice_runtime.py`

Responsibilities:

- Report runtime status.
- Start/stop the speech runtime process when configured.
- Preload/unload Ollama models using `keep_alive`.
- Support GPU and CPU mode through config.
- Avoid starting duplicate runtime processes.
- Return clear errors when dependencies or ports are unavailable.

The service should not execute tools directly. It coordinates lifecycle only.

### Speech Integration

Add a new voice mode:

- `VOICE_RUNTIME=legacy`
- `VOICE_RUNTIME=hf_s2s`

`legacy` keeps the existing wake/VAD/STT/Ollama/TTS flow.

`hf_s2s` connects the client side to the server speech runtime. The speech runtime should use an OpenAI-compatible LLM endpoint where possible. For first implementation, the HENRY backend remains the authoritative tool executor. If the runtime cannot safely stream tool calls into HENRY, we keep tool calls in the existing `ConversationService` path and use the runtime for lower-latency speech I/O around text/tool orchestration.

## Configuration

Add settings:

- `VOICE_RUNTIME`, default `legacy`
- `VOICE_RUNTIME_URL`, default `ws://127.0.0.1:8765/v1/realtime`
- `VOICE_RUNTIME_COMMAND`, default empty
- `VOICE_RUNTIME_DEVICE`, default `cuda`
- `VOICE_RUNTIME_AUTO_START`, default `false`
- `VOICE_RUNTIME_LLM_MODEL`, default from `OLLAMA_MODEL`
- `OLLAMA_KEEP_ALIVE`, default `5m`
- `OLLAMA_UNLOAD_ON_STOP`, default `true`

GPU safety defaults:

- Do not autostart the heavy runtime unless explicitly configured.
- Keep Ollama model keep-alive finite by default.
- Unload the configured Ollama model when stopping runtime if `OLLAMA_UNLOAD_ON_STOP=true`.
- Support CPU mode via runtime command/config, accepting worse latency.

## Tool Calls

Tool calls must stay configured from one source of truth:

- Move repeated hard-coded Ollama tool schema construction toward schemas derived from registered tools, or keep the existing schemas but expose them through a single helper.
- Preserve execution through `ToolsService`.
- Add tests that verify timer/todo/idea tool calls still execute through `ConversationService`.

No speech model should directly mutate HENRY state outside HENRY's tool system.

## UI Design

The first screen should be the usable assistant, not a landing page.

Layout:

- Left: compact navigation rail with icon-first sections.
- Center: large HENRY face/status/transcript area.
- Right: contextual panel for the active tool view.
- Bottom/status area: connection, voice runtime, model, and quick controls.

Visual direction:

- Dark neutral base, not a one-hue palette.
- High contrast text.
- Subtle accent colors for runtime state and productivity tools.
- No decorative gradients/orbs.
- Stable responsive sizing for display and small touchscreen use.

## Error Handling

Runtime API should return structured failures:

- Dependency missing.
- Runtime already running.
- Runtime not running.
- Port unavailable.
- Ollama unavailable.
- Model preload/unload failed.

The GTK app should show status and keep the rest of the UI usable.

## Testing

Add focused tests for:

- Settings defaults.
- Runtime service start/stop idempotency with mocked subprocess.
- Ollama preload/unload payloads.
- Voice runtime API routes.
- Existing tool-call path still working.

Manual verification:

- Start backend.
- Start GTK app.
- Start/stop runtime from UI.
- Preload/unload Ollama model and confirm API returns success.
- Run one voice/tool command in legacy mode before enabling `hf_s2s`.

## Implementation Order

1. Add runtime settings and service/API with tests.
2. Add GTK app shell with runtime controls and basic state polling.
3. Wire GTK launcher while preserving Tkinter launcher.
4. Add `hf_s2s` config/docs and a minimal adapter.
5. Verify legacy tool calls, runtime controls, and UI startup.

## Open Decisions

- Exact first speech runtime command depends on the server environment and installed CUDA version.
- Exact GTK visual polish should be refined after the functional shell is running.
- Full streamed tool-call support through the speech runtime can follow after lifecycle controls and GTK app are stable.
