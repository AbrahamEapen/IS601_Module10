# IS601 Module 10 — User Authentication with SQLAlchemy & FastAPI

## Running Tests Locally

### Prerequisites

- Python 3.10+
- Docker (for the PostgreSQL database)
- A virtual environment with dependencies installed

### 1. Start the PostgreSQL container

```bash
docker run -d \
  --name test-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=fastapi_db \
  -p 5432:5432 \
  postgres:15
```

Or with Docker Compose (starts both the app and the database):

```bash
cd module10_is601
docker-compose up -d db
```

### 2. Set up the virtual environment

```bash
cd module10_is601
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate.bat    # Windows
pip install -r requirements.txt
```

### 3. Configure the database URL

```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fastapi_db
# Windows PowerShell: $env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/fastapi_db"
```

### 4. Run the tests

```bash
# All tests (unit + integration + e2e)
pytest

# Unit tests only (no database required for hashing/schema tests)
pytest tests/unit/ -v

# Integration tests only (requires Postgres)
pytest tests/integration/ -v

# A specific test file
pytest tests/unit/test_hashing.py -v

# With coverage report
pytest --cov=app --cov-report=term-missing

# Include slow tests
pytest --run-slow

# Keep the database between runs (skip truncation)
pytest --preserve-db
```

### Test layout

| Directory | What it covers |
|---|---|
| `tests/unit/test_calculator.py` | Calculator operations |
| `tests/unit/test_hashing.py` | `hash_password` / `verify_password` functions |
| `tests/unit/test_user_schemas.py` | `UserCreate` and `UserRead` Pydantic schemas |
| `tests/integration/test_user.py` | User CRUD, sessions, uniqueness via the ORM |
| `tests/integration/test_user_auth.py` | Registration, login, JWT token flow |
| `tests/integration/test_user_constraints.py` | Email/username uniqueness & invalid-email checks |
| `tests/integration/test_schema_base.py` | Schema validation edge cases |
| `tests/e2e/test_e2e.py` | Browser UI tests via Playwright |

