# rpi-intercom

A room-to-room intercom system for Raspberry Pi with touchscreen display, powered by SIP and Asterisk. Rooms can call each other, conference calls are supported.

![Intercom 1](https://github.com/Michdo93/test2/blob/main/intercom.png?raw=true)
![Intercom 2](https://github.com/Michdo93/test2/blob/main/intercom2.png?raw=true)
![Intercom 3](https://github.com/Michdo93/test2/blob/main/intercom3.png?raw=true)

---

## Requirements

- Raspberry Pi 3B / 3B+
- Waveshare 3.5" Touchscreen Display
- Raspberry Pi OS Desktop (32-bit)
- Asterisk server running on your local network
- USB speakerphone: Plantronics Calisto 3200 (or compatible USB Audio Class device)

---

## Pre-Installation: Waveshare 3.5" Display

Install display drivers before setting up the application:

```bash
sudo apt update && sudo apt upgrade -y
git clone https://github.com/waveshare/LCD-show
cd LCD-show
sudo ./LCD35-show
```

The Pi will reboot automatically. After reboot, enable portrait mode:

```bash
echo "display_rotate=1" | sudo tee -a /boot/config.txt
sudo reboot
```

---

## Audio Setup: Plantronics Calisto 3200

The Plantronics Calisto 3200 is a USB speakerphone with built-in echo cancellation and noise reduction. It is recognized as a standard USB Audio Class device on Linux — no driver installation required.

### 1. Plug in the device and verify recognition

```bash
lsusb
aplay -l
arecord -l
```

The device should appear as a new audio card, typically `card 1`.

### 2. Set as default audio device

```bash
sudo nano /etc/asound.conf
```

```
defaults.pcm.card 1
defaults.ctl.card 1
```

### 3. Test microphone and speaker

```bash
# Record a 5-second test clip
arecord -d 5 -D hw:1,0 -f cd /tmp/test.wav

# Play it back
aplay -D hw:1,0 /tmp/test.wav
```

### 4. Set volume

```bash
amixer -c 1 sset Master 80%
```

To make the volume setting persistent across reboots:

```bash
sudo alsactl store
```

### Note on PulseAudio / PipeWire

If PulseAudio or PipeWire is active (default on Raspberry Pi OS Desktop), the card index may change. In that case, identify the device by name instead:

```bash
pactl list short sinks
pactl list short sources
```

Set by name in `/etc/asound.conf` if needed:

```
defaults.pcm.!default {
    type hw
    card Calisto
}
defaults.ctl.!default {
    type hw
    card Calisto
}
```

---

## Installation

### 1. Install dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-tk linphone-cli alsa-utils
```

### 2. Clone the repository

```bash
cd /opt
git clone https://github.com/Michdo93/rpi-intercom.git
cd rpi-intercom
```

### 3. Set up virtual environment

```bash
python3 -m venv .
source ./bin/activate
pip install pillow
```

### 4. Create configuration

```bash
cp config.example.py config.py
nano config.py
```

Adjust the following values:

```python
SIP_SERVER   = "192.168.1.50"   # IP address of your Asterisk server
SIP_PORT     = 5060

MY_USERNAME  = "room1"          # SIP username for this device
MY_PASSWORD  = "room1pass"      # SIP password
MY_ROOM_NAME = "Conference"     # Display name for this room

ROOMS = {
    "Conference": "501",
    "Kitchen":    "502",
    "Bathroom":   "503",
    "IoT":        "504",
    "Multimedia": "505",
}
```

### 5. Run

```bash
source ./bin/activate
python main.py
```

---

## Autostart

```bash
sudo nano /etc/systemd/system/intercom.service
```

```ini
[Unit]
Description=Intercom
After=network.target

[Service]
User=pi
WorkingDirectory=/opt/rpi-intercom
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStart=/opt/rpi-intercom/bin/python3 main.py
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable intercom
sudo systemctl start intercom
```

---

## Asterisk Configuration

This application connects to an Asterisk server. See the companion repository [asterisk-smarthome](https://github.com/Michdo93/asterisk-smarthome) for the full Asterisk setup.

Add one endpoint per room to `/etc/asterisk/pjsip.conf`:

```ini
[room1]
type=endpoint
context=smarthome
disallow=all
allow=ulaw
allow=alaw
allow=g722
allow=opus
auth=room1
aors=room1
media_encryption=sdes
media_encryption_optimistic=yes
rtp_symmetric=yes
rewrite_contact=yes

[room1]
type=auth
auth_type=userpass
username=room1
password=room1pass

[room1]
type=aor
max_contacts=1
remove_existing=yes
```

Add intercom extensions to `/etc/asterisk/extensions.conf`:

```ini
[smarthome]
exten => 501,1,Dial(PJSIP/room1,30)
 same => n,Hangup()

exten => 502,1,Dial(PJSIP/room2,30)
 same => n,Hangup()

exten => 503,1,Dial(PJSIP/room3,30)
 same => n,Hangup()

exten => 504,1,Dial(PJSIP/room4,30)
 same => n,Hangup()

exten => 505,1,Dial(PJSIP/room5,30)
 same => n,Hangup()
```

Reload after changes:

```bash
sudo asterisk -r
pjsip reload
dialplan reload
exit
```

---

## Customization

### Rooms and extensions

Edit the `ROOMS` dictionary in `config.py`:

```python
ROOMS = {
    "Living Room": "501",
    "Bedroom":     "502",
    "Office":      "503",
}
```

### Room icons

Edit the `ROOM_ICONS` dictionary in `ui.py`:

```python
ROOM_ICONS = {
    "Living Room": "🛋",
    "Bedroom":     "🛏",
    "Office":      "💻",
}
```

### Service buttons (Calendar, Weather, News)

Edit `SERVICE_BUTTONS` in `ui.py`:

```python
SERVICE_BUTTONS = [
    ("📅", "Calendar",   "601"),
    ("🌤", "Weather",    "602"),
    ("📰", "News",       "603"),
]
```

### Test buttons (STT/TTS)

Edit `TEST_BUTTONS` in `ui.py`:

```python
TEST_BUTTONS = [
    ("🎤", "STT Test",          "100"),
    ("🔊", "TTS Test",          "200"),
    ("🧠", "Whisper (single)",  "300"),
    ("🔁", "Whisper (loop)",    "400"),
]
```

---

## Per-device configuration

| Device | MY_USERNAME | MY_PASSWORD | MY_ROOM_NAME |
|--------|-------------|-------------|--------------|
| Pi 1   | room1       | room1pass   | Conference   |
| Pi 2   | room2       | room2pass   | Kitchen      |
| Pi 3   | room3       | room3pass   | Bathroom     |
| Pi 4   | room4       | room4pass   | IoT          |
| Pi 5   | room5       | room5pass   | Multimedia   |

---

## License

MIT
