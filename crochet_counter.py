#!/usr/bin/env python3
import argparse
import os
import re
import select
import sys
import time

try:
    import numpy as np
except ImportError:
    np = None

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    from evdev import InputDevice, ecodes, list_devices
except ImportError:
    InputDevice = None
    ecodes = None
    list_devices = None

# Keep a simple boolean for backend selection.
evdev = InputDevice is not None and ecodes is not None and list_devices is not None

try:
    import pyglet
except ImportError:
    pyglet = None


class PygletDevice:
    def __init__(self, device, index):
        self.device = device
        self.index = index
        self.path = f"joystick:{index}"
        self.name = getattr(device, "name", f"Joystick {index}")
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.rx = 0.0
        self.ry = 0.0
        self.rz = 0.0
        self.buttons = []
        self._read_state()

    def __getattribute__(self, name):
        if name in {"x", "y", "z", "rx", "ry", "rz", "buttons"}:
            object.__getattribute__(self, "_read_state")()
        return object.__getattribute__(self, name)

    def _read_state(self):
        if hasattr(self.device, "x"):
            self.x = getattr(self.device, "x", 0.0)
        else:
            self.x = 0.0
        if hasattr(self.device, "y"):
            self.y = getattr(self.device, "y", 0.0)
        else:
            self.y = 0.0
        if hasattr(self.device, "z"):
            self.z = getattr(self.device, "z", 0.0)
        else:
            self.z = 0.0
        if hasattr(self.device, "rx"):
            self.rx = getattr(self.device, "rx", 0.0)
        else:
            self.rx = 0.0
        if hasattr(self.device, "ry"):
            self.ry = getattr(self.device, "ry", 0.0)
        else:
            self.ry = 0.0
        if hasattr(self.device, "rz"):
            self.rz = getattr(self.device, "rz", 0.0)
        else:
            self.rz = 0.0
        self.buttons = list(getattr(self.device, "buttons", []))

    def open(self):
        if getattr(self.device, "device", None) is not None:
            self.device.open()

    def close(self):
        try:
            self.device.close()
        except Exception:
            pass


def select_input_backend(platform_name=None, has_evdev=None, has_pyglet=None):
    platform_name = platform_name or sys.platform
    has_evdev = evdev if has_evdev is None else has_evdev
    has_pyglet = (pyglet is not None) if has_pyglet is None else has_pyglet

    if platform_name.startswith("linux") and has_evdev:
        return "evdev"
    if platform_name.startswith("win") and has_pyglet:
        return "pyglet"
    if platform_name.startswith("linux"):
        return "unsupported"
    if platform_name.startswith("win"):
        return "unsupported"
    if has_evdev:
        return "evdev"
    if has_pyglet:
        return "pyglet"
    return "unsupported"


def list_input_devices():
    backend = select_input_backend()
    if backend == "evdev":
        devices = []
        for path in list_devices():
            try:
                dev = InputDevice(path)
            except OSError:
                continue
            devices.append((path, dev.name, dev.phys or ""))
        return devices

    if backend == "pyglet":
        if pyglet is None:
            raise RuntimeError("pyglet is not installed. Install it with 'pip install pyglet'.")
        devices = []
        for index, device in enumerate(pyglet.input.get_joysticks()):
            devices.append((str(index), getattr(device.device, "name", f"Joystick {index}"), ""))
        return devices

    raise RuntimeError("No supported input backend is available on this platform. On Linux install evdev. On Windows install pygame.")


