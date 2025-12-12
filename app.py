import json
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime, timedelta
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route('/schedule_json', methods=['POST'])
def schedule_json():
    school_arrival_time = request.form.get('school_arrival_time')
    work_meeting_time = request.form.get('work_meeting_time')
    selected_activities = request.form.getlist('activities')
    journey_stops = []
    stop_index = 0
    while True:
        location = request.form.get(f'stop_location_{stop_index}')
        if not location:
            break
        journey_stops.append({'location': location})
        stop_index += 1
    boy_morning = any(stop.get('location') == 'school' for stop in journey_stops)
    all_activities = load_activities()
    schedule = calculate_schedule(journey_stops, selected_activities, all_activities, boy_morning, school_arrival_time, work_meeting_time)
    return jsonify(schedule or {})

ACTIVITIES_DB = 'activities_db.json'
ROUTES_DB = 'routes_db.json'

# Database functions
def load_activities():
    if not os.path.exists(ACTIVITIES_DB):
        return []
    with open(ACTIVITIES_DB, 'r') as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                for idx, activity in enumerate(data):
                    if 'order' not in activity:
                        activity['order'] = idx
                data.sort(key=lambda x: x.get('order', 999))
                return data
            else:
                return []
        except Exception:
            return []

def save_activities(activities):
    with open(ACTIVITIES_DB, 'w') as f:
        json.dump(activities, f, indent=2)

def load_routes():
    if not os.path.exists(ROUTES_DB):
        return []
    with open(ROUTES_DB, 'r') as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_routes(routes):
    with open(ROUTES_DB, 'w') as f:
        json.dump(routes, f, indent=2)

def get_route(from_loc, to_loc):
    """Find a route between two locations"""
    routes = load_routes()
    for route in routes:
        if route['from'] == from_loc and route['to'] == to_loc:
            return route
    return None

def get_travel_minutes(from_loc, to_loc):
    """Get travel time including 10-min buffer for 'to work' routes"""
    route = get_route(from_loc, to_loc)
    if not route:
        return None
    minutes = route['minutes']
    if to_loc == 'work':
        minutes += 10  # 10-minute walk-in buffer
    return minutes

def get_available_destinations(from_loc):
    """Get all possible destinations from a location"""
    routes = load_routes()
    return [r for r in routes if r['from'] == from_loc]

# Routes
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Save form data
        session['school_arrival_time'] = request.form.get('school_arrival_time')
        session['work_meeting_time'] = request.form.get('work_meeting_time')
        session['selected_activities'] = request.form.getlist('activities')

        # Save journey stops (locations only, no times)
        journey_stops = []
        stop_index = 0
        while True:
            location = request.form.get(f'stop_location_{stop_index}')
            if not location:
                break
            journey_stops.append({'location': location})
            stop_index += 1
        session['journey_stops'] = journey_stops
    
    # Load activities and group by section
    all_activities = load_activities()
    selected_activities = session.get('selected_activities', [])
    
    # Add statistics to activities
    for activity in all_activities:
        if 'timing_history' in activity and activity['timing_history']:
            history = activity['timing_history']
            twins_times = [r['duration_minutes'] for r in history if r.get('twins_morning')]
            no_twins_times = [r['duration_minutes'] for r in history if not r.get('twins_morning')]
            
            activity['twins_avg'] = round(sum(twins_times) / len(twins_times), 1) if twins_times else None
            activity['no_twins_avg'] = round(sum(no_twins_times) / len(no_twins_times), 1) if no_twins_times else None
        else:
            activity['twins_avg'] = None
            activity['no_twins_avg'] = None
    
    # Group activities by section
    sections = {}
    for idx, activity in enumerate(all_activities):
        section = activity['section']
        if section not in sections:
            sections[section] = []
        sections[section].append({
            'idx': idx,
            'activity': activity,
            'selected': str(idx) in selected_activities
        })
    
    # Calculate journey times
    journey_stops = session.get('journey_stops', [])
    boy_morning = any(stop.get('location') == 'school' for stop in journey_stops)
    school_arrival_time = session.get('school_arrival_time', None)
    work_meeting_time = session.get('work_meeting_time', None)
    schedule = calculate_schedule(journey_stops, selected_activities, all_activities, boy_morning, school_arrival_time, work_meeting_time)

    # Get available routes for journey builder
    routes = load_routes()
    all_locations = sorted(list(set([r['from'] for r in routes] + [r['to'] for r in routes])))

    return render_template('home.html',
                         sections=sections,
                         schedule=schedule,
                         boy_morning=boy_morning,
                         school_arrival_time=school_arrival_time,
                         work_meeting_time=work_meeting_time,
                         journey_stops=journey_stops,
                         all_locations=all_locations,
                         routes=routes)

