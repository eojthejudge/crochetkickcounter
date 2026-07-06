from types import SimpleNamespace
from unittest.mock import Mock

import crochet_counter
from crochet_counter import PygletDevice, get_axis_value, handle_command, select_input_backend


def test_linux_prefers_evdev_when_available():
    assert select_input_backend("linux", has_evdev=True, has_pyglet=True) == "evdev"


def test_windows_prefers_pyglet_when_available():
    assert select_input_backend("win32", has_evdev=False, has_pyglet=True) == "pyglet"


def test_returns_unsupported_when_no_backend():
    assert select_input_backend("linux", has_evdev=False, has_pyglet=False) == "unsupported"


def test_get_axis_value_supports_named_axes():
    device = SimpleNamespace(x=0.0, y=0.0, rz=-1.0)
    assert get_axis_value(device, "rz") == -1.0


def test_get_axis_value_supports_numeric_axes():
    device = SimpleNamespace(x=0.25, y=0.0, rz=0.0)
    assert get_axis_value(device, 0) == 0.25


def test_pyglet_device_forwards_axis_and_button_state():
    underlying = SimpleNamespace(x=0.5, y=-0.25, rz=1.0, buttons=[False, True])
    wrapper = PygletDevice(underlying, 0)
    assert wrapper.x == 0.5
    assert wrapper.y == -0.25
    assert wrapper.rz == 1.0
    assert wrapper.buttons == [False, True]


def test_pyglet_device_reflects_later_underlying_updates():
    underlying = SimpleNamespace(x=0.0, y=0.0, rz=0.0, buttons=[])
    wrapper = PygletDevice(underlying, 0)
    underlying.x = 0.75
    underlying.rz = -0.5
    underlying.buttons = [True]
    assert wrapper.x == 0.75
    assert wrapper.rz == -0.5
    assert wrapper.buttons == [True]


def test_handle_command_supports_reset_and_set():
    count, should_exit = handle_command("reset", 3)
    assert count == 0
    assert should_exit is False

    count, should_exit = handle_command("set 5", 3)
    assert count == 5
    assert should_exit is False


def test_handle_command_supports_quit_and_increment():
    count, should_exit = handle_command("+", 3)
    assert count == 4
    assert should_exit is False

    count, should_exit = handle_command("quit", 3)
    assert count == 3
    assert should_exit is True


def test_pump_pyglet_events_uses_short_timeout():
    if crochet_counter.pyglet is None:
        return

    step = Mock()
    original_step = crochet_counter.pyglet.app.platform_event_loop.step
    crochet_counter.pyglet.app.platform_event_loop.step = step
    try:
        crochet_counter.pump_pyglet_events()
    finally:
        crochet_counter.pyglet.app.platform_event_loop.step = original_step

    step.assert_called_once_with(0.001)
