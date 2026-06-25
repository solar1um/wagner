# Wagner — Project Context

## What This Is
Desktop application for editing Assetto Corsa Data (.acd) files. Built with Python + pywebview (native window) + Flask backend + HTML/CSS/JS frontend.

## Target
Windows portable .exe. Single-file, no install. Right-click on data.acd → "Edit with Wagner".

## Tech Stack
- Python 3.10+
- `acd` library (philippkosarev/acd) — reads/writes .acd files
- Flask — backend API
- pywebview — wraps HTML in native Windows window
- PyInstaller — builds single .exe
- HTML/CSS/JS — frontend (single file, no external deps)

## File Structure
```
wagner/
├── wagner/
│   ├── __init__.py          # from wagner.app import main
│   ├── app.py               # Entry point: pywebview window + Flask + shell registration
│   ├── backend.py           # 7 API endpoints for ACD operations
│   └── static/
│       └── index.html       # SPA: categories, cards, sliders, LUT editor, tooltips
├── build.py                 # PyInstaller build script
├── build.bat                # Windows one-click build
├── pyproject.toml           # Package metadata
├── README.md
└── .gitignore
```

## Backend API (backend.py)
All state held in memory.

- `POST /api/open` — {path: "..."} → opens .acd, returns {car_name, files[], info: {mass, limiter, power_peak}}
- `GET /api/file?name=...` — returns {name, content, changed, is_lut}
- `POST /api/edit` — {name, content} → overwrite entire file
- `POST /api/edit_param` — {name, param, value} → find param= in section, replace (section-aware via :: separator)
- `GET /api/summary` — car overview with change tracking
- `POST /api/save` — {action: "save"} → writes ACD to disk, auto-backup (.bak)
- `POST /api/diff` — {path: "other.acd"} → compare two ACDs (backend only, not in UI)
- `POST /api/undo` — reverts to last saved state
- `GET /api/state` — {path, opened, changed_count, diff_path}

## Frontend (index.html)
Dark theme, ~1100 lines, no CDN. Features:
- 10 categories: Overview, Engine, Drivetrain, Suspension, Tyres, Brakes, Aero, AI, Setup, All Files
- INI editor: cards with [SECTIONS], dropdowns for enums, sliders for ranged values, tooltips on hover
- LUT editor: editable table + draggable canvas chart (mouse-drag points)
- Engine power calculator: peak kW and Nm updated in real-time
- Clean UI: hides VERSION, HEADER, GRAPHICS, COAST_DATA, DAMAGE sections
- Change tracking: orange dots on categories, orange borders on modified inputs
- Drag & drop: drop data.acd onto window
- First-run modal: "Register right-click menu?"

## Build Process
On Windows:
```
1. Extract zip anywhere
2. Run build.bat
3. Gets dist\Wagner.exe (~15 MB, portable)
```

build.bat: creates .venv, pip installs acd/flask/pywebview/pyinstaller, runs build.py
build.py: PyInstaller --onefile --windowed --add-data static/ → wagner/static/

## ACD Format Notes
- .acd is a dict of {filename: content} stored with XOR encryption
- Key derived from file's basename (or parent dir basename if named "data.*")
- Moving/renaming an .acd can break decryption

## Key Decisions
- Shell register key: `Software\Classes\.acd\shell\wagner`
- AppData folder: `%APPDATA%\.wagner\first_run_done`
- Frozen static path: `sys._MEIPASS/wagner/static/`
- Section-aware params use `::` separator: `[TURBO_0]::LAG_DN`
- HIDDEN_PARAMS: VERSION, POWER_CURVE, COAST_CURVE, DY0, DY1, DX0, DX1, etc.
- HIDDEN_SECTIONS: [HEADER], [GRAPHICS], [COAST_DATA], [DAMAGE], etc.

## Dependencies
```
acd>=0.0.1 (from git+https://github.com/philippkosarev/acd.git)
flask>=3.0
pywebview>=6.0
pyinstaller>=6.0 (build only)
```

## Tested With
- Real ACD: faz_mercedes_w222_s650 (71 files, CSP extensions, multiple turbo stages)
- All 9 categories render correctly with real parameters
- Section-aware editing verified (TURBO_0 vs TURBO_1 independent)
- Comment stripping in values (; inline comments)