def calculate_schedule(journey_stops, selected_activities, all_activities, boy_morning, school_arrival_time, work_meeting_time):
    """Calculate the complete schedule based on selected stops and constraints."""
    if not journey_stops or len(journey_stops) == 0:
        return None

    stops_list = [s.get('location') for s in journey_stops]

    # Calculate home activity time and external variable bump
    home_time = 0
    external_bump = 0
    for idx_str in selected_activities:
        try:
            idx = int(idx_str)
            if idx < len(all_activities):
                activity = all_activities[idx]
                minutes = activity.get('minutes_no_twins', 0)
                if activity.get('section') == 'Daily External Variables':
                    external_bump += minutes
                else:
                    home_time += minutes
        except (ValueError, IndexError) as e:
            logger.warning(f"Invalid activity index: {idx_str}. Error: {e}")
            continue

    # Determine constraints
    constraints = []
    if boy_morning and school_arrival_time and 'school' in stops_list:
        try:
            datetime.strptime(school_arrival_time, '%H:%M')
            constraints.append(('school', school_arrival_time))
        except ValueError:
            logger.warning(f"Invalid school arrival time: {school_arrival_time}")
            return None
    if work_meeting_time and 'work' in stops_list:
        try:
            datetime.strptime(work_meeting_time, '%H:%M')
            constraints.append(('work', work_meeting_time))
        except ValueError:
            logger.warning(f"Invalid work meeting time: {work_meeting_time}")
            return None
    if not constraints:
        return None

    # For each constraint, calculate the required leave time from home
    def calc_leave_home_time(target_stop, arrival_time):
        # Work backwards from arrival_time at target_stop to home
        try:
            current_time = datetime.strptime(arrival_time, '%H:%M')
        except ValueError as e:
            logger.error(f"Failed to parse time {arrival_time}: {e}")
            return None, None
        # Do not shift the arrival time; apply external bump per transit leg instead
        timeline = []
        stops = [s['location'] for s in journey_stops]
        if target_stop not in stops:
            return None, None
        idx = stops.index(target_stop)
        # Build base leg durations from home to target_stop
        base_legs = []
        for i in range(0, idx):
            base_travel = get_travel_minutes(journey_stops[i]['location'], journey_stops[i+1]['location'])
            if base_travel is None:
                logger.warning(f"No route found: {journey_stops[i]['location']} -> {journey_stops[i+1]['location']}")
                return None, None
            base_legs.append(base_travel)
        # Distribute external bump proportionally across legs
        def distribute_bump(base_list, total):
            if not base_list or not total:
                return [0] * len(base_list)
            total_base = sum(base_list)
            # Initial proportional allocation
            alloc = [int((b / total_base) * total) for b in base_list]
            # Fix rounding to match total
            diff = total - sum(alloc)
            # Distribute remaining minutes by descending fractional part
            fracs = sorted(
                [(i, (base_list[i] / total_base) * total - alloc[i]) for i in range(len(base_list))],
                key=lambda x: x[1], reverse=True
            )
            for k in range(diff):
                alloc[fracs[k % len(base_list)][0]] += 1
            return alloc
        bump_per_leg = distribute_bump(base_legs, external_bump)
        # Go backwards from target_stop to home applying per-leg bumps
        for i in range(idx, 0, -1):
            base_travel = base_legs[i-1]
            add_bump = bump_per_leg[i-1] if bump_per_leg else 0
            travel_minutes = base_travel + add_bump
            current_time = current_time - timedelta(minutes=travel_minutes)
            route = get_route(journey_stops[i-1]['location'], journey_stops[i]['location'])
            timeline.insert(0, {
                'location': journey_stops[i-1]['location'],
                'time': current_time.strftime('%I:%M %p'),
                'label': f"Leave {journey_stops[i-1]['location'].title()}",
                'travel_info': f"{route['description']} ({travel_minutes} min)"
            })
        # Subtract home activities
        leave_home_time = current_time
        wake_time = leave_home_time - timedelta(minutes=home_time)
        timeline.insert(0, {
            'location': 'home',
            'time': wake_time.strftime('%I:%M %p'),
            'label': 'Wake Up',
            'travel_info': f"Get ready at home ({home_time} min)"
        })
        return wake_time, timeline

    # Calculate all required wake times, use the earliest
    wake_times = []
    timelines = []
    for stop, arr_time in constraints:
        wake, tl = calc_leave_home_time(stop, arr_time)
        if wake:
            wake_times.append((wake, stop, arr_time, tl))
    if not wake_times:
        return None
    # Earliest wake time
    wake_times.sort(key=lambda x: x[0])
    wake_time, main_stop, main_arrival, main_timeline = wake_times[0]

    # Now, build the full forward timeline from wake_time
    # Start fresh and build complete timeline for ALL stops
    timeline = []
    stops = [s['location'] for s in journey_stops]
    
    # Start at wake time at home
    current_time = wake_time
    timeline.append({
        'location': 'home',
        'time': current_time.strftime('%I:%M %p'),
        'label': 'Wake Up',
        'travel_info': f"Get ready at home ({home_time} min)"
    })
    
    # Add home time
    current_time = current_time + timedelta(minutes=home_time)
    
    # Go through ALL stops in order
    # Forward legs base durations and distributed bump across all legs
    base_forward = []
    for i in range(len(journey_stops)-1):
        base_travel = get_travel_minutes(journey_stops[i]['location'], journey_stops[i+1]['location'])
        if base_travel is None:
            logger.error(f"Cannot build timeline: missing route from {journey_stops[i]['location']} to {journey_stops[i+1]['location']}")
            return None
        base_forward.append(base_travel)
    forward_bump = []
    if external_bump:
        # Reuse proportional bump distribution helper
        def distribute_bump_forward(base_list, total):
            if not base_list or not total:
                return [0] * len(base_list)
            total_base = sum(base_list)
            alloc = [int((b / total_base) * total) for b in base_list]
            diff = total - sum(alloc)
            fracs = sorted(
                [(i, (base_list[i] / total_base) * total - alloc[i]) for i in range(len(base_list))],
                key=lambda x: x[1], reverse=True
            )
            for k in range(diff):
                alloc[fracs[k % len(base_list)][0]] += 1
            return alloc
        forward_bump = distribute_bump_forward(base_forward, external_bump)
    # Build forward timeline using distributed bumps
    for i in range(len(journey_stops)-1):
        route = get_route(journey_stops[i]['location'], journey_stops[i+1]['location'])
        add_bump = forward_bump[i] if forward_bump else 0
        travel_minutes = base_forward[i] + add_bump
        
        # Leave current stop
        timeline.append({
            'location': journey_stops[i]['location'],
            'time': current_time.strftime('%I:%M %p'),
            'label': f"Leave {journey_stops[i]['location'].title()}",
            'travel_info': f"{route['description']} ({travel_minutes} min)"
        })
        
        # Travel to next stop
        current_time = current_time + timedelta(minutes=travel_minutes)
        
        # Only show "Arrive at" for the final stop
        if i == len(journey_stops) - 2:  # Last iteration (final stop)
            timeline.append({
                'location': journey_stops[i+1]['location'],
                'time': current_time.strftime('%I:%M %p'),
                'label': f"Arrive at {journey_stops[i+1]['location'].title()}"
            })

    return {
        'timeline': timeline,
        'total_time': home_time,
        'home_time': home_time
    }

@app.route('/get_routes_from/<location>')
def get_routes_from(location):
    """API endpoint to get available routes from a location"""
    routes = get_available_destinations(location)
    return jsonify(routes)

@app.route('/add_activity', methods=['GET', 'POST'])
def add_activity():
    if request.method == 'POST':
        try:
            activities = load_activities()
            name = request.form.get('name', '').strip()
            if not name:
                logger.warning("Activity name is required")
                return render_template('edit_activity.html', activity={}, idx=None, add_mode=True, error="Activity name is required")
            
            new_activity = {
                'section': request.form.get('section', ''),
                'name': name,
                'minutes_twins': int(request.form.get('minutes_twins', 0)),
                'minutes_no_twins': int(request.form.get('minutes_no_twins', 0)),
                'location': request.form.get('location', ''),
                'note': request.form.get('note', '')
            }
            activities.append(new_activity)
            save_activities(activities)
            logger.info(f"Added activity: {new_activity['name']}")
            return redirect(url_for('home'))
        except (ValueError, KeyError) as e:
            logger.error(f"Error adding activity: {e}")
            return render_template('edit_activity.html', activity={}, idx=None, add_mode=True, error="Invalid form data")
    return render_template('edit_activity.html', activity={}, idx=None, add_mode=True)

@app.route('/remove_activity/<int:idx>', methods=['POST'])
def remove_activity(idx):
    activities = load_activities()
    if 0 <= idx < len(activities):
        activities.pop(idx)
        save_activities(activities)
    return redirect(url_for('home'))

