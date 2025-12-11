import json
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

ACTIVITIES_DB = 'activities_db.json'

# Database functions
def load_activities():
    if not os.path.exists(ACTIVITIES_DB):
        return []
    with open(ACTIVITIES_DB, 'r') as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                # Initialize order field if it doesn't exist and sort by order
                for idx, activity in enumerate(data):
                    if 'order' not in activity:
                        activity['order'] = idx
                # Sort by order field
                data.sort(key=lambda x: x.get('order', 999))
                return data
            else:
                return []
        except Exception:
            return []

def save_activities(activities):
    with open(ACTIVITIES_DB, 'w') as f:
        json.dump(activities, f, indent=2)

# Helper functions
def get_routine():
    return session.get('routine', [])

def get_weather():
    return session.get('weather', 'clear')

def get_selected():
    routine = get_routine()
    return [item for item in routine if item.get('selected', True)]

def weather_time(weather):
    if weather == 'rainy':
        return 5
    elif weather == 'snowy':
        return 15
    return 0

def get_leave_by():
    leave_by = session.get('leave_by')
    if leave_by:
        return datetime.strptime(leave_by, '%H:%M')
    meeting_at = session.get('meeting_at')
    if meeting_at:
        return datetime.strptime(meeting_at, '%H:%M')
    boys_school = session.get('boys_school')
    if boys_school == 'yes':
        return datetime.strptime('07:45', '%H:%M')
    return None

# Routes
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Save form data
        session['twins_morning'] = request.form.get('twins_morning') == 'yes'
        session['meeting_at'] = request.form.get('meeting_at')
        session['boys_school'] = request.form.get('boys_school') == 'yes'
        session['selected_activities'] = request.form.getlist('activities')
        
        # Calculate what time we need to arrive at work
        # Work backwards to determine leave time
        twins_morning = session.get('twins_morning')
        meeting_at = session.get('meeting_at')
        boys_school = session.get('boys_school')
        
        work_arrival_time = None
        if meeting_at:
            work_arrival_time = datetime.strptime(meeting_at, '%H:%M')
        
        # Determine when we need to leave home
        if twins_morning and boys_school:
            # Need to drop kids at school by 7:55, then drive to work
            # Two constraints: 
            # 1. Be at school by 7:55 (need to leave home 10 min before)
            # 2. Be at work for meeting (need to leave home 30 min before meeting)
            school_time = datetime.strptime('07:55', '%H:%M')
            leave_for_school = school_time - timedelta(minutes=10)
            
            if work_arrival_time:
                # Leave 30 min before work (10 to school + 20 school to work)
                leave_for_work = work_arrival_time - timedelta(minutes=30)
                # Take the earlier time
                earliest_leave = min(leave_for_school, leave_for_work)
            else:
                earliest_leave = leave_for_school
            
            session['leave_by_time'] = earliest_leave.strftime('%H:%M')
            session['arrive_at_work'] = work_arrival_time.strftime('%H:%M') if work_arrival_time else None
        elif work_arrival_time:
            # Just going to work (no school drop-off)
            # 20 minutes direct to work
            leave_for_work = work_arrival_time - timedelta(minutes=20)
            session['leave_by_time'] = leave_for_work.strftime('%H:%M')
            session['arrive_at_work'] = work_arrival_time.strftime('%H:%M')
        else:
            session['leave_by_time'] = None
            session['arrive_at_work'] = None
    
    # Load activities and group by section
    all_activities = load_activities()
    twins_morning = session.get('twins_morning', False)
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
    
    # Calculate times - separate HOME and TRANSIT activities
    home_time = 0
    additional_transit_time = 0
    
    # Add Knowns that are at home (not "Drive to work")
    for idx, activity in enumerate(all_activities):
        if activity['section'] == 'Knowns' and activity.get('location') != 'In Transit':
            if twins_morning:
                home_time += activity.get('minutes_twins', 0)
            else:
                home_time += activity.get('minutes_no_twins', 0)
    
    # Add selected activities - separate home vs transit
    for idx_str in selected_activities:
        idx = int(idx_str)
        if idx < len(all_activities):
            activity = all_activities[idx]
            # Don't double-count Knowns
            if activity['section'] != 'Knowns':
                minutes = activity.get('minutes_twins', 0) if twins_morning else activity.get('minutes_no_twins', 0)
                if activity.get('location') == 'In Transit':
                    additional_transit_time += minutes
                else:
                    home_time += minutes
    
    # Calculate wake-up and leave times
    wakeup_time = None
    leave_time = None
    arrive_time_str = None
    leave_by = session.get('leave_by_time')
    arrive_at = session.get('arrive_at_work')
    
    # Adjust leave time for additional transit time (weather conditions, etc.)
    if leave_by and additional_transit_time > 0:
        leave_dt = datetime.strptime(leave_by, '%H:%M')
        # Need to leave earlier to account for extra transit time
        leave_dt = leave_dt - timedelta(minutes=additional_transit_time)
        leave_by = leave_dt.strftime('%H:%M')
    
    if leave_by:
        # We know when to leave home (already calculated above)
        leave_dt = datetime.strptime(leave_by, '%H:%M')
        leave_time = leave_dt.strftime('%I:%M %p')
        
        # Wake-up time = leave time - home activity time
        wakeup_dt = leave_dt - timedelta(minutes=home_time)
        wakeup_time = wakeup_dt.strftime('%I:%M %p')
    
    if arrive_at:
        arrive_dt = datetime.strptime(arrive_at, '%H:%M')
        arrive_time_str = arrive_dt.strftime('%I:%M %p')
    
    total_time = home_time
    
    return render_template('home.html', 
                         sections=sections, 
                         twins_morning=twins_morning,
                         total_time=total_time,
                         home_time=home_time,
                         wakeup_time=wakeup_time,
                         leave_time=leave_time,
                         arrive_time=arrive_time_str,
                         meeting_at=session.get('meeting_at', ''),
                         boys_school=session.get('boys_school', False))

