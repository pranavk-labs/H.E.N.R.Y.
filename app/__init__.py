"""H.E.N.R.Y. Application package - modular voice assistant with GUI."""

from __future__ import annotations

__all__ = ["HenryApp", "VoiceLoop", "HenryGUI", "UIState"]

_EXPORTS = {
    "HenryApp": ("app.coordinator", "HenryApp"),
    "VoiceLoop": ("app.voice_loop", "VoiceLoop"),
    "HenryGUI": ("app.gui", "HenryGUI"),
    "UIState": ("app.state", "UIState"),
}


def __getattr__(name: str):
    """Load legacy app exports only when callers ask for them."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    module = __import__(module_name, fromlist=[attr_name])
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
