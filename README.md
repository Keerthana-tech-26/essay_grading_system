# Essay Grading with Feedback (Django)

This is a minimal, self-contained Django project that grades essays and generates feedback using simple NLP heuristics (no external APIs).

## Features
- Submit an essay (title + content).
- Automatic scoring based on:
  - Length/coverage (word count)
  - Clarity (average sentence length)
  - Vocabulary diversity (type-token ratio)
  - Readability proxy (Flesch-Kincaid-ish heuristic)
  - Passive voice/hedging detection (simple regex heuristics)
  - Common misspellings & repeated words (basic checks)
- Instant feedback report per essay with actionable suggestions.
- Stores essays and results in SQLite.
- Admin panel enabled.

## Quickstart

```bash
# 1) Create & activate a virtualenv (recommended)
python -m venv .venv
# Windows: .venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Migrate & run
python manage.py migrate
python manage.py createsuperuser 
python manage.py runserver
```

## Project Layout
- `manage.py` – Django entrypoint
- `project/` – Django project settings/urls
- `essays/` – The app with models, views, forms, grading utils, templates, and static assets
- `static/` – Static assets
- `staticfiles/` – Collected static files
- `templates/` – HTML templates
- `db.sqlite3` – SQLite database file
- `requirements.txt` – Python dependencies
- `README.md` – Documentation

## Notes
- This grading system uses simple heuristics and is intended for demos/class projects. 
- For production or higher accuracy, integrate robust NLP models or services.
