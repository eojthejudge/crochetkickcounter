# Crochet Kick Counter

A simple Linux counter for crocheting that increments when a USB Saitek rudder pedal button is pressed.

## Setup

1. Install Python 3 if not already installed.
2. Install the dependency:

```bash
python3 -m pip install evdev
```

On Debian/Ubuntu you can also install system package:

```bash
sudo apt install python3-evdev
```

## Usage

List input devices:

```bash
python3 crochet_counter.py --list
```

Run the counter with an explicit event device path:

```bash
python3 crochet_counter.py --device /dev/input/event3
```

Or just run the script directly with the default axis settings for your pedal:

```bash
python3 crochet_counter.py
```

The default behavior is now:
- `--axis ABS_Y`
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

If the pedal button is not `BTN_0`, set the button explicitly using the event code name from the device output:

```bash
python3 crochet_counter.py --button BTN_1
```

If the pedal has no button and only reports axis motion, use `--axis` instead. Start by running:

```bash
python3 crochet_counter.py --verbose --device /dev/input/eventX
```

Watch for lines like `event: type=3 code=ABS_X value=...` or `ABS_RUDDER`.

Then run with the axis name and threshold:

```bash
python3 crochet_counter.py --axis ABS_RUDDER --axis-threshold 10 --axis-direction positive --device /dev/input/eventX
```

## Notes

- The script reads raw Linux input events from `/dev/input/event*`.
- You may need to run it with `sudo` or set device permissions so your user can access the event file.
- Press the pedal once to increment the count. Use Ctrl+C to stop.
