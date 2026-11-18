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

## What's New in v3

**Look & feel**
- Modern gradient theme with glass sidebar, dark / light mode (remembers your choice), animated counters, toasts and confetti
- Dashboard with weekly study chart, subject doughnut, GitHub-style streak calendar, level card and exam countdown
- Installable as an app on phone / desktop (PWA) with an offline page

**Planning**
- Kanban board (drag & drop) · Monthly calendar of deadlines and exams · Weekly timetable
- Pomodoro Focus Timer that automatically fills today's goal, streak and XP
- Exam countdowns · Syllabus tracker with per-subject progress

**Learning**
- Notes: Markdown toolbar, tags, pin to top, folders by subject, PDF / Markdown export, print view
- Flashcards with flip-card study mode (generate from notes)
- Free local Study Assistant: note summaries, quizzes, exam-topic predictor (from your PYQ data) and note-grounded study help; no paid API or internet connection required
- Global search (Ctrl + K)

**Motivation**
- XP, levels, 10 badges, leaderboard and streak freezes

**Accounts & tools**
- Forgot-password by email · profile photo · optional "Continue with Google" · one-click demo account
- Excel / PDF export for tasks, PYQs and exams · daily deadline e-mail reminders

### Optional settings (environment variables)

| Variable | What it enables |
|---|---|
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | Real password-reset and reminder emails (otherwise printed to the log) |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (+ optional `GOOGLE_REDIRECT_URI`) | "Continue with Google" button. Redirect URI to register: `https://<your-site>/accounts/google/callback/` |
| `DEMO_MODE=True` | "Try the Demo Account" button on the login page |

### Useful commands

```bash
python manage.py migrate                 # apply the new database tables
python manage.py seed_demo               # create the demo account (add --reset to rebuild)
python manage.py send_reminders          # e-mail due tasks / upcoming exams (run daily, e.g. Render Cron Job)
python manage.py test hub                # run the automated tests
```

## Free local Study Assistant

The Study Assistant uses local text-processing and your saved notes/PYQ records. It does not call a paid AI provider, require an API key, or send study content to an external AI service. Summaries and quizzes are generated from supplied text; tutor answers are retrieved from matching saved notes. It is intentionally transparent when your notes do not contain an answer, rather than inventing facts.

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
5. Copy `.env.example` to `.env`. SQLite is used automatically for local development, so MySQL is not required.
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

Local development uses SQLite by default (`db.sqlite3`), so the project can run without installing a MySQL server or MySQL command-line client. To use MySQL, install the `mysqlclient` Python package and set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` in `.env`. For deployment, a `DATABASE_URL` can be supplied.

Database backup file: `student_smart_hub_backup.sql` (only if separately supplied).

## Project Purpose

This project is developed as an academic minor project to demonstrate web application development using Python and Django.

## Future Scope

- Improved PDF

## Gmail password-reset email setup

Password-reset emails use Gmail SMTP when both `EMAIL_HOST_USER` and
`EMAIL_HOST_PASSWORD` are configured in the project-root `.env` file.

1. Enable 2-Step Verification on the Gmail/Google account.
2. Create a Google App Password for this application.
3. Copy `.env.example` to `.env` and set `EMAIL_HOST_USER` to the Gmail address
   and `EMAIL_HOST_PASSWORD` to the 16-character App Password (remove spaces).
4. Keep `.env` private; never commit it to GitHub.
5. Restart Django and test the Forgot Password flow with a user account that
   has that same email address saved in its profile.
6. Check the Inbox and Spam folder. For local development, the reset link uses
   the local host/domain from the request. On deployment, configure the correct
   HTTPS domain and allowed hosts.

If Gmail credentials are not configured, Django deliberately falls back to
its console email backend and prints reset emails in the `runserver` terminal.

## PYQ PDF extraction and file retention

- Searchable PDFs are extracted using `pypdf`.
- Scanned/image-only PDFs can use OCR when PyMuPDF, `pytesseract`, and the
  Tesseract OCR system application are installed. Install Tesseract separately
  on Windows/macOS/Linux and make sure its executable is available on `PATH`.
- The original uploaded PDF is retained after questions are saved or individual
  questions are deleted.
- Use **Delete PDF** in **My Uploaded Files** to remove the original upload.
  Deleting that PDF does not delete the already-saved PYQ questions.
- OCR accuracy depends on scan quality, page orientation, language packs, and
  Tesseract configuration. Always review extracted questions before saving.

For local environment setup, copy `.env.example` to `.env`. SQLite works without
additional database setup. Fill in Gmail App Password settings only if you want
real email delivery; otherwise password-reset links are printed in the server terminal.
