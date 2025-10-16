# Repository Guidelines

## Project Structure & Module Organization
The FastAPI entry point lives in `app/main.py`, with request routing declared in `app/api.py` and service wiring in `app/config.py`. Shared orchestration layers sit under `app/core/`, where document models, plugin interfaces, and the LLM client are defined. Domain-specific behavior is split into `app/plugins/` for processing strategies and `app/templates/` for prompt assets, while `app/pdf.py` handles ingestion. Tests reside in `tests/` for reusable fixtures and in the root-level `test_*.py` scripts that exercise full document flows; supporting assets are stored in `test_data/`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` creates and activates an isolated environment (Windows users should adapt the activate path).
- `pip install -r requirements.txt` installs the FastAPI, Pydantic, and Azure OpenAI dependencies expected by the service.
- `uvicorn app.main:app --reload` starts the API locally with hot reload at `http://localhost:8000`.
- `python -m pytest tests test_*.py` runs the unit and integration suites; add `-k` to target a single scenario.
- `make build` produces the Podman image defined in the `Dockerfile` when containerization is required.

## Coding Style & Naming Conventions
Use standard Python formatting with four-space indentation, type hints, and module-level docstrings that describe intent. Module and file names follow `snake_case`, classes use `PascalCase`, and async helpers or plugin IDs should remain descriptive (e.g., `informed_consent_plugin`). Keep configuration access centralized in `app/config.py` and prefer the shared logging utilities in `app/logger.py` over ad-hoc `print` calls.

## Testing Guidelines
The suite is `pytest`-based, and test files should follow the `test_<feature>.py` pattern mirrored by existing scripts such as `test_ki_summary.py`. Populate the `.env` file with Azure OpenAI credentials before invoking tests that touch the LLM client, otherwise they will fail fast. Store deterministic fixtures in `test_data/`, and when adding new integration runs, surface generated reports via the helper functions in `tests/test_utils.py` to keep JSON outputs reproducible.

## Commit & Pull Request Guidelines
Existing history favors short, imperative messages (e.g., `refactor: remove unused code`), so continue using lowercase summaries with an optional `type:` prefix. Reference related issues in the body, note any environment prerequisites, and attach sample outputs or screenshots when UI or API responses change. PRs should explain how to reproduce new behavior locally and call out any follow-up automation or documentation tasks.

## Environment & Secrets
Create a project root `.env` that supplies the Azure OpenAI base URL, key, version, and deployment names; the application and tests load it automatically via `python-dotenv`. Never commit secrets—use placeholders like `<your_OPENAI_API_KEY>` in shared snippets, and rotate credentials if accidental exposure occurs.
