"""Tests for GTK app-level actions and shortcuts."""

from __future__ import annotations

import app.gtk_app as gtk_app


class FakeAction:
    """Small Gio.SimpleAction stand-in."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.callback = None

    def connect(self, _signal: str, callback) -> None:
        self.callback = callback

    def activate(self) -> None:
        assert self.callback is not None
        self.callback(self, None)


class FakeGio:
    """Small Gio namespace stand-in."""

    class SimpleAction:
        @staticmethod
        def new(name: str, _parameter_type) -> FakeAction:
            return FakeAction(name)


class FakeApp:
    """Small Adw.Application stand-in."""

    def __init__(self) -> None:
        self.actions: dict[str, FakeAction] = {}
        self.accels: dict[str, list[str]] = {}

    def add_action(self, action: FakeAction) -> None:
        self.actions[action.name] = action

    def set_accels_for_action(self, action_name: str, accelerators: list[str]) -> None:
        self.accels[action_name] = accelerators


class FakeWindow:
    """Captures invoked GTK window commands."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def go_back(self) -> None:
        self.calls.append("back")

    def start_runtime(self) -> None:
        self.calls.append("start")

    def stop_runtime(self) -> None:
        self.calls.append("stop")

    def preload_model(self) -> None:
        self.calls.append("preload")

    def unload_model(self) -> None:
        self.calls.append("unload")


def test_install_app_actions_registers_shortcuts_and_callbacks():
    """GTK app actions expose keyboard shortcuts and invoke window commands."""
    app = FakeApp()
    window = FakeWindow()

    gtk_app.install_app_actions(app, window, FakeGio)

    assert app.accels["app.back"] == ["Escape", "<Alt>Left"]
    assert app.accels["app.start"] == ["<Primary>Return"]
    app.actions["back"].activate()
    app.actions["start"].activate()

    assert window.calls == ["back", "start"]
