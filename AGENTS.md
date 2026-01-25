# Repository Guidelines

## Project Structure & Module Organization
- `apps/`: Django apps (`core`, `account`, `contabilidade`, `nfse`). Business logic, models, views, and app-specific templates live here.
- `config/`: Django project configuration (settings, URLs, ASGI/WSGI).
- `templates/`: Global templates and shared layout components.
- `static/`: Frontend assets (`static/css`, `static/js`, `static/img`).
- `modules/`: Auxiliary modules (e.g., local chat integration).
- `logs/`: Rotating app logs (`debug.log`, `error.log`).
- `db.sqlite3`: Local development database.

## Build, Test, and Development Commands
Use standard Django commands from the repo root:
- `python manage.py runserver` — start the dev server (use `python manage.py runserver 8000` for a custom port).
- `python manage.py migrate` — apply database migrations.
- `python manage.py makemigrations` — create migrations after model changes.
- `python manage.py dbshell` — open a DB shell.
- `python manage.py shell < apps/core/tests/run_ai_tests.py` — run the AI test script.

## Coding Style & Naming Conventions
- Python/Django conventions: 4-space indentation, snake_case for modules/functions, PascalCase for classes/models.
- Keep app templates under `apps/<app>/templates/<app>/` and shared UI under `templates/`.
- No formatter or linter is enforced in-repo; follow existing patterns in the nearest file.

## Testing Guidelines
- Tests exist in `apps/**/tests.py` and `apps/core/tests/`. There is no formal test runner configuration beyond Django’s defaults.
- Prefer Django’s test runner: `python manage.py test`.
- Scripted tests live under `apps/core/script_test/` for manual/exploratory runs.

## Commit & Pull Request Guidelines
- Recent commit messages are short, lowercase, and in Portuguese (e.g., `melhorias`, `criado menu clientes tomadores`). Keep them concise and action-oriented.
- PRs should include: a brief summary, affected areas (apps/templates/static), and testing notes. Add screenshots or GIFs for UI/template changes.

## Configuration & Security
- Runtime settings are driven by `.env` (e.g., `OPENAI_API_KEY`, `REDIS_URL`, `DEBUG`).
- Redis is required for session storage; ensure it runs on `localhost:6379` during development.