@app.route('/edit_activity/<int:idx>', methods=['GET', 'POST'])
def edit_activity(idx):
    activities = load_activities()
    if idx >= len(activities):
        return redirect(url_for('home'))
    activity = activities[idx]
    if request.method == 'POST':
        activity['name'] = request.form['name']
        activity['minutes_twins'] = int(request.form['minutes_twins'])
        activity['minutes_no_twins'] = int(request.form['minutes_no_twins'])
        activity['location'] = request.form['location']
        activity['note'] = request.form['note']
        activity['section'] = request.form['section']
        activities[idx] = activity
        save_activities(activities)
        return redirect(url_for('home'))
    return render_template('edit_activity.html', activity=activity, idx=idx)

@app.route('/manage_routes')
def manage_routes():
    routes = load_routes()
    return render_template('manage_routes.html', routes=routes)

@app.route('/add_route', methods=['GET', 'POST'])
def add_route():
    if request.method == 'POST':
        try:
            routes = load_routes()
            from_loc = request.form.get('from', '').strip()
            to_loc = request.form.get('to', '').strip()
            minutes = int(request.form.get('minutes', 0))
            
            if not from_loc or not to_loc:
                logger.warning("Route locations required")
                return redirect(url_for('manage_routes'))
            if minutes <= 0:
                logger.warning("Route minutes must be positive")
                return redirect(url_for('manage_routes'))
            
            new_route = {
                'from': from_loc,
                'to': to_loc,
                'minutes': minutes,
                'description': request.form.get('description', '')
            }
            routes.append(new_route)
            save_routes(routes)
            logger.info(f"Added route: {new_route['from']} -> {new_route['to']}")
            return redirect(url_for('manage_routes'))
        except (ValueError, KeyError) as e:
            logger.error(f"Error adding route: {e}")
            return redirect(url_for('manage_routes'))
    
    # Get all unique locations
    routes = load_routes()
    locations = sorted(list(set([r['from'] for r in routes] + [r['to'] for r in routes])))
    return render_template('edit_route.html', route={}, idx=None, add_mode=True, locations=locations)

@app.route('/edit_route/<int:idx>', methods=['GET', 'POST'])
def edit_route(idx):
    routes = load_routes()
    if idx >= len(routes):
        return redirect(url_for('manage_routes'))
    
    route = routes[idx]
    
    if request.method == 'POST':
        route['from'] = request.form['from']
        route['to'] = request.form['to']
        route['minutes'] = int(request.form['minutes'])
        route['description'] = request.form['description']
        routes[idx] = route
        save_routes(routes)
        return redirect(url_for('manage_routes'))
    
    locations = sorted(list(set([r['from'] for r in routes] + [r['to'] for r in routes])))
    return render_template('edit_route.html', route=route, idx=idx, locations=locations)

@app.route('/remove_route/<int:idx>', methods=['POST'])
def remove_route(idx):
    routes = load_routes()
    if 0 <= idx < len(routes):
        routes.pop(idx)
        save_routes(routes)
    return redirect(url_for('manage_routes'))

@app.route('/timer', methods=['GET'])
def timer():
    activities = load_activities()
    twins_morning = request.args.get('twins', 'false') == 'true'
    
    sections = {}
    for activity in activities:
        section = activity['section']
        if section not in sections:
            sections[section] = []
        sections[section].append(activity)
    
    return render_template('timer.html', sections=sections, twins_morning=twins_morning)