@app.route('/set_leave_by', methods=['POST'])
def set_leave_by():
    work_by = request.form.get('work_by')
    meeting_at = request.form.get('meeting_at')
    boys_school = request.form.get('boys_school')
    leave_times = []
    if work_by:
        t = datetime.strptime(work_by, '%H:%M')
        t = (t - timedelta(minutes=30)).time()
        leave_times.append(t)
        session['leave_by'] = t.strftime('%H:%M')
    if meeting_at:
        t = datetime.strptime(meeting_at, '%H:%M')
        t = (t - timedelta(minutes=30)).time()
        leave_times.append(t)
        session['meeting_at'] = t.strftime('%H:%M')
    if boys_school == 'yes':
        t = datetime.strptime('07:45', '%H:%M').time()
        leave_times.append(t)
        session['boys_school'] = 'yes'
    else:
        session['boys_school'] = 'no'
    if leave_times:
        earliest = min(leave_times)
        session['earliest_leave'] = earliest.strftime('%H:%M')
    return redirect(url_for('home'))

@app.route('/add_activity', methods=['GET', 'POST'])
def add_activity():
    if request.method == 'POST':
        activities = load_activities()
        new_activity = {
            'section': request.form['section'],
            'name': request.form['name'],
            'minutes_twins': int(request.form['minutes_twins']),
            'minutes_no_twins': int(request.form['minutes_no_twins']),
            'location': request.form['location'],
            'note': request.form['note']
        }
        activities.append(new_activity)
        save_activities(activities)
        return redirect(url_for('home'))
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

@app.route('/add_to_routine/<int:idx>', methods=['POST'])
def add_to_routine(idx):
    activities = load_activities()
    if 0 <= idx < len(activities):
        routine = session.get('routine', [])
        activity = activities[idx].copy()
        activity['selected'] = True
        routine.append(activity)
        session['routine'] = routine
    return redirect(url_for('home'))

@app.route('/remove_from_routine/<int:idx>', methods=['POST'])
def remove_from_routine(idx):
    routine = session.get('routine', [])
    if 0 <= idx < len(routine):
        routine.pop(idx)
        session['routine'] = routine
    return redirect(url_for('home'))

@app.route('/set_weather', methods=['POST'])
def set_weather():
    session['weather'] = request.form['weather']
    return redirect(url_for('home'))

@app.route('/update_routine', methods=['POST'])
def update_routine():
    routine = get_routine()
    selected = request.form.getlist('selected')
    for idx, item in enumerate(routine):
        item['selected'] = str(idx) in selected
    move = request.form.get('move')
    if move:
        direction, idx = move.split('-')
        idx = int(idx)
        if direction == 'up' and idx > 0:
            routine[idx-1], routine[idx] = routine[idx], routine[idx-1]
        elif direction == 'down' and idx < len(routine)-1:
            routine[idx+1], routine[idx] = routine[idx], routine[idx+1]
    session['routine'] = routine
    return redirect(url_for('home'))

@app.route('/save_routine', methods=['POST'])
def save_routine():
    routine = get_routine()
    with open('saved_routine.txt', 'w') as f:
        for item in routine:
            f.write(f"{item['name']},{item.get('minutes_twins', 0)},{item.get('selected', True)}\n")
    return redirect(url_for('home'))

@app.route('/start_timer', methods=['POST'])
def start_timer():
    session['current_idx'] = 0
    return redirect(url_for('timer'))

@app.route('/timer', methods=['GET'])
def timer():
    activities = load_activities()
    twins_morning = request.args.get('twins', 'false') == 'true'
    
    # Group by section
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
    
    # Find the activity and add timing record
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
            
            # Keep only last 50 records
            activity['timing_history'] = activity['timing_history'][-50:]
            break
    
    save_activities(activities)
    return {'success': True, 'duration_minutes': round(duration_seconds / 60, 1)}

@app.route('/manage_activities')
def manage_activities():
    activities = load_activities()
    
    # Add statistics to each activity
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
    
    # Calculate statistics for each activity
    activity_stats = []
    for activity in activities:
        if 'timing_history' in activity and activity['timing_history']:
            history = activity['timing_history']
            
            # Separate by context
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
            
            # Calculate variance from estimate
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
    
    # Only allow reordering within same section
    if dragged['section'] != target['section']:
        return {'success': False, 'error': 'Cannot move between sections'}, 400
    
    # Get dragged order and target order
    dragged_order = dragged['order']
    target_order = target['order']
    
    # If dragging down (to higher order)
    if dragged_order < target_order:
        # Shift all items between dragged and target down by 1
        for activity in activities:
            if activity['section'] == dragged['section']:
                if dragged_order < activity['order'] <= target_order:
                    activity['order'] -= 1
        dragged['order'] = target_order
    # If dragging up (to lower order)
    else:
        # Shift all items between target and dragged up by 1
        for activity in activities:
            if activity['section'] == dragged['section']:
                if target_order <= activity['order'] < dragged_order:
                    activity['order'] += 1
        dragged['order'] = target_order
    
    save_activities(activities)
    return {'success': True}

if __name__ == "__main__":
    app.run(debug=True)
