# Getting Ready Timing Calculator Web App

## Overview

This project is inspired by a conversation about building a web app to help users plan and manage their morning routines, especially for those with ADHD or time blindness. The app aims to calculate the optimal time to start getting ready based on daily tasks, appointments, and variable conditions (like weather or travel time).

## Key Features

- **Personalized Questionnaires:** The app asks relevant questions (e.g., "Do you have a meeting? What time? Do you need to drop kids at school?") to gather daily requirements.
- **Dynamic Checklists:** Users can create and customize checklists for their morning routines, with each task assigned a time estimate.
- **Time Calculation:** The app adds up all required tasks and conditions (e.g., snowy weather adds extra travel time) to determine when the user needs to start getting ready.
- **Task Impact Suggestions:** If the calculated start time is very early, the app can suggest tasks to postpone (e.g., "Skipping shaving your legs saves 20 minutes").
- **Default and Custom Timings:** Includes default times for common activities (e.g., drive time, walk-in time) and allows users to input their own timings.
- **Timer and Checklist Integration:** Provides a step-by-step timer for each activity, similar to a workout timer, guiding users through their routine.
- **Pause and Adjust:** Users can pause the timer for unexpected events (e.g., bathroom breaks) and adjust timings as needed.
- **Activity Time Tracking:** Optionally, users can record actual times for activities (e.g., shower duration) to help the app learn and improve future estimates.
- **Printable or Simple Forms:** For broader accessibility, the app could offer printable checklists or forms for users to fill in based on their own time studies.

## Target Users

- Individuals with ADHD or time blindness
- Anyone looking to optimize their morning routine
- Users who benefit from structured checklists and time management tools

## Future Ideas

- Allow users to load their own timings and routines
- Build out a questionnaire or task builder for personalized routines
- Option to average or use max times from recorded activity durations
- Expand accessibility (e.g., printable forms, simple web interface)

## Limitations

- Web apps cannot provide push notifications, but timers and reminders are available within the app

## Getting Started

This README documents the initial concept. The next steps are to define the relevant questions, default activities, and time impacts, then build a simple prototype for home use. Feedback and adjustments will be incorporated as the project develops.

## Reference: Start Time Calculator CSV

The file `Start Time Calculator(Sheet1).csv` provides a detailed breakdown of activities, timing, and variables for morning routines. The app framework will incorporate these sections:

- **Schedule Inputs:**
	- First work meeting/event start time (dropdown in 5-minute increments)
	- Driving big twins to school (Y/N, must leave by 7:55 if yes)

- **Knowns (Transit):**
	- Drive to work (30 min, or 20 min if no twins)
	- Walking time from parking (10 min)

- **Daily External Variables:**
	- Weather conditions (light rain, heavy rain, emergency, etc.)
	- Injury/sickness (adds time)

- **Daily Minimum Activities:**
	- Get out of bed, use bathroom (15 min)
	- Set up pump supplies, change baby, pump/feed baby, etc.
	- Basic hygiene and prep (skincare, makeup, brush teeth, get dressed, gather supplies, load car)

- **Add Ons:**
	- Optional activities (retainer, outfit selection, shower, shave, hair care, makeup, meal prep, etc.)

Each activity has a time estimate, location, and notes. The app will allow users to select, order, and customize these activities, and will factor in external variables to calculate the optimal start time.

---
"You dream it and I'll do my best to build it!"