@app.route('/save_timing', methods=['POST'])
def save_timing():
    activity_name = request.form.get('activity_name')
    duration_seconds = int(request.form.get('duration_seconds', 0))
    twins_morning = request.form.get('twins_morning') == 'true'
    
    activities = load_activities()
    
    for activity in activities:
        if activity['name'] == activity_name:
            if 'timing_history' not in activity:
                activity['timing_history'] = []
            
            activity['timing_history'].append({
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'duration_seconds': duration_seconds,
                'duration_minutes': round(duration_seconds / 60, 1),
                'twins_morning': twins_morning
            })
            
            activity['timing_history'] = activity['timing_history'][-50:]
            break
    
    save_activities(activities)
    return {'success': True, 'duration_minutes': round(duration_seconds / 60, 1)}

@app.route('/manage_activities')
def manage_activities():
    activities = load_activities()
    
    for activity in activities:
        if 'timing_history' in activity and activity['timing_history']:
            history = activity['timing_history']
            twins_times = [r['duration_minutes'] for r in history if r.get('twins_morning')]
            no_twins_times = [r['duration_minutes'] for r in history if not r.get('twins_morning')]
            
            activity['twins_avg'] = round(sum(twins_times) / len(twins_times), 1) if twins_times else None
            activity['no_twins_avg'] = round(sum(no_twins_times) / len(no_twins_times), 1) if no_twins_times else None
            activity['record_count'] = len(history)
        else:
            activity['twins_avg'] = None
            activity['no_twins_avg'] = None
            activity['record_count'] = 0
    
    return render_template('manage_activities.html', activities=activities)

@app.route('/history')
def history():
    activities = load_activities()
    
    activity_stats = []
    for activity in activities:
        if 'timing_history' in activity and activity['timing_history']:
            history = activity['timing_history']
            
            twins_times = [r['duration_minutes'] for r in history if r.get('twins_morning')]
            no_twins_times = [r['duration_minutes'] for r in history if not r.get('twins_morning')]
            
            stats = {
                'activity': activity,
                'total_records': len(history),
                'twins_avg': round(sum(twins_times) / len(twins_times), 1) if twins_times else None,
                'no_twins_avg': round(sum(no_twins_times) / len(no_twins_times), 1) if no_twins_times else None,
                'twins_estimate': activity.get('minutes_twins', 0),
                'no_twins_estimate': activity.get('minutes_no_twins', 0),
                'history': sorted(history, key=lambda x: x['date'], reverse=True)
            }
            
            if stats['twins_avg']:
                stats['twins_variance'] = round(stats['twins_avg'] - stats['twins_estimate'], 1)
            if stats['no_twins_avg']:
                stats['no_twins_variance'] = round(stats['no_twins_avg'] - stats['no_twins_estimate'], 1)
            
            activity_stats.append(stats)
    
    return render_template('history.html', activity_stats=activity_stats)

@app.route('/delete_timing/<activity_name>/<int:record_index>', methods=['POST'])
def delete_timing(activity_name, record_index):
    activities = load_activities()
    
    for activity in activities:
        if activity['name'] == activity_name:
            if 'timing_history' in activity and 0 <= record_index < len(activity['timing_history']):
                activity['timing_history'].pop(record_index)
                save_activities(activities)
                return {'success': True}
            return {'success': False, 'error': 'Record not found'}, 404
    
    return {'success': False, 'error': 'Activity not found'}, 404

@app.route('/reorder_activity', methods=['POST'])
def reorder_activity():
    data = request.get_json()
    dragged_idx = data.get('dragged_idx')
    target_idx = data.get('target_idx')
    
    activities = load_activities()
    
    if dragged_idx < 0 or dragged_idx >= len(activities) or target_idx < 0 or target_idx >= len(activities):
        return {'success': False, 'error': 'Invalid activity index'}, 400
    
    dragged = activities[dragged_idx]
    target = activities[target_idx]
    
    if dragged['section'] != target['section']:
        return {'success': False, 'error': 'Cannot move between sections'}, 400
    
    dragged_order = dragged['order']
    target_order = target['order']
    
    if dragged_order < target_order:
        for activity in activities:
            if activity['section'] == dragged['section']:
                if dragged_order < activity['order'] <= target_order:
                    activity['order'] -= 1
        dragged['order'] = target_order
    else:
        for activity in activities:
            if activity['section'] == dragged['section']:
                if target_order <= activity['order'] < dragged_order:
                    activity['order'] += 1
        dragged['order'] = target_order
    
    save_activities(activities)
    return {'success': True}

if __name__ == "__main__":
    app.run(debug=True)