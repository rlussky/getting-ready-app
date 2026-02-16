# Getting Ready Timing Calculator Web App

## Overview

A Flask web app that helps plan your morning by calculating when to wake up and leave, based on selected activities, transit routes, and constrained arrival times (school/work). Designed to support ADHD and time-blindness workflows with quick adjustments and clear timelines.

## Current Features

- **Journey Stops builder:** Drag-and-drop `School`, `Daycare`, and fixed `Home` with a muted handle. `Work` is always included and fixed as the last stop.
- **Inline constraints:** When `School` is checked, an “Arrive at school” dropdown appears. `Work` displays a “First work meeting” dropdown. These define fixed arrival targets the schedule works backward from.
- **Activities selection:** Organized into sections (Daily External Variables, Daily Minimum Activities, Add Ons). Checkbox selections drive the total “home time” before departure.
- **External variable bump (proportional):** Selected external variables add minutes to transit. The bump is distributed proportionally across each leg’s base duration. Constrained arrivals (school/work) do not shift; leave times adjust earlier.
- **Sticky summary timeline:** A compact, emoji-enhanced timeline stays at the top and refreshes live as you change options.
- **Full timeline details:** The results section shows the wake time, leaves, and final arrival, including route descriptions and leg durations.
- **Manage Activities & Routes:** CRUD screens to add/edit activities and define transit routes (from→to, minutes, description). Routes power travel calculations.
- **Timer & History:** Timer page for guided execution of activities, and History page for insights. Activity timing history is used to show averages alongside estimates.

## How It Works

1. **Select Journey Stops** in the Morning Options card.
   - `Home` is always first; `Work` is always included and last.
   - Check `School` or `Daycare` to include them; drag to reorder (except Home/Work which are fixed).
   - If `School` is checked, choose the arrival time; set your first `Work` meeting time.
2. **Choose Activities** under Today’s Activities.
   - Minimums default on; add optional items as needed.
   - External variables increase transit time proportionally across legs.
3. **Schedule Calculation** builds a backward plan to meet your latest constrained arrival, then a forward timeline including all legs and home prep.

## Data and Logic Notes

- **Routes:** Defined in `routes_db.json`. `get_travel_minutes()` adds a 10-minute walk-in buffer for legs arriving at `work`.
- **Constraints:** Added only when the corresponding stop is selected (school/work).
- **Proportional bump:** External minutes are split across segments based on their base durations; rounding is handled so the sum equals the total bump.
- **Wake time:** Determined by the earliest wake needed to satisfy all constraints.

## Running Locally

1. Create/activate a virtual environment and install requirements:

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac/Pi
# or: .\venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

2. (Recommended) Set a stable secret key so sessions survive restarts:

```bash
export SECRET_KEY="some-random-string-here"
```

3. Start the server:

```bash
python app.py
```

4. Open the app at http://<your-ip>:5000

## Deploying on a Raspberry Pi

1. Install Python 3 and pip if not already present:
   ```bash
   sudo apt update && sudo apt install python3 python3-venv python3-pip -y
   ```
2. Clone or copy the project to the Pi.
3. Create a venv and install dependencies:
   ```bash
   cd getting-ready-app
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Set a permanent secret key:
   ```bash
   echo 'export SECRET_KEY="$(python3 -c \"import secrets; print(secrets.token_hex(24))\")"' >> ~/.bashrc
   source ~/.bashrc
   ```
5. Run the app:
   ```bash
   python3 app.py
   ```
   Access from any device on the same network at `http://<pi-ip>:5000`.

6. (Optional) Auto-start on boot with a systemd service:
   ```bash
   sudo tee /etc/systemd/system/getting-ready.service > /dev/null <<EOF
   [Unit]
   Description=Getting Ready App
   After=network.target

   [Service]
   User=$USER
   WorkingDirectory=$(pwd)
   Environment=SECRET_KEY=$(echo $SECRET_KEY)
   ExecStart=$(pwd)/venv/bin/python app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   EOF

   sudo systemctl daemon-reload
   sudo systemctl enable getting-ready
   sudo systemctl start getting-ready
   ```

## Files

- `app.py`: Flask app, schedule calculation, activity stats, route management.
- `templates/home.html`: UI for journey stops, activities, sticky summary.
- `templates/manage_routes.html`, `templates/edit_route.html`: Route management UI.
- `templates/manage_activities.html`, `templates/edit_activity.html`: Activity management UI.
- `templates/history.html`: Timing history and insights view.
- `templates/settings.html`: App settings (work buffer, inline timer, per-stop config).
- `routes_db.json`, `activities_db.json`, `settings_db.json`: Data stores for routes, activities, and settings.
- `requirements.txt`: Python dependencies.

## Reference: Start Time Calculator CSV

`Start Time Calculator(Sheet1).csv` lists activities, timings, and variables that inspired the app’s sections and default estimates.

---
"You dream it and I'll do my best to build it!"

## Changelog

- UI: Home styling matches Work; Work fixed last and always checked; Daycare aligned with drag handle; School arrival dropdown appears only when School is checked.
- Logic: External variable minutes are distributed proportionally across transit legs; constrained arrivals (School/Work) remain fixed; `get_travel_minutes()` adds 10-min buffer for legs to Work.
- Docs: README refreshed with Journey Stops, constraints, proportional bump, sticky summary, management pages, and local run steps.
