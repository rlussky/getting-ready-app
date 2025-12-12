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
./venv/Scripts/activate
pip install -r requirements.txt
```

2. Start the server:

```bash
python app.py
```

3. Open the app at http://127.0.0.1:5000

## Files

- `app.py`: Flask app, schedule calculation, activity stats, route management.
- `templates/home.html`: UI for journey stops, activities, sticky summary.
- `templates/manage_routes.html`, `templates/edit_route.html`: Route management UI.
- `templates/manage_activities.html`, `templates/edit_activity.html`: Activity management UI.
- `templates/timer.html`, `templates/history.html`: Timer and history views.
- `routes_db.json`, `activities_db.json`: Data stores for routes and activities.
- `requirements.txt`: Python dependencies.

## Reference: Start Time Calculator CSV

`Start Time Calculator(Sheet1).csv` lists activities, timings, and variables that inspired the app’s sections and default estimates.

---
"You dream it and I'll do my best to build it!"
