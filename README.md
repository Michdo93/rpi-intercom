# rpi-intercom

A room-to-room intercom system for Raspberry Pi with a touchscreen display, powered by SIP and Asterisk. Rooms can call each other, and the system can be extended with conference calls and additional SIP services.

![Intercom 1](https://github.com/Michdo93/test2/blob/main/intercom.png?raw=true)
![Intercom 2](https://github.com/Michdo93/test2/blob/main/intercom2.png?raw=true)
![Intercom 3](https://github.com/Michdo93/test2/blob/main/intercom3.png?raw=true)

---

## Features

- Touchscreen interface for room-to-room communication
- SIP-based communication through an Asterisk server
- Configurable rooms and extension numbers
- Optional service and test buttons for integrations with other services
- Fullscreen interface for kiosk-style operation
- Local configuration without requiring a cloud service

## Requirements

### Hardware

- Raspberry Pi 3 Model B or Raspberry Pi 3 Model B+
- 3.5-inch SPI touchscreen display compatible with the `piscreen` DRM device-tree overlay
- USB speakerphone or compatible audio input/output device
- Network connection to the Asterisk server

The display setup described below was tested with a 3.5-inch SPI display using an ILI9486-compatible display controller and an XPT2046/ADS7846-compatible touchscreen controller.

Other displays may require different device-tree overlays, rotation settings, or touchscreen calibration.

### Software

- DietPi with Debian 13 (Trixie)
- X11 with Openbox
- Python 3 and Tkinter
- Python virtual environment
- `baresip` for SIP communication
- An Asterisk server on the local network

The instructions below describe the tested DietPi setup. Other operating systems may require different configuration paths and package names.

---

## 1. Prepare DietPi

Update the package lists and installed packages:

```bash
sudo apt update
sudo apt upgrade -y
```

Install the application dependencies:

```bash
sudo apt install -y \
    git \
    python3 \
    python3-venv \
    python3-tk \
    baresip \
    alsa-utils \
    xserver-xorg \
    xinit \
    x11-xserver-utils \
    openbox \
    lightdm
```

If a package is already installed, APT will leave the existing installation in place.

Verify that the required commands are available:

```bash
python3 --version
baresip -h
```

The graphical environment must be working before configuring the application to start automatically.

---

## 2. Configure the SPI touchscreen

### 2.1. Enable the display overlay

On the tested DietPi installation, the boot configuration is located at `/boot/firmware/config.txt`. The path `/boot/config.txt` may be a symbolic link to this file.

Open the configuration:

```bash
sudo nano /boot/firmware/config.txt
```

Use the following settings for the tested display:

```ini
max_framebuffers=1
hdmi_blanking=1
dtoverlay=piscreen,drm,rotate=90
dtparam=spi=on
dtoverlay=disable-bt
```

Check for duplicate or conflicting display and SPI settings before saving.

**Important:** `dtoverlay=disable-bt` disables the Raspberry Pi's onboard Bluetooth functionality. Remove this setting if Bluetooth is required and your display configuration allows it.

Reboot:

```bash
sudo reboot
```

After reboot, check that the display is detected and that the graphical desktop has the expected portrait orientation.

The physical display is 480 × 320 pixels; with the tested rotation, X11 reports a 320 × 480 portrait workspace.

### 2.2. Correct touchscreen coordinates

The touchscreen controller may report coordinates in a different orientation from the rotated display. On the tested system, the device is named `ADS7846 Touchscreen`.

Check the detected input devices:

```bash
DISPLAY=:0 xinput list
```

Apply the tested coordinate transformation:

```bash
DISPLAY=:0 \
xinput set-prop "ADS7846 Touchscreen" \
"Coordinate Transformation Matrix" \
0 1 0 1 0 0 0 0 1
```

The command must run in the active X11 session. If it reports that it cannot open the display, run it from that session or supply the correct `DISPLAY` and `XAUTHORITY` environment variables.

### 2.3. Make touchscreen rotation persistent

Create a script in the DietPi user's home directory:

```bash
mkdir -p /home/dietpi/.config

nano /home/dietpi/.config/touchscreen.sh
```

Add:

```sh
#!/bin/sh

xinput set-prop "ADS7846 Touchscreen" \
    "Coordinate Transformation Matrix" \
    0 1 0 1 0 0 0 0 1
```

Make it executable:

```bash
chmod +x /home/dietpi/.config/touchscreen.sh
```

Open the Openbox autostart file:

```bash
mkdir -p /home/dietpi/.config/openbox

nano /home/dietpi/.config/openbox/autostart
```

Add the following line:

```sh
/home/dietpi/.config/touchscreen.sh &
```

If the file already contains other startup commands, keep them and add this line rather than replacing the entire file.

The transformation is applied when Openbox starts. If the touchscreen is not yet available at that moment, the script may need to be retried after the X11 session has initialized.

---

## 3. Install the application

Clone the repository into `/opt/rpi-intercom`:

```bash
cd /opt
sudo git clone https://github.com/Michdo93/rpi-intercom.git
sudo chown -R dietpi:dietpi /opt/rpi-intercom
cd /opt/rpi-intercom
```

Create a Python virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install the Python dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install pillow
```

If the repository provides a maintained `requirements.txt`, install its dependencies instead of maintaining a separate list manually:

```bash
python -m pip install -r requirements.txt
```

The application uses Tkinter for its graphical interface. On Debian-based systems, Tkinter is provided by the `python3-tk` package.

---

## 4. Configure the application

Create the local configuration file:

```bash
cd /opt/rpi-intercom
cp config.example.py config.py
nano config.py
```

If `config.example.py` is not present in your checkout, create `config.py` using the configuration options supported by the version of the application you installed.

Set the address of your Asterisk server, SIP credentials, room names, and extension numbers.

Example:

```python
SIP_SERVER = "192.168.0.66"
SIP_PORT = 5060

MY_USERNAME = "room1"
MY_PASSWORD = "change-this-password"
MY_ROOM_NAME = "Konferenz"

ROOMS = {
    "Konferenz": "501",
    "Küche": "502",
    "Bad": "503",
    "IoT": "504",
    "Multimedia": "505",
}

SERVICE_EXTENSIONS = {
    "Kalender": "601",
    "Wetter": "602",
    "Nachrichten": "603",
}

TEST_EXTENSIONS = {
    "STT Test": "100",
    "TTS Test": "200",
    "Whisper (einmalig)": "300",
    "Whisper (Schleife)": "400",
}

DEFAULT_VOLUME = 80
DEFAULT_BRIGHTNESS = 80
FULLSCREEN = True
```

Use the option names supported by your checked-out `config.py` and `config.example.py`; do not add options that the installed application does not read.

Each intercom device needs its own SIP username, password, and room name. The extension numbers must match the dialplan on the Asterisk server.

**Security:** Do not commit real SIP passwords to a public repository. Keep `config.py` local and use unique credentials for each device.

---

## 5. Configure audio

The application requires a working microphone and speaker. A USB speakerphone such as the Plantronics Calisto 3200 can provide both.

### 5.1. Identify the audio device

Connect the device and run:

```bash
lsusb
aplay -l
arecord -l
```

Use the output to identify the correct playback and capture devices. Do not assume that the USB device will always be `card 1`; ALSA card numbers can change between systems and reboots.

### 5.2. Test playback and recording

For a device identified as `hw:1,0`, record a short test:

```bash
arecord -d 5 -D hw:1,0 -f cd /tmp/test.wav
```

Play it back:

```bash
aplay -D hw:1,0 /tmp/test.wav
```

Replace `hw:1,0` with the device identifier shown on your system.

If recording or playback fails, inspect the available ALSA devices and mixer controls:

```bash
aplay -L
arecord -L
alsamixer
```

### 5.3. Set the volume

List the available mixer controls:

```bash
amixer -c 1 scontrols
```

If the card provides a `Master` control, its volume can be adjusted with:

```bash
amixer -c 1 sset Master 80%
```

Replace the card number and control name with the values available on your device. Some USB audio devices expose different controls or manage their volume internally.

The audio device used by `baresip` must be configured consistently with the device that passed the recording and playback tests. A successful ALSA test alone does not guarantee that SIP audio is configured correctly.

---

## 6. Run the application manually

First, start the application from a working graphical session:

```bash
cd /opt/rpi-intercom
source .venv/bin/activate
python main.py
```

Alternatively, use the virtual environment's interpreter directly:

```bash
cd /opt/rpi-intercom
DISPLAY=:0 \
XAUTHORITY=/home/dietpi/.Xauthority \
.venv/bin/python main.py
```

The second command assumes that the X11 session is running on display `:0` and uses the DietPi user's X authority file.

Verify the following before configuring autostart:

- The interface opens on the touchscreen.
- Touch input selects the intended buttons.
- The application can register with the Asterisk server.
- Calls can be placed and answered.
- Microphone and speaker audio work in both directions.

If the application does not start, inspect its terminal output before proceeding.

---

## 7. Configure automatic kiosk startup

The application uses Tkinter and needs an active graphical session. For the tested DietPi configuration, start it from Openbox's autostart file rather than running it as a headless system service.

### 7.1. Configure automatic login

Configure LightDM to log in as `dietpi` and start the Openbox session.

The exact LightDM configuration file can vary with the installed DietPi setup. Check the active LightDM configuration before editing it. Ensure that automatic login is enabled for the `dietpi` user and that the selected session is `openbox`.

After changing the display-manager configuration, reboot and verify that the graphical session starts without manual login.

### 7.2. Start the intercom from Openbox

Edit the autostart file:

```bash
nano /home/dietpi/.config/openbox/autostart
```

Keep the touchscreen transformation command and add the intercom startup command:

```sh
/home/dietpi/.config/touchscreen.sh &

cd /opt/rpi-intercom
DISPLAY=:0 XAUTHORITY=/home/dietpi/.Xauthority \
    /opt/rpi-intercom/.venv/bin/python /opt/rpi-intercom/main.py &
```

If the touchscreen script is already present, do not add it a second time.

Reboot and verify that the display, touch input, and intercom interface start automatically.

---

## 8. Asterisk configuration

The intercom communicates with an Asterisk server using SIP. The server must have corresponding SIP endpoints, authentication credentials, and dialplan extensions.

See the companion repository [asterisk-smarthome](https://github.com/Michdo93/asterisk-smarthome) for the associated Asterisk setup.

The following is an example for a PJSIP endpoint. Adapt the codecs, transport, media settings, context, and authentication to the server's existing configuration.

### 8.1. Configure PJSIP endpoints

Add one endpoint, authentication section, and AOR per intercom device in `/etc/asterisk/pjsip.conf`.

Example for `room1`:

```ini
[room1]
type=endpoint
context=smarthome
disallow=all
allow=ulaw
allow=alaw
auth=room1
aors=room1
rtp_symmetric=yes
force_rport=yes
rewrite_contact=yes

[room1]
type=auth
auth_type=userpass
username=room1
password=change-this-password

[room1]
type=aor
max_contacts=1
remove_existing=yes
```

Use unique section names and credentials for each device. The example uses a simple endpoint configuration; secure the SIP transport and media appropriately for your network. Codec availability and encryption settings must be consistent with the Asterisk server and the SIP client.

### 8.2. Configure the dialplan

Add the room extensions to the appropriate context in `/etc/asterisk/extensions.conf`:

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

The `Dial()` destinations must match the endpoint names in `pjsip.conf`, and the extension numbers must match the `ROOMS` dictionary in each intercom's `config.py`.

### 8.3. Reload Asterisk

Connect to the Asterisk console:

```bash
sudo asterisk -r
```

Reload the configuration:

```text
pjsip reload
dialplan reload
```

Then exit:

```text
exit
```

Verify that the endpoints register successfully before testing calls between rooms.

---

## 9. Customize rooms and extensions

Room names and extension numbers are configured in `config.py`.

For example:

```python
ROOMS = {
    "Wohnzimmer": "501",
    "Schlafzimmer": "502",
    "Büro": "503",
}
```

Every room extension must also exist in the Asterisk dialplan.

### Room icons

If the UI version defines a `ROOM_ICONS` dictionary in `ui.py`, edit that dictionary to change the icons associated with room names.

Example:

```python
ROOM_ICONS = {
    "Living Room": "🛋",
    "Bedroom": "🛏",
    "Office": "💻",
}
```

Emoji rendering depends on the fonts available in the graphical environment. If a glyph is missing, install a suitable font or use a simpler text label.

### Service buttons

If the UI version defines `SERVICE_BUTTONS`, these entries can be used to configure additional SIP service destinations.

Example:

```python
SERVICE_BUTTONS = [
    ("📅", "Calendar", "601"),
    ("🌤", "Weather", "602"),
    ("📰", "News", "603"),
]
```

The corresponding extensions must be implemented on the Asterisk server.

### Test buttons

If the UI version defines `TEST_BUTTONS`, the entries can be customized in the same way.

Example:

```python
TEST_BUTTONS = [
    ("🎤", "STT Test", "100"),
    ("🔊", "TTS Test", "200"),
    ("🧠", "Whisper (single)", "300"),
    ("🔁", "Whisper (loop)", "400"),
]
```

These buttons do not implement speech recognition or text-to-speech themselves. Their behavior depends on the destination extensions and the services configured on the Asterisk server.

The available dictionaries and button definitions depend on the version of `ui.py` in the repository.

---

## 10. Per-device configuration

Each Raspberry Pi should use a unique SIP account and a matching room extension.

| Device | SIP username | Example extension | Room name |
|---|---|---:|---|
| Pi 1 | `room1` | 501 | Konferenz |
| Pi 2 | `room2` | 502 | Küche |
| Pi 3 | `room3` | 503 | Bad |
| Pi 4 | `room4` | 504 | IoT |
| Pi 5 | `room5` | 505 | Multimedia |

The passwords are configured individually and should not be shared between devices.

---

## Troubleshooting

### Display is blank or incorrectly rotated

- Check the display overlay in `/boot/firmware/config.txt`.
- Verify that SPI is enabled.
- Confirm that the selected overlay is compatible with the display controller.
- Check the X11 display resolution and orientation.

### Touch input is rotated or offset

- Verify the detected input device with `xinput list`.
- Check the coordinate transformation matrix.
- Confirm that `touchscreen.sh` is executed from Openbox autostart after the graphical session has started.

### Application does not start

Run the application manually to see Python errors:

```bash
cd /opt/rpi-intercom
.venv/bin/python main.py
```

Check that the virtual environment contains the required packages and that Tkinter is installed.

### SIP registration or calls fail

- Check network connectivity to the Asterisk server.
- Verify the SIP server address, port, username, and password in `config.py`.
- Check the Asterisk endpoint registration and dialplan.
- Inspect the output from the SIP client and the Asterisk console.

### No microphone or speaker audio

- Check the ALSA devices with `aplay -l` and `arecord -l`.
- Test recording and playback independently of the intercom application.
- Verify the audio device configured in `baresip`.
- Check that the selected codecs are supported by both sides.

---

## License

MIT
