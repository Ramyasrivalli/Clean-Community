# Clean Community – Sanitation & Hygiene Portal

A Flask and SQLite prototype for a Community Service Project (CSP). It gives residents an easy way to report local sanitation issues and gives administrators a small dashboard to manage them.

## Features

- Resident registration, login, logout, and editable profile
- Complaint reporting with optional image uploads
- Personal complaint history and status tracking
- Hygiene awareness and emergency contact pages
- Separate administrator login, statistics, filters, status updates, image viewing, and deletion
- Responsive, high-contrast interface designed for simple use on phones and computers

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this project folder.
3. Install the dependency:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the app:

   ```bash
   python app.py
   ```

5. Open `http://127.0.0.1:5000` in a browser.

The first run automatically creates `database.db` and `static/uploads/`.

## Administrator login (demo)

- Email: `admin@cleancommunity.local`
- Password: `admin123`

For a real deployment, set these environment variables before running the app:

```bash
set ADMIN_EMAIL=your-admin@example.com
set ADMIN_PASSWORD=a-strong-password
set SECRET_KEY=a-long-random-secret
```

On macOS/Linux, replace `set` with `export`.

## Project structure

```text
app.py                 Flask routes, authentication, and database logic
requirements.txt       Python dependency list
templates/             Reusable Jinja HTML templates
static/css/style.css   Responsive visual design
static/js/main.js      Small client-side helpers and validation
static/uploads/        Uploaded complaint photos (created automatically)
database.db            SQLite database (created automatically)
```

## Note for deployment

This is a college demonstration prototype. Before public deployment, set a strong `SECRET_KEY`, replace the demo administrator credentials, enable HTTPS, and use a production WSGI server.