def find_device(device_path=None, name_pattern=None):
    backend = select_input_backend()
    if backend == "evdev":
        if device_path:
            try:
                return InputDevice(device_path)
            except OSError as exc:
                raise RuntimeError(f"Unable to open {device_path}: {exc}")

        if not name_pattern:
            name_pattern = re.compile(r"saitek|rudder|joystick|gamepad|flight", re.I)
        elif isinstance(name_pattern, str):
            name_pattern = re.compile(name_pattern, re.I)

        for path, name, phys in list_input_devices():
            if name_pattern.search(name) or name_pattern.search(phys):
                try:
                    return InputDevice(path)
                except OSError:
                    continue

        raise RuntimeError("No matching input device found. Use --list to discover event paths.")

    if backend == "pyglet":
        if pyglet is None:
            raise RuntimeError("pyglet is not installed. Install it with 'pip install pyglet'.")

        devices = list(pyglet.input.get_joysticks())
        if device_path:
            try:
                index = int(device_path)
            except ValueError:
                index = None
            if index is not None:
                if index < len(devices):
                    return PygletDevice(devices[index], index)
                raise RuntimeError(f"Joystick index {index} was not found.")

        if not name_pattern:
            name_pattern = re.compile(r"saitek|rudder|joystick|gamepad|flight", re.I)
        elif isinstance(name_pattern, str):
            name_pattern = re.compile(name_pattern, re.I)

        for index, device in enumerate(devices):
            if name_pattern.search(getattr(device.device, "name", f"Joystick {index}")):
                return PygletDevice(device, index)

        if not devices:
            raise RuntimeError("No game controllers were found. Connect one and try again.")
        raise RuntimeError("No matching controller was found. Use --list to discover joystick names.")

    raise RuntimeError("No supported input backend is available on this platform. On Linux install evdev. On Windows install pygame.")


def print_devices():
    try:
        devices = list_input_devices()
    except RuntimeError as exc:
        print(f"Error: {exc}")
        return

    if not devices:
        print("No input devices found.")
        return
    print("Input devices:")
    for path, name, phys in devices:
        print(f"  {path}\t{name}\t{phys}")


def parse_event_code(value, backend):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if str(value).isdigit():
        return int(value)
    if backend == "evdev" and ecodes is not None:
        return ecodes.ecodes.get(value)
    return None


def get_axis_value(device, axis_spec):
    if axis_spec is None:
        return None
    if isinstance(axis_spec, int):
        names = ["x", "y", "z", "rx", "ry", "rz"]
        axis_name = names[axis_spec] if 0 <= axis_spec < len(names) else None
        if axis_name is None:
            return None
        return getattr(device, axis_name, 0.0)
    if isinstance(axis_spec, str):
        return getattr(device, axis_spec.lower(), 0.0)
    return None


def play_beep(args):
    if not args.audio:
        return
    try:
        if os.name == "nt":
            import winsound
            winsound.Beep(1000, 120)
        elif sd is not None and np is not None:
            sample_rate = 44100
            duration = 0.15
            freq = 1000.0
            samples = np.sin(2 * np.pi * freq * np.arange(int(sample_rate * duration)) / sample_rate).astype(np.float32)
            sd.play(samples, samplerate=sample_rate, blocking=False)
        else:
            sys.stdout.write("\a")
            sys.stdout.flush()
    except Exception:
        pass


_console_input_buffer = []


def read_pending_command(stdin_obj=None):
    stdin_obj = stdin_obj or sys.stdin
    if not getattr(stdin_obj, "isatty", lambda: False)():
        return None

    try:
        import msvcrt
    except ImportError:
        return None

    if not msvcrt.kbhit():
        return None

    key = msvcrt.getwch()
    if key in {"\r", "\n"}:
        sys.stdout.write("\n")
        sys.stdout.flush()
        line = "".join(_console_input_buffer).strip().lower()
        _console_input_buffer.clear()
        return line
    if key in {"\x03", "\x1b"}:
        raise KeyboardInterrupt
    if key in {"\x08", "\x7f"}:
        if _console_input_buffer:
            _console_input_buffer.pop()
            sys.stdout.write("\b \b")
            sys.stdout.flush()
        return None
    _console_input_buffer.append(key)
    sys.stdout.write(key)
    sys.stdout.flush()
    return None


def handle_command(command, count):
    if command in {"q", "quit", "exit"}:
        return count, True
    if command in {"+", "inc", "i"}:
        return count + 1, False
    if command in {"-", "dec", "d"}:
        return max(0, count - 1), False
    if command.startswith("set "):
        try:
            return int(command.split(None, 1)[1]), False
        except ValueError:
            return count, False
    if command == "reset":
        return 0, False
    if command in {"p", "status"}:
        return count, False
    return count, False


def pump_pyglet_events():
    if pyglet is None:
        return
    try:
        pyglet.app.platform_event_loop.step(0.001)
    except Exception:
        pass


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    if os.name == "nt":
        try:
            import msvcrt
            msvcrt.setmode(sys.stdin.fileno(), os.O_TEXT)
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Crochet counter driven by a USB pedal or game controller.")
    parser.add_argument("--list", action="store_true", help="List input devices and exit.")
    parser.add_argument("--device", help="Event device path on Linux or joystick index on Windows.")
    parser.add_argument("--name", default="saitek|rudder", help="Regex used to find the pedal device when --device is not provided.")
    parser.add_argument("--button", default=None, help="Button event code to use for incrementing the counter.")
    parser.add_argument("--axis", default="y", help="Absolute axis event code (Linux) or axis index (Windows) for incrementing the counter.")
    parser.add_argument("--axis-threshold", type=int, default=10, help="Threshold value for axis trigger.")
    parser.add_argument("--axis-direction", choices=["positive", "negative"], default="positive", help="Axis crossing direction that triggers a count.")
    parser.add_argument("--decrement-button", default=None, help="Optional button event code to decrement the counter.")
    parser.add_argument("--start", type=int, default=0, help="Starting counter value.")
    parser.add_argument("--goal", type=int, help="Optional goal count to display.")
    parser.add_argument("--audio", action="store_true", help="Play a short beep whenever the counter increases.")
    parser.add_argument("--verbose", action="store_true", help="Log raw events for debugging.")
    parser.add_argument("--debug-input", action="store_true", help="Print joystick control values repeatedly for debugging.")

    args = parser.parse_args()

    backend = select_input_backend()
    if backend == "unsupported":
        print("Error: no supported input backend is available on this platform.")
        print(f"Active Python interpreter: {sys.executable}")
        print("On Linux install evdev with 'python -m pip install evdev'.")
        print("On Windows install pyglet with 'python -m pip install pyglet'.")
        print("If you are using a virtual environment, make sure this script is run with that environment's Python.")
        sys.exit(1)

    if args.list:
        print_devices()
        return

    try:
        dev = find_device(device_path=args.device, name_pattern=args.name)
    except RuntimeError as exc:
        print(f"Error: {exc}")
        print("Use --list to discover connected input devices.")
        sys.exit(1)

    print(f"Using device: {dev.path} ({dev.name})")
    print("Press the pedal or button to increment the counter. Ctrl+C to exit.")

    count = args.start
    increment_code = parse_event_code(args.button, backend)
    axis_code = parse_event_code(args.axis, backend)
    decrement_code = parse_event_code(args.decrement_button, backend)

    if backend != "evdev" and args.axis is None:
        axis_code = 0
        args.axis = "0"

    if backend == "evdev":
        if args.axis and axis_code is None:
            print(f"Error: unknown axis code '{args.axis}'. Use --verbose and watch device output to discover the axis name.")
            sys.exit(1)
        if args.button and increment_code is None:
            print(f"Error: unknown button code '{args.button}'. Use --verbose and watch device output to discover the button name.")
            sys.exit(1)
    else:
        if args.axis and axis_code is None:
            if str(args.axis).isdigit():
                axis_code = int(args.axis)
            else:
                axis_code = args.axis.lower()
        if args.axis and axis_code is None:
            print(f"Error: unknown axis code '{args.axis}'. On Windows use a numeric axis index, for example --axis 0, or a named axis like --axis rz.")
            sys.exit(1)
        if args.button and increment_code is None:
            print(f"Error: unknown button code '{args.button}'. On Windows use a numeric button index, for example --button 0.")
            sys.exit(1)

    def show_count():
        goal_text = f" / {args.goal}" if args.goal is not None else ""
        print(f"Count: {count}{goal_text}", flush=True)

    show_count()

    button_name = args.button
    axis_name = args.axis
    decrement_name = args.decrement_button or "<none>"
    if axis_code is not None:
        print(f"Increment axis: {axis_name} ({axis_code}), threshold={args.axis_threshold}, direction={args.axis_direction}")
    else:
        print(f"Increment button: {button_name} ({increment_code})")
    if decrement_code:
        print(f"Decrement button: {decrement_name} ({decrement_code})")
    if args.goal is not None:
        print(f"Goal: {args.goal}")

    previous_axis_value = None
    print("Commands while running: +, -, set <n>, reset, status, quit")

    if backend == "pyglet":
        try:
            dev.open()
        except Exception as exc:
            print(f"Warning: unable to open joystick device: {exc}")
        dev._read_state()

    if args.debug_input and backend == "pyglet":
        print("Debug input mode: printing joystick axis values every 0.1s. Press Ctrl+C to stop.")

    try:
        if backend == "evdev":
            while True:
                ready, _, _ = select.select([dev.fd], [], [])

                command = read_pending_command()
                if command is not None:
                    count, should_exit = handle_command(command, count)
                    if should_exit:
                        break
                    if command:
                        if command in {"reset", "+", "-", "inc", "i", "dec", "d", "p", "status"} or command.startswith("set "):
                            show_count()
                        else:
                            print("Commands: +, -, set <n>, reset, status, quit")
                    continue

                if dev.fd in ready:
                    for event in dev.read():
                        if args.verbose:
                            if event.type == ecodes.EV_KEY:
                                code_name = ecodes.KEY.get(event.code, str(event.code))
                            elif event.type == ecodes.EV_ABS:
                                code_name = ecodes.ABS.get(event.code, str(event.code))
                            else:
                                code_name = str(event.code)
                            print(f"event: type={event.type} code={code_name} value={event.value}")

                        if axis_code is not None and event.type == ecodes.EV_ABS and event.code == axis_code:
                            if previous_axis_value is None:
                                previous_axis_value = event.value
                                continue

                            triggered = False
                            if args.axis_direction == "positive":
                                if previous_axis_value <= args.axis_threshold < event.value:
                                    triggered = True
                            else:
                                if previous_axis_value >= args.axis_threshold > event.value:
                                    triggered = True

                            previous_axis_value = event.value
                            if triggered:
                                count += 1
                                show_count()
                                play_beep(args)
                            continue

                        if event.type != ecodes.EV_KEY:
                            continue
                        if event.value != 1:
                            continue
                        if increment_code is not None and event.code == increment_code:
                            count += 1
                            show_count()
                            play_beep(args)
                        elif decrement_code and event.code == decrement_code:
                            count = max(0, count - 1)
                            show_count()
        else:
            while True:
                command = read_pending_command()
                if command is not None:
                    count, should_exit = handle_command(command, count)
                    if should_exit:
                        print("Stopping.", flush=True)
                        break
                    if command:
                        if command in {"reset", "+", "-", "inc", "i", "dec", "d", "p", "status"} or command.startswith("set "):
                            show_count()
                        else:
                            print("Commands: +, -, set <n>, reset, status, quit", flush=True)
                    continue

                pump_pyglet_events()

                if args.debug_input and backend == "pyglet":
                    dev._read_state()
                    print(f"debug: x={getattr(dev, 'x', None)} y={getattr(dev, 'y', None)} rz={getattr(dev, 'rz', None)} buttons={getattr(dev, 'buttons', None)}", flush=True)

                if axis_code is not None:
                    current_axis = get_axis_value(dev, axis_code)
                    if args.verbose:
                        print(f"axis {axis_name} value={current_axis}")
                    if previous_axis_value is None:
                        previous_axis_value = current_axis
                    else:
                        triggered = False
                        if args.axis_direction == "positive":
                            if previous_axis_value <= args.axis_threshold / 100.0 < current_axis:
                                triggered = True
                        else:
                            if previous_axis_value >= args.axis_threshold / 100.0 > current_axis:
                                triggered = True
                        previous_axis_value = current_axis
                        if triggered:
                            count += 1
                            show_count()
                            play_beep(args)

                if hasattr(dev, "buttons"):
                    buttons = getattr(dev, "buttons", [])
                    if buttons:
                        if increment_code is not None and increment_code < len(buttons) and buttons[increment_code]:
                            count += 1
                            show_count()
                            play_beep(args)
                        elif decrement_code is not None and decrement_code < len(buttons) and buttons[decrement_code]:
                            count = max(0, count - 1)
                            show_count()

                time.sleep(0.01)
    except KeyboardInterrupt:
        print()  # newline
        print("Stopped.")
    finally:
        if backend == "pyglet":
            dev.close()


if __name__ == "__main__":
    main()
