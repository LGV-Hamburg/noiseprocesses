# Copilot Instructions for `noiseprocesses`

## Project Overview
- **Purpose:** Python wrapper for the Java-based [NoiseModelling](https://noise-planet.org/noisemodelling.html) library, enabling environmental noise mapping workflows.
- **Architecture:**
  - **API Layer:** FastAPI/OGC Processes API (`app.py`) exposes noise calculation processes as web endpoints.
  - **Processing Layer:** Python classes wrap and orchestrate Java NoiseModelling via JNI/JPype, with process registration using decorators (see `@register_process`).
  - **Data Layer:** Integrates with spatial databases (PostGIS/H2GIS) and uses GeoJSON for spatial data exchange.
  - **Java Layer:** Java code and Groovy scripts (in `NoiseModelling/` and `wps_scripts/`) are built and invoked for core calculations.
  - **See:** `diagram.md` for mermaid diagrams and data flow.

## Key Developer Workflows
- **Environment:**
  - Python 3.12+, managed with Poetry (`pyproject.toml`).
  - Java 11+ required for NoiseModelling. Use `java_setup.sh` to configure Java tools.
  - Docker/Compose supported for local and production builds.
- **Build & Run:**
  - `make build-image` — Build Docker image (uses `docker-compose-build.yaml`).
  - `make run-local` — Start dev containers (uses `docker-compose-dev.yaml`).
  - `make check-java` & `make dist` — Build Java/Groovy components.
  - `poetry install` — Set up Python dependencies.
- **Testing & Linting:**
  - Run tests with `pytest` (see `pyproject.toml` for plugins).
  - Lint/format: `black`, `isort`, `mypy`, `ruff` (configured in `pyproject.toml`).
  - Pre-commit hooks: `pre-commit run --all-files`.
- **Docs:**
  - Built with Jupyter Book: `make build-docs` (see `docs/`).

## Project Conventions & Patterns
- **Process Registration:**
  - Register new processes using `@register_process` decorator and define a `process_description` class variable (see `app.py`, `examples/`).
- **Configuration:**
  - Use `.env` for environment variables (loaded in `Makefile`).
  - Python config in `noiseprocesses/config.py`.
- **Data Exchange:**
  - Use GeoJSON for spatial features; schemas defined in process descriptions.
- **External Integration:**
  - Java code in `NoiseModelling/` is built and invoked via JPype/JayDeBeApi.
  - Database access via SQLAlchemy, H2GIS/PostGIS.
- **Template Management:**
  - Project structure managed by Copier template (see `README.md`).

## Examples & References
- See `examples/` for process usage patterns.
- See `docs/content/developers/` for setup and command references.
- See `diagram.md` for architecture and data flow diagrams.

---
**When in doubt, check `Makefile`, `pyproject.toml`, and `README.md` for canonical workflows and conventions.**
