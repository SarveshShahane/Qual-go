# Qualgo Backend Service

> **AI-Based Interactive Quantum Algorithm Learning Platform**  

The `qualgo-backend` service provides the asynchronous REST API and backend infrastructure powering **Qualgo**. It handles secure user authentication, session management, database persistence via PostgreSQL and SQLAlchemy Async, and serves as the bridge to quantum simulation backends and AI tutoring services.

---

## Architecture & Tech Stack

- **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12, ASGI asynchronous execution)
- **Database & ORM:** [PostgreSQL](https://www.postgresql.org/) with [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/) and [`asyncpg`](https://github.com/MagicStack/asyncpg)
- **Database Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
- **Authentication & Security:**
  - JWT access tokens & refresh tokens with rotating credentials
  - Cross-site protection with `HttpOnly`, `SameSite=Lax`, and SSL/TLS secure cookie flags
  - Password hashing using `bcrypt`
- **Validation & Schemas:** [Pydantic v2](https://docs.pydantic.dev/) with `email-validator`
- **Quantum Simulation Engines (Integration Track):**
  - [Qiskit](https://qiskit.org/) & [Qiskit Aer](https://github.com/Qiskit/qiskit-aer) (statevector and shot simulation)
  - [Google Cirq](https://quantumai.google/cirq)
  - [Xanadu PennyLane](https://pennylane.ai/) (quantum machine learning and variational circuits)
  - [qBraid](https://qbraid.com/) SDK (cloud quantum device access)

---

## Project Structure

```
qual-backend/
├── alembic/                    # Database migration scripts
│   ├── versions/               # Versioned migration files
│   └── env.py                  # Alembic environment and model metadata
├── app/
│   ├── app.py                  # FastAPI app entry point, lifespan, CORS & exceptions
│   ├── config/
│   │   └── config.py           # Centralized environment settings & configuration
│   ├── database/
│   │   ├── nosql/              # NoSQL cache & document handlers (future extension)
│   │   └── sql/
│   │       ├── db.py           # Async engine & sessionmaker definitions
│   │       └── models/         # SQLAlchemy declarative ORM models
│   ├── exceptions/
│   │   ├── auth.py             # Auth-specific domain exceptions & HTTP handlers
│   │   └── base_exception.py   # Base application exceptions & global handlers
│   ├── routes/
│   │   └── auth.py             # Authentication endpoints (register, login, refresh, me)
│   ├── schemas/
│   │   └── auth.py             # Pydantic request/response validation models
│   └── services/
│       └── auth.py             # Auth business logic (token generation, hashing, verification)
├── alembic.ini                 # Alembic configuration file
├── Dockerfile                  # Production container definition
├── requirements.txt            # Python dependencies
└── .env                        # Local environment variables
```

---

## Environment Configuration

Create a `.env` file in the `qual-backend` root with the following parameters:

```ini
# Database Configuration
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=qual_dev
DATABASE_USER=postgres
DATABASE_PASSWORD=your_secure_password

# Application Environment
ENVIRONMENT=development
COOKIE_SECURE=false

# JWT Authentication
JWT_SECRET_KEY=your_super_secret_jwt_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## Quickstart & Local Development

### 1. Prerequisites
- Python 3.12+
- PostgreSQL server (running locally or in a container)

### 2. Setup Virtual Environment
```bash
# Windows (PowerShell)
cd qual-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
cd qual-backend
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Database Migrations
```bash
alembic upgrade head
```

### 5. Launch the API Server
```bash
uvicorn app.app:app --reload --host 127.0.0.1 --port 8000
```
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative ReDoc UI: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 6. Run Unit Tests
```bash
python -m unittest discover -s tests -p "*test*.py"
```


---

## API Endpoints Reference

### Authentication (`/auth`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/auth/register` | Register a new user account with email & password | No |
| `POST` | `/auth/login` | Authenticate user, set `access_token` and `refresh_token` in HttpOnly cookies | No |
| `POST` | `/auth/refresh` | Issue a new access token using a valid refresh token cookie | Cookie |
| `POST` | `/auth/logout` | Invalidate refresh token in DB and clear authentication cookies | Cookie |
| `GET` | `/auth/me` | Fetch authenticated user profile data | Cookie / Bearer |

#### Sample Request: User Registration
```json
POST /auth/register
Content-Type: application/json

{
  "email": "student@egreenquanta.org",
  "password": "StrongPassword123!"
}
```

#### Sample Response: User Profile (`GET /auth/me`)
```json
{
  "id": "c1f7a01a-8c50-48e2-9be1-8b0123456789",
  "email": "student@egreenquanta.org",
  "is_active": true,
  "created_at": "2026-09-20T11:00:00Z"
}
```

---

## Quantum Simulation & AI Services Roadmap

The following service modules are architected for integration in upcoming milestones:

1. **`app/services/quantum_runner.py`**:
   - Executes OpenQASM 3.0 / Qiskit circuits on `qiskit_aer.AerSimulator`
   - Returns full statevector distributions, density matrices, and measurement shot histograms
   - Interfaces Cirq and PennyLane for differentiable parameter tuning
2. **`app/services/ai_copilot.py`**:
   - Analyzes user quantum circuits to detect non-unitary operations and gate overhead
   - Formulates step-by-step mathematical explanations tailored to learner skill level
3. **`app/routes/curriculum.py`**:
   - Progress telemetry, checkpoint scoring, and mastery quiz submission verification

