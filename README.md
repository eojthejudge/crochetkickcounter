# Crochet Kick Counter

A cross-platform counter for crocheting that increments from a USB pedal or game controller.

## Setup

1. Install Python 3 if not already installed.
2. Install the dependencies for your platform:

Linux:

```bash
python3 -m pip install -r requirements.txt
```

Windows:

```powershell
py -m pip install -r requirements.txt
```

If you are on Linux and want the raw input backend, you can also install the system package:

```bash
sudo apt install python3-evdev
```

## Usage

List input devices:

```bash
python3 crochet_counter.py --list
```

Linux example with an explicit event device path:

```bash
python3 crochet_counter.py --device /dev/input/event3
```

Windows example with a joystick index:

```powershell
py crochet_counter.py --device 0
```

Or just run the script directly with the default settings:

```bash
python3 crochet_counter.py
```

The default behavior is now:
- `--axis ABS_Y` on Linux
- `--axis 0` on Windows
- `--axis-threshold 10`
- `--axis-direction positive`

To hear a short beep whenever the counter increases, run:

```bash
python3 crochet_counter.py --audio
```

While the counter is running, you can type commands into the terminal:
- `+`, `inc`, `i`: increment
- `-`, `dec`, `d`: decrement
- `set <n>`: set a specific value
- `reset`: reset to 0
- `status`, `p`: print current count
- `quit`, `exit`, `q`: stop the program

If the pedal button is not `BTN_0`, set the button explicitly using the event code name from the device output on Linux:

```bash
python3 crochet_counter.py --button BTN_1
```

On Windows, use a numeric button index instead, for example:

```powershell
py crochet_counter.py --button 0
```

If the pedal has no button and only reports axis motion, use `--axis` instead. On Linux start by running:

```bash
python3 crochet_counter.py --verbose --device /dev/input/eventX
```

Watch for lines like `event: type=3 code=ABS_X value=...` or `ABS_RUDDER`.

Then run with the axis name and threshold:

```bash
python3 crochet_counter.py --axis ABS_RUDDER --axis-threshold 10 --axis-direction positive --device /dev/input/eventX
```

## Notes

- On Linux the script reads raw input events from `/dev/input/event*`.
- On Windows it uses pygame and joystick events instead.
- You may need to run Linux with `sudo` or set device permissions so your user can access the event file.
- Press the pedal once to increment the count. Use Ctrl+C to stop.
