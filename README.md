# Brightness Sync

**Automatic laptop brightness control via iPhone Shortcuts**

A Windows desktop application that syncs your laptop's screen brightness with your iPhone's brightness sensor. Features perceptual brightness calibration, system tray integration, and smooth transitions.

## Features

- **iPhone Integration**: Control brightness via iPhone Shortcuts app
- **Perceptual Calibration**: Accounts for different display characteristics (iPhone XR 625 nits vs laptop 300 nits)
- **System Tray**: Clean GUI with context menu controls
- **Smooth Transitions**: Gradual brightness changes for eye comfort
- **Auto Brightness**: Time-based automatic brightness adjustment
- **Windows Autostart**: Optional startup with Windows

## Quick Start

### 1. Install and Run

**Option A: Pre-built executable**
```bash
# Run the installer
install.bat

# Or run directly
dist/BrightnessSync.exe
```

**Option B: From source**
```bash
pip install flask screen-brightness-control pystray pillow
python brightness_tray.py
```

### 2. Configure iPhone Shortcuts

1. Open **Shortcuts** app on iPhone
2. Create new shortcut with these actions:
   - **Get Current Brightness** (from Device Details)
   - **Get Contents of URL**
     - URL: `http://YOUR_PC_IP:5000/brightness`
     - Method: `POST`
     - Headers: `Content-Type: application/json`
     - Request Body: **Dictionary**
       - `brightness`: *Get Current Brightness result*
       - `smooth`: `true` (Boolean)

3. Replace `YOUR_PC_IP` with your computer's IP address

### 3. Find Your PC's IP Address

```bash
ipconfig | findstr "IPv4"
```

## API Endpoints

The server runs on port 5000 and provides these endpoints:

### POST /brightness
Set brightness with various input formats:
```json
{"brightness": 0.5, "smooth": true}          // iPhone brightness (0-1)
{"level": "normal", "smooth": true}          // Predefined levels
{"time_based": true, "smooth": true}         // Auto by time of day
{"lux": 300, "smooth": true}                 // Light sensor data
```

### GET /brightness
Get current brightness:
```json
{"current_brightness": 65, "timestamp": "2024-01-01T12:00:00"}
```

### POST /auto
Auto brightness by time of day

### GET /health
Server status check

### GET /config
View current configuration

## Brightness Calibration

The app includes perceptual calibration between iPhone XR (625 nits) and laptop displays (~300 nits):

- **LUT Mode**: Lookup table with interpolation (default)
- **Perceptual Mode**: Gamma curve calibration (γ=2.2)
- **Logarithmic Mode**: Log-based brightness scaling
- **Linear Mode**: Simple proportional mapping

Example mappings (iPhone → Laptop):
- 50% → 68%
- 25% → 32%
- 75% → 82%

## Configuration

Edit `brightness_server.py` to customize:

```python
CONFIG = {
    'display_calibration': {
        'iphone_max_nits': 625,        # Your iPhone model's max brightness
        'laptop_max_nits': 300,        # Your laptop's max brightness
        'brightness_curve': 'lut',     # Calibration method
    },
    'time_based_brightness': {
        'night': {'start': '22:00', 'end': '06:00', 'level': 'very_dark'},
        'day': {'start': '09:00', 'end': '18:00', 'level': 'bright'},
    }
}
```

## Requirements

- **Windows 10/11**
- **Python 3.7+** (if running from source)
- **iPhone** with Shortcuts app
- **WiFi network** (iPhone and PC must be on same network)

### Python Dependencies
```
flask>=2.0.0
screen-brightness-control>=0.20.0
pystray>=0.19.0
pillow>=8.0.0
```

## System Tray Menu

Right-click the system tray icon for:
- Current brightness display
- Quick brightness presets (10%, 25%, 50%, 75%, 100%)
- Auto brightness by time
- Toggle Windows autostart
- Open web interface
- View logs

## Troubleshooting

**iPhone Shortcuts not working:**
- Verify PC and iPhone are on same WiFi network
- Check Windows Firewall settings for port 5000
- Confirm server is running (check system tray)

**Brightness not changing:**
- Ensure display drivers are installed
- Some external monitors don't support software brightness control
- Try running as administrator

**Autostart not working:**
- Check Windows startup apps in Task Manager
- Verify antivirus isn't blocking the executable

## Building from Source

```bash
# Install build dependencies
pip install pyinstaller

# Build executable
python -m PyInstaller --onefile --windowed --name=BrightnessSync brightness_tray.py

# Create installer
install.bat
```

## License

MIT License - feel free to modify and distribute.

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## Support

- Create an issue for bugs or feature requests
- Check the logs folder for debugging information
- Ensure your display supports programmatic brightness control