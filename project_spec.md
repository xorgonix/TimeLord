

***  

# PROJECT_SPEC.md

# Project Specification: ActiveWindow Time Tracker (Python/NiceGUI Edition)

## 1. Executive Summary
Build a cross-platform desktop application that passively tracks user productivity by monitoring the active foreground window and detecting user input (mouse/keyboard). 
- **Core Logic:** Python-based system monitoring.
- **UI Framework:** NiceGUI (Python web framework wrapped as a native app).
- **Privacy:** Local-first storage (SQLite).
- **Goal:** Functionally similar to "Memtime" but built as a standalone private tool using Python.

## 2. Technical Stack
- **Language:** Python 3.10+
- **UI Framework:** NiceGUI (built on FastAPI, Vue.js, Quasar, Tailwind)
- **System Hooks:** 
  - `pynput` (for keyboard/mouse listening)
  - `pygetwindow` or `psutil` (for foreground window detection)
  - `platform` specific checks (winreg for Windows, Quartz for macOS if needed)
- **Database:** SQLite (via `sqlite3` or `SQLModel`)
- **Packaging:** `pyinstaller` or NiceGUI `ui.run(native=True)` for desktop experience.

## 3. Project Directory Structure
```text
/app
  /core            # Tracking logic, hooks, database models
  /ui              # NiceGUI pages, components, layouts
  /utils           # Helpers (idle detection, time formatting)
  /tests           # NiceGUI testing fixtures
main.py            # Entry point (ui.run)
PROJECT_SPEC.md    # This file
requirements.txt   # Dependencies


## 4. Core Logic Requirements

### 4.1 Window Tracking (Background Task)
- **Implementation:** Must run in a non-blocking background task (`background_tasks.create`) to avoid freezing the NiceGUI event loop.
- **Polling Interval:** Check foreground window every 1 second.
- **Event Trigger:** Record a new event ONLY when:
  1. The foreground window process ID changes.
  2. OR the user becomes idle (see 4.2).
  3. OR the user resumes from idle.
- **Data to Capture:**
  - `process_name` (e.g., "WINWORD.EXE")
  - `window_title` (e.g., "Report.docx - Word")
  - `start_time` (Unix timestamp)
  - `end_time` (Unix timestamp, null if active)

### 4.2 Idle Detection
- **Definition:** No mouse movement, clicks, or keyboard input globally.
- **Threshold:** Configurable (default 60 seconds).
- **Behavior:**
  - If idle > threshold: Close current active event with `end_time`.
  - Create an "Idle" state record.
  - Do NOT attribute idle time to any application.
  - On resume: Start new event for the current foreground window.
- **Concurrency:** Input monitoring must use `run.io_bound` or a separate thread to avoid blocking the NiceGUI async loop.

### 4.3 Input Monitoring
- Monitor global input hooks to reset idle timer.
- **Security:** Do not log *content* of keystrokes, only the *event* of a keystroke.
- **Mouse Jiggler Note:** The system treats simulated input as real input. Do not attempt to detect hardware vs. software input.

## 5. Data Schema (SQLite)

### Table: `events`
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment |
| `start_ts` | INTEGER NOT NULL | Unix timestamp (ms) |
| `end_ts` | INTEGER | Unix timestamp (ms), NULL if active |
| `app_name` | TEXT NOT NULL | Executable name |
| `window_title` | TEXT | Window title string |
| `process_id` | INTEGER | OS Process ID |
| `is_idle` | BOOLEAN DEFAULT 0 | 1 if this record represents idle time |
| `project_tag` | TEXT | Optional user tag (nullable) |

### Table: `settings`
| Column | Type | Description |
|--------|------|-------------|
| `key` | TEXT PRIMARY KEY | e.g., 'idle_threshold', 'theme' |
| `value` | TEXT | JSON or string value |

## 6. UI Implementation Guidelines (NiceGUI)

**CRITICAL:** All UI code must strictly follow the **NiceGUI Advanced LLM Instruction Guide**. Do not use standard web patterns (React/Vue vanilla).

### 6.1 Layout & Structure
- Use **declarative UI** with `with` context managers (`with ui.column():`, `with ui.card():`).
- Use `ui.row()` and `ui.column()` for layout alignment.
- Use `ui.card()` for grouping timeline blocks or stats.
- **Navigation:** Use `ui.navigate.to('/path')` for page changes. Do not use `window.location`.

### 6.2 Styling
- **No raw CSS files.** Use Tailwind/Quasar via NiceGUI methods:
  - `.classes('w-full bg-blue-500 shadow-lg')` for Tailwind/Quasar classes.
  - `.props('outline dense icon="add"')` for Quasar properties.
  - `.style('color: red;')` only for inline overrides.
- **Dark Mode:** Support dark mode via Quasar theming (`.classes('dark')`).

### 6.3 State Management
- **Server-Side State:** Variables live on the server. Use `app.storage.user` for preferences (requires `storage_secret`).
- **Binding:** Use `.bind_value()`, `.bind_visibility_from()`, `.bind_text_to()` for syncing UI to Python variables.
- **Reactivity:** Use `@ui.refreshable` for sections that need re-rendering (e.g., the daily summary stats).
- **Signals:** Use `reaktiv` signals (`Signal()`, `Computed()`) for complex interdependent state if needed.

### 6.4 Components
- **Tables:** Use `ui.aggrid()` for the timeline data view (high performance).
  - Configure `columnDefs` and `rowData` in Python.
  - Use `await grid.get_selected_rows()` for interaction.
- **Dialogs:** Use `ui.dialog()` for confirmations or editing events.
  - Await dialog results: `result = await dialog`.
- **Charts:** Use `ui.echart()` or `ui.plotly()` for activity visualization if AG Grid is too tabular.
- **System Tray:** NiceGUI does not natively support system tray in all modes. 
  - *Fallback:* Use a small always-on-top window minimized to taskbar, or integrate `pystray` if native tray is required (run in separate thread).

### 6.5 Concurrency & Performance
- **Never Block:** Do not run tracking loops in the main UI thread.
- **Background Tasks:** Use `background_tasks.create(tracking_loop)` for the monitor.
- **IO Bound:** Use `run.io_bound()` for database writes or heavy file operations.
- **Timers:** Use `ui.timer(interval, callback)` for UI updates (e.g., updating a "Current App" label every second).

### 6.6 Testing
- Use `nicegui.testing.User` fixture for UI tests.
- Example:
  ```python
  async def test_dashboard(user: User):
      await user.open('/')
      user.find('Start Tracking').click()
      await user.should_see('Tracking Active')
  ```

## 7. App Lifecycle & Storage
- **Startup:** `app.on_startup(init_database)` to ensure DB exists.
- **Shutdown:** `app.on_shutdown(save_pending_events)` to ensure no data loss.
- **Storage:** Set `storage_secret` in `ui.run()` to enable `app.storage.user`.
- **Native Mode:** Run with `ui.run(native=True, window_size=(1024, 768))` to behave like a desktop app.

## 8. Privacy & Security Constraints
1. **Local-First:** No network requests for telemetry.
2. **Encryption:** Database file should be encrypted (use `sqlcipher` via Python wrapper if possible, otherwise rely on OS disk encryption).
3. **Transparency:** UI must clearly indicate when recording (e.g., Green/Red status indicator).
4. **Exclusions:** Allow users to add app names to an "Ignore List" (e.g., password managers).

## 9. Development Phases

### Phase 1: Core Tracker (Python CLI)
- Build Python script that logs foreground window to stdout every 5 seconds.
- Implement idle detection logic using `pynput`.
- Verify cross-platform compatibility (Win/Mac/Linux).

### Phase 2: Database & Persistence
- Integrate SQLite.
- Implement logic to save/load events.
- Create migration system.

### Phase 3: NiceGUI Interface
- Build Main Dashboard using `ui.column`, `ui.aggrid`, and `ui.card`.
- Connect frontend to backend logic via global state or database polling.
- Implement Settings Panel using `.bind_value()` for configuration.

### Phase 4: Polish & Packaging
- Implement `native=True` mode.
- Add `pystray` integration if possible for system tray.
- Build executable using `pyinstaller` or `auto-py-to-exe`.

## 10. Known Edge Cases to Handle
- **Multiple Monitors:** Track foreground window regardless of screen position.
- **Fullscreen Games:** Detect if window is fullscreen; still track if input received.
- **System Sleep:** Pause tracking on sleep event; resume on wake (do not log sleep time as idle).
- **Permissions:** macOS requires Accessibility permissions for input monitoring. App should detect and prompt user if missing.
```

hello

***

### How to Use This with Your AI Coding Tool

1.  **Save the File:** Copy the content above into a file named `PROJECT_SPEC.md` in your project root.
2.  **Start the AI Session:** Open your AI coding tool (Quencode/Qwen/Cursor).
3.  **The Initial Prompt:**
    > "I want to build the ActiveWindow Time Tracker described in `PROJECT_SPEC.md`. Please read the spec carefully, paying close attention to the **NiceGUI Implementation Guidelines** in Section 6. Start by scaffolding the Phase 1 Core Tracker in Python. Create the directory structure and a `main.py` that initializes NiceGUI in native mode and prints 'Hello' to verify the UI launches."
4.  **Iterate:**
    *   Once the UI launches, prompt: *"Proceed to Phase 1 Core Logic. Implement the foreground window tracking function using `pygetwindow` and run it in a `background_tasks.create` loop so it doesn't block the UI."*
    *   Then: *"Proceed to Phase 2. Set up the SQLite database according to the schema in Section 5. Ensure database writes happen via `run.io_bound` to avoid blocking."*
    *   Then: *"Proceed to Phase 3. Build the Dashboard UI using `ui.aggrid` for the timeline and `ui.card` for stats. Follow the styling rules in Section 6.2."*

### Why This Works Better for NiceGUI
*   **Concurrency Safety:** The spec explicitly tells the AI to use `background_tasks` and `run.io_bound`. Without t top his, AI often writes synchronous `while True` loops that freeze the NiceGUI interface.
*   **UI Consistency:** By embedding the "No raw CSS" and "Use `.props()`" rules, you prevent the AI from writing standard HTML/CSS that breaks NiceGUI's reactivity.
*   **State Management:** Explicitly defining `app.storage` usage ensures the AI doesn't try to use client-side localStorage for critical logic, which won't sync with the Python backend.

This single document now contains the **Product Logic** + **Technical Stack** + **UI Framework Rules**, making it a complete "brain" for your AI developer.
