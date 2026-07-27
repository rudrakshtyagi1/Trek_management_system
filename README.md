# Trekkers — Trekking Management Application

A Flask + Jinja2 + Bootstrap + SQLite web app for managing treks across
three roles: Admin, Trek Staff, and Users (Trekkers).

## Stack

- Flask (backend)
- Jinja2, HTML, CSS, Bootstrap 5 (frontend) — no other CSS framework
- SQLite via Flask-SQLAlchemy — tables created **programmatically**, never by hand
- Flask-Login for session/auth handling
- Chart.js — used only for the optional admin dashboard charts (not for
  any core requirement, per the "no JS for core requirements" rule)

## Project layout

```
trekking_app/
├── app.py              # app factory, blueprint registration, Flask-Login user_loader
├── config.py            # SQLite path + seed admin credentials
├── extensions.py        # db, login_manager instances (avoids circular imports)
├── models.py             # Admin, Staff, User, Trek, Booking, TrekReview
├── utils.py               # role_required decorator (blocks cross-role access)
├── seed.py                 # creates tables + seeds the one Admin account
├── auth/routes.py          # login (all 3 roles), register (staff/user only)
├── admin/routes.py         # trek CRUD, staff approval, user blacklist, search, chart API
├── staff/routes.py         # manage only their assigned treks
├── user/routes.py          # browse/search/filter, book, cancel, history, reviews, profile
├── templates/              # Jinja2 templates, organized by role
├── static/css/style.css    # custom theme (not default Bootstrap blue)
└── requirements.txt
```

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Creates the SQLite DB + tables programmatically, and seeds the admin account
python seed.py

# Run the app
python app.py
```

Visit `http://127.0.0.1:5000`.

**Seeded admin login:** username `admin`, password `admin123`
(change `ADMIN_USERNAME` / `ADMIN_PASSWORD` in `config.py` before you
submit if you want your own credentials — and re-run `seed.py` after
deleting `instance/trekking.db`).

## Business rules implemented

- Admin is pre-seeded, never self-registers
- Staff self-registers but is locked out of their dashboard until admin approval
- Only the trek's assigned staff member can manage it (enforced server-side,
  not just hidden in the UI — verified with a direct route-access test)
- Booking is blocked once a trek is full or not "Open" (overbooking prevention
  re-checks slot count immediately before commit)
- Marking a trek "Completed" rolls all its active bookings to "Completed" too,
  so trekking history stays accurate
- Full booking history is retained — cancelled bookings are marked
  "Cancelled", never deleted

## Still worth doing before submission

- Add your own name/roll number and AI/LLM declaration to the project report
- Walk through each blueprint yourself and be ready to modify it live —
  this is required for the viva, not optional
- Consider adding: Flask-WTF for CSRF protection + cleaner form validation,
  pagination on the treks/users tables, an ER diagram (draw this from
  `models.py`'s relationships for your report)
- Initialize this as a git repo early and commit incrementally — the
  instructions require a git history as proof of originality
