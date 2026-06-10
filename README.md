# rpi-intercom

A room-to-room intercom system for Raspberry Pi with touchscreen display, powered by SIP and Asterisk. Rooms can call each other, conference calls are supported.

---

## Requirements

- Raspberry Pi 3B / 3B+ with touchscreen (e.g. Waveshare 3.5")
- Raspberry Pi OS Desktop (32-bit)
- Asterisk server running on your local network
- USB speakerphone (e.g. EMEET e104)

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
    "Conference": "101",
    "Kitchen":    "102",
    "Bathroom":   "103",
    "IoT":        "104",
    "Multimedia": "105",
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

Add one endpoint per room to `/etc/asterisk/pjsip.conf`:

```ini
[raum1]
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

[rom1]
type=auth
auth_type=userpass
username=room1
password=room1pass

[room1]
type=aor
max_contacts=1
remove_existing=yes
```

Add extensions to `/etc/asterisk/extensions.conf`:

```ini
[smarthome]
exten => 101,1,Dial(PJSIP/room1,30)
 same => n,Hangup()

exten => 102,1,Dial(PJSIP/room2,30)
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
    "Living Room": "101",
    "Bedroom":     "102",
    "Office":      "103",
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

Any emoji works — it will be displayed as the room tile icon.

### Portrait mode (touchscreen)

```bash
sudo nano /boot/config.txt
```

```ini
display_rotate=1
```

### Set default audio device (USB speakerphone)

Check the card number after plugging in:

```bash
aplay -l
arecord -l
```

Set as default:

```bash
sudo nano /etc/asound.conf
```

```
defaults.pcm.card 1
defaults.ctl.card 1
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
