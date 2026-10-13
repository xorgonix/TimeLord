# ActiveWindow Time Tracker

A cross-platform desktop application that passively tracks user productivity by monitoring the active foreground window and detecting user input (mouse/keyboard).

## Features

- **Automatic Window Tracking**: Monitors active foreground window every 1 second
- **Idle Detection**: Detects when you're away from keyboard (configurable threshold)
- **Privacy-First**: All data stored locally in SQLite database
- **System Tray Integration**: Minimize to tray, quick access
- **Beautiful Dashboard**: View your daily activity with AG Grid timeline
- **Native Desktop App**: Runs as a native desktop application

## Installation

### From Source

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd TimeLord
   ```

2. **Create virtual environment** (using uv):
   ```bash
   uv venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies**:
   ```bash
   uv pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   .venv\Scripts\python.exe main.py  # Windows
   .venv/bin/python main.py  # macOS/Linux
   ```

### From Executable (Windows)

1. **Build the executable**:
   ```bash
   pyinstaller build.spec
   ```

2. **Find the executable** in `dist/TimeLord/TimeLord.exe`

3. **Run** `TimeLord.exe`

## Usage

1. **Start the application** - The app launches in the system tray
2. **Click the tray icon** to open the dashboard
3. **Use your computer normally** - TimeLord tracks active windows automatically
4. **View your activity** in the dashboard timeline
5. **Minimize to tray** - Click the minimize button or use tray menu

## Project Structure

```
TimeLord/
├── app/
│   ├── core/
│   │   ├── tracker.py      # Window tracking and idle detection
│   │   ├── database.py     # SQLite database operations
│   │   └── models.py       # Data models
│   ├── ui/
│   │   └── dashboard.py    # Main dashboard UI
│   ├── utils/
│   │   └── tray.py         # System tray integration
│   └── tests/              # Test files
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── build.spec             # PyInstaller build configuration
└── PROJECT_SPEC.md        # Project specification
```

## Technical Stack

- **UI Framework**: NiceGUI (FastAPI + Vue.js + Quasar)
- **System Hooks**: pynput (input), pygetwindow (window tracking)
- **Database**: SQLite
- **System Tray**: pystray
- **Packaging**: PyInstaller

## Configuration

Edit settings in the database (future: settings UI):

- `idle_threshold`: Seconds before considered idle (default: 60)
- `theme`: UI theme (default: light)

## Privacy

- All data stored locally in `timelord.db`
- No network requests for telemetry
- No keystroke content logging (only input events)
- Database file can be encrypted (future: sqlcipher support)

## Development

### Running in Development Mode

```bash
.venv\Scripts\python.exe -m nicegui main.py
```

### Building for Production

```bash
pyinstaller build.spec --clean
```

## Troubleshooting

### macOS Permissions
macOS requires Accessibility permissions for input monitoring. Go to:
`System Preferences → Security & Privacy → Privacy → Accessibility`
Add TimeLord to the list.

### Linux Dependencies
May require additional packages:
```bash
sudo apt-get install python3-tk python3-dev
```

## License

MIT License

## Contributing

Contributions welcome! Please read the project specification first.
