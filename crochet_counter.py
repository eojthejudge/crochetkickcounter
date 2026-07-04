#!/usr/bin/env python3
import argparse
import re
import select
import sys

try:
    from evdev import InputDevice, ecodes, list_devices
except ImportError:
    print("Missing dependency: python-evdev. Install it with 'pip install evdev' or your distro package manager.")
    sys.exit(1)


def list_input_devices():
    devices = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
        except OSError:
            continue
        devices.append((path, dev.name, dev.phys or ""))
    return devices


def find_device(device_path=None, name_pattern=None):
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


def print_devices():
    devices = list_input_devices()
    if not devices:
        print("No input devices found. Check your USB pedal is connected and you have permission to read /dev/input/event*.")
        return
    print("Input devices:")
    for path, name, phys in devices:
        print(f"  {path}\t{name}\t{phys}")


def main():
    parser = argparse.ArgumentParser(description="Crochet counter driven by a USB Saitek rudder pedal.")
    parser.add_argument("--list", action="store_true", help="List input devices and exit.")
    parser.add_argument("--device", help="Path to the event device, e.g. /dev/input/event3.")
    parser.add_argument("--name", default="saitek|rudder", help="Regex used to find the pedal device when --device is not provided.")
    parser.add_argument("--button", default=None, help="Button event code to use for incrementing the counter.")
    parser.add_argument("--axis", default="ABS_Y", help="Absolute axis event code to use for incrementing the counter, e.g. ABS_X or ABS_RUDDER.")
    parser.add_argument("--axis-threshold", type=int, default=10, help="Threshold value for axis trigger.")
    parser.add_argument("--axis-direction", choices=["positive", "negative"], default="positive", help="Axis crossing direction that triggers a count.")
    parser.add_argument("--decrement-button", default=None, help="Optional button event code to decrement the counter.")
    parser.add_argument("--start", type=int, default=0, help="Starting counter value.")
    parser.add_argument("--goal", type=int, help="Optional goal count to display.")
    parser.add_argument("--verbose", action="store_true", help="Log raw events for debugging.")

    args = parser.parse_args()

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
    print("Press the pedal pedal or button to increment the counter. Ctrl+C to exit.")

    def parse_event_code(value):
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if value.isdigit():
            return int(value)
        return ecodes.ecodes.get(value)

    count = args.start
    increment_code = parse_event_code(args.button)
    axis_code = parse_event_code(args.axis)
    decrement_code = parse_event_code(args.decrement_button)

    if args.axis and axis_code is None:
        print(f"Error: unknown axis code '{args.axis}'. Use --verbose and watch device output to discover the axis name.")
        sys.exit(1)

    if args.button and increment_code is None:
        print(f"Error: unknown button code '{args.button}'. Use --verbose and watch device output to discover the button name.")
        sys.exit(1)

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

    def show_count():
        goal_text = f" / {args.goal}" if args.goal is not None else ""
        print(f"Count: {count}{goal_text}")

    show_count()

    previous_axis_value = None

    stdin_fd = sys.stdin.fileno()
    print("Commands while running: +, -, set <n>, reset, status, quit")

    try:
        while True:
            ready, _, _ = select.select([dev.fd, stdin_fd], [], [])

            if stdin_fd in ready:
                line = sys.stdin.readline()
                if not line:
                    continue
                command = line.strip().lower()
                if command in {"q", "quit", "exit"}:
                    break
                if command in {"+", "inc", "i"}:
                    count += 1
                    show_count()
                    continue
                if command in {"-", "dec", "d"}:
                    count = max(0, count - 1)
                    show_count()
                    continue
                if command.startswith("set "):
                    try:
                        count = int(command.split(None, 1)[1])
                        show_count()
                    except ValueError:
                        print("Invalid set value. Use: set <number>")
                    continue
                if command == "reset":
                    count = 0
                    show_count()
                    continue
                if command in {"p", "status"}:
                    show_count()
                    continue
                if command:
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
                        continue

                    if event.type != ecodes.EV_KEY:
                        continue
                    if event.value != 1:
                        continue
                    if increment_code is not None and event.code == increment_code:
                        count += 1
                        show_count()
                    elif decrement_code and event.code == decrement_code:
                        count = max(0, count - 1)
                        show_count()
    except KeyboardInterrupt:
        print()  # newline
        print("Stopped.")


if __name__ == "__main__":
    main()
