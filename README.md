# ثقة — Thiqa

> AI-powered seller trust verification for the Algerian digital economy.

Thiqa lets Algerian buyers instantly verify online sellers before paying. Paste a Facebook URL, Instagram URL, phone number, or username — get a trust score, a community blacklist check, and an AI verdict in Darija.

---

---

## Tech Stack

| Layer    | Technology                                                 |
| -------- | ---------------------------------------------------------- |
| Frontend | React + Vite + CSS                                         |
| Backend  | FastAPI + SQLAlchemy + Alembic                             |
| Database | PostgreSQL                                                 |
| AI / NLP | AraBERT (fine-tuned) + Groq LLaMA + EasyOCR + EfficientNet |
| Storage  | Cloudinary (screenshots)                                   |
| LLM      | Groq — free at console.groq.com                            |

---

## Prerequisites

Install these before cloning:

- [Python 3.11+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- [PostgreSQL 15+](https://www.postgresql.org/download/)
- [Git](https://git-scm.com/)

---

## Clone the Repo

```bash
git clone https://github.com/YOURTEAM/thiqa.git
cd thiqa
git checkout dev
```

Create your feature branch immediately:

```bash
git checkout -b feature/your-name-your-feature
```

---

## Backend Setup

### 1. Create and activate the virtual environment

```bash
cd backend
python -m venv venv
```

**Windows:**

```bash
venv\Scripts\activate
```

**Mac / Linux:**

```bash
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal prompt. Every time you open a new terminal to work on the backend, run this activate command first.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your .env file

Copy the example and fill in real values:

```bash
# Windows
copy ..\env.example backend\.env

# Mac / Linux
cp ../env.example backend/.env
```

Open `backend/.env` and fill in:

```env
SECRET_KEY=any-long-random-string-you-make-up
DEBUG=True

DB_NAME=thiqa
DB_USER=thiqa_user
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432

GROQ_API_KEY=gsk_xxxxxx        # get free at console.groq.com
FACEBOOK_ACCESS_TOKEN=          # leave empty for now
CLOUDINARY_URL=                 # leave empty for now

FRONTEND_URL=http://localhost:5173
```

### 4. Set up PostgreSQL

Open pgAdmin (or psql if you have it in PATH) and run:

```sql
CREATE DATABASE thiqa;
CREATE USER thiqa_user WITH PASSWORD 'your_postgres_password';
GRANT ALL PRIVILEGES ON DATABASE thiqa TO thiqa_user;
```

Make sure `DB_PASSWORD` in your `.env` matches what you used above.

### 5. Run database migrations

```bash
cd backend
venv\Scripts\activate   # if not already active

alembic upgrade head
```

Open pgAdmin → your `thiqa` database → Schemas → public → Tables → Refresh.  
You should see 5 tables: `users`, `seller_profiles`, `seller_contacts`, `reports`, `reviews`.

### 6. Start the backend server

```bash
uvicorn app.main:app --reload --port 8000
```

Visit [http://localhost:8000/docs](http://localhost:8000/docs) — you should see the Swagger UI with all API routes listed.

---

## Frontend Setup

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Create your .env file

```bash
# Windows
copy nul .env

# Mac / Linux
touch .env
```

Open `frontend/.env` and add:

```env
VITE_API_URL=http://localhost:8000/api
```

### 3. Start the frontend

```bash
npm run dev
```

Visit [http://localhost:5173](http://localhost:5173) — stub pages should render.

---

## AI Setup

The AI code lives in `ai/` and runs inside the backend Python process.  
No separate server needed — the backend imports from `ai/` directly.

All AI packages are already included in `backend/requirements.txt`.  
If you need to run AI scripts or notebooks independently:

```bash
cd backend
venv\Scripts\activate   # reuse the backend venv
python -c "from ai import analyze_text; print(analyze_text('test'))"
```

This should print the stub dict without errors.

### Getting your Groq API key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up for free
3. Go to API Keys → Create API Key
4. Copy the key into `backend/.env` as `GROQ_API_KEY`

Free tier: 14,400 requests/day — more than enough.

---

## Sanity Check — All Three Should Run

Open three terminals and verify:

```bash
# Terminal 1 — AI
cd backend && venv\Scripts\activate
python -c "from ai import analyze_text; print(analyze_text('test'))"
# → should print stub dict ✅

# Terminal 2 — Backend
cd backend && venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs shows all routes ✅

# Terminal 3 — Frontend
cd frontend
npm run dev
# → http://localhost:5173 renders ✅
```

---

## Project Structure

```
thiqa/
├── .env.example              ← template — copy to backend/.env
├── .gitignore
├── README.md
│
├── ai/                       ← AI engineer's territory
│   ├── __init__.py           ← public interface (5 functions)
│   ├── text_analyzer/        ← AraBERT + Groq scam detection
│   ├── image_analyzer/       ← GAN fake image detector
│   ├── ocr/                  ← EasyOCR screenshot extractor
│   ├── sentiment/            ← AraBERT comment sentiment
│   ├── scoring/              ← trust score formula
│   ├── models/               ← saved model weights (gitignored)
│   ├── data/                 ← training data
│   ├── tests/                ← AI unit tests
│   └── requirements.txt      ← documentation only (use backend venv)
│
├── backend/                  ← backend engineer's territory
│   ├── .env                  ← gitignored — real values here
│   ├── venv/                 ← gitignored — activate this for all Python work
│   ├── alembic/              ← database migrations
│   ├── app/
│   │   ├── main.py           ← FastAPI app entry point
│   │   ├── config.py         ← reads .env variables
│   │   ├── db/               ← SQLAlchemy connection
│   │   ├── models/           ← ORM table definitions
│   │   ├── routes/           ← API endpoints
│   │   ├── schemas/          ← Pydantic request/response shapes
│   │   └── services/         ← business logic (FB API, Cloudinary, etc.)
│   └── requirements.txt
│
├── frontend/                 ← frontend engineer's territory
│   ├── .env                  ← gitignored — VITE_API_URL only
│   ├── node_modules/         ← gitignored
│   ├── src/
│   │   ├── api/thiqa.js      ← all API calls — import from here only
│   │   ├── pages/            ← one file per page
│   │   ├── components/       ← reusable UI components
│   │   └── App.jsx           ← routing
│   └── package.json
│
└── notebooks/                ← Colab fine-tuning notebooks
```

---

## API Endpoints (Quick Reference)

| Method | Path                       | Auth required |
| ------ | -------------------------- | ------------- |
| POST   | `/api/auth/register/`      | No            |
| POST   | `/api/auth/login/`         | No            |
| GET    | `/api/search/?q=`          | No            |
| POST   | `/api/analyze/text/`       | No            |
| POST   | `/api/analyze/screenshot/` | No            |
| POST   | `/api/analyze/image/`      | No            |
| POST   | `/api/reports/`            | Yes           |
| GET    | `/api/reports/?seller_id=` | No            |
| POST   | `/api/reviews/`            | Yes           |
| GET    | `/api/reviews/?seller_id=` | No            |
| GET    | `/api/blacklist/`          | No            |
| GET    | `/api/history/`            | Yes           |

Full request/response shapes: see `frontend/src/api/thiqa.js` and `backend/app/schemas/schemas.py`.

---

## Git Workflow

### Branches

```
main    → protected, final submission only
dev     → integration branch, merge here via PR
feature/ → your working branch, one per feature
```

### Daily routine

```bash
# morning — sync with latest dev
git checkout feature/your-feature
git pull origin dev

# commit often
git add .
git commit -m "feat(backend): reports endpoint real implementation"

# when feature is done — open PR into dev on GitHub
# after merge — create next feature branch
git checkout dev && git pull origin dev
git checkout -b feature/next-feature
```

### Commit message format

```
feat(scope):  new feature
stub(scope):  placeholder, not real yet
real(scope):  stub replaced with real implementation
fix(scope):   bug fix
docs:         documentation only

Scopes: ai | backend | frontend | db | config
```

### The one rule that prevents integration hell

> Never change a response shape without updating `frontend/src/api/thiqa.js` AND announcing in Discord before merging.

### Final submission (Day 10)

```bash
git checkout main
git merge dev
git tag v1.0.0-submission
git push origin main --tags
```

---

## Useful Links

- [Swagger UI (backend docs)](http://localhost:8000/docs) — only works when backend is running
- [Groq Console](https://console.groq.com) — free LLM API keys
- [Facebook Developer Portal](https://developers.facebook.com) — Graph API access token
- [Cloudinary](https://cloudinary.com) — free screenshot storage
- [pgAdmin](https://www.pgadmin.org) — database GUI
- [Alembic docs](https://alembic.sqlalchemy.org)