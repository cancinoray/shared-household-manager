# Shared Household Manager

Household chore rotation tool. Django 5.1 + HTMX, server-rendered templates,
SQLite. See [`_docs/plan.md`](_docs/plan.md) for scope and
[`_docs/backlog.md`](_docs/backlog.md) for the task breakdown.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python manage.py migrate
python manage.py runserver
```

## Running tests

```bash
pytest
```

or with Django's built-in runner:

```bash
python manage.py test
```

Run the system check with `python manage.py check`.
