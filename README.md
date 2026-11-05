# Student Smart Hub

## Project Overview
Student Smart Hub is a web-based student management and study assistance application developed using Python and Django.

The main purpose of this project is to help students organize their study activities, manage notes, track daily goals and maintain previous year question papers (PYQs) in one place.

## Features

1. **User Authentication**
   - Student Registration
   - Login and Logout

2. **Student Dashboard**
   - Personalized Dashboard
   - Study Statistics
   - Progress Overview

3. **Profile Management**
   - View Profile
   - Update Student Details

4. **Notes Manager**
   - Add, Edit and Delete Notes
   - Search Notes
   - Mark Important Notes
   - Upload Attachments

5. **Study Planner**
   - Create and Manage Study Tasks
   - Set Task Priority
   - Track Task Completion

6. **Study Goals**
   - Set Daily Study Hour Targets
   - Set Daily Task Targets
   - Track Study Progress

7. **Study Streak Tracker**
   - Daily Study Check-in
   - Current Streak
   - Longest Streak

8. **PYQ Management**
   - Add, Edit and Delete Questions
   - Search and Filter Questions
   - Identify Repeated Questions
   - PYQ Analytics

9. **PDF Upload and Extraction**
   - Upload Previous Year Question Papers
   - Extract Text from PDF Files
   - Preview Extracted Questions

## Technologies Used

- Python
- Django
- MySQL
- HTML
- CSS
- Bootstrap
- JavaScript

## Installation and Setup

1. Clone or download the project.
2. Open the project folder in VS Code.
3. Create and activate a virtual environment.
4. Install the required Python packages.
5. Configure MySQL database settings.
6. Run database migrations.
7. Start the Django development server.

## Run Project

```bash
python manage.py migrate
python manage.py runserver
```

Open the following URL in your browser:

http://127.0.0.1:8000/

## Database

The project uses MySQL as its database management system.

Database backup file: `student_smart_hub_backup.sql`

## Project Purpose

This project is developed as an academic minor project to demonstrate web application development using Python and Django.

## Future Scope

- Improved PDF