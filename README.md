# ثقة Thiqa

> **AI-Powered Seller Trust Verification Platform for the Algerian Digital Economy**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python)](https://www.python.org/)

Thiqa (ثقة — Arabic for _trust_) helps Algerian online buyers assess the trustworthiness of social media sellers before completing a purchase. Paste any Facebook, Instagram, or TikTok seller URL and get an instant AI-generated trust score with a verdict in Algerian Darija.

---

## ✨ Features

- 🔍 **Seller Trust Score (0–100)** — Multi-signal Gradient Boosting + rule-based blend
- 🗣️ **Arabic/Darija Sentiment Analysis** — Fine-tuned MARBERTv2 on Algerian e-commerce text
- 🖼️ **AI Image Detector** — Sightengine API + Groq LLaVA fallback
- 📸 **Screenshot OCR Pipeline** — EasyOCR extracts text from conversation screenshots
- 🤖 **Scam Text Analyzer** — LLaMA 3.3 70B via Groq with few-shot Algerian scam examples
- 📋 **Community Reports & Reviews** — Credibility-scored report system
- 🚫 **Blacklist** — Paginated, searchable blacklist of reported scammers
- 🔐 **JWT Authentication** — Stateless auth with bcrypt password hashing

---

## 🧠 AI Pipeline

```
User Input (URL / Text / Image)
        ↓
Platform Detection & Scraping (Apify)
        ↓
┌───────────────────────────────────────┐
│  EasyOCR  │ MARBERTv2 │ Sightengine  │
│ Screenshot│ Sentiment  │ AI Image Det │
└───────────────────────────────────────┘
        ↓
Gradient Boosting + Rule-Based Blend
        ↓
Trust Score (0–100) + Darija Verdict
```

### Trust Score Verdict Thresholds

| Score  | Color         | Label                 |
| ------ | ------------- | --------------------- |
| 80–100 | 🟢 Dark Green | Very Trustworthy      |
| 65–79  | 🟩 Green      | Generally Trustworthy |
| 50–64  | 🟨 Yellow     | Some Doubts           |
| 40–49  | 🟧 Orange     | Concerning Signs      |
| 0–39   | 🔴 Red        | Avoid                 |

---

## 🏗️ Tech Stack

| Layer     | Technology                                   |
| --------- | -------------------------------------------- |
| Frontend  | React 18 + Vite                              |
| Backend   | FastAPI + Uvicorn (Python 3.11+)             |
| Database  | PostgreSQL 15 + SQLAlchemy + Alembic         |
| LLM       | Groq API (LLaMA 3.3 70B)                     |
| Sentiment | MARBERTv2 (fine-tuned) + CAMeL BERT fallback |
| OCR       | EasyOCR (Arabic + English)                   |
| ML        | scikit-learn GradientBoostingClassifier      |
| Image AI  | Sightengine + Groq LLaVA fallback            |
| Scraping  | Apify (Facebook / Instagram / TikTok)        |
| Storage   | Cloudinary (report screenshots)              |
| Auth      | JWT (python-jose) + bcrypt                   |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15
- [Apify](https://apify.com) account (for scraping)
- [Groq](https://groq.com) API key (for LLM)

### 1. Clone the repository

```bash
git clone https://github.com/your-org/thiqa.git
cd thiqa
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate      # Windows
source venv/bin/activate     # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials (see Environment Variables below)

# Run database migrations
alembic upgrade head

# Start the backend
uvicorn app.main:app --reload
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the frontend
npm run dev
```

The app will be available at `http://localhost:5173`

---

## ⚙️ Environment Variables

Create a `backend/.env` file with the following:

```env
DATABASE_URL=postgresql://thiqa_user:your_password@localhost:5432/thiqa_db
SECRET_KEY=your_jwt_secret_key

APIFY_API_KEY=your_apify_token
GROQ_API_KEY=your_groq_api_key
SIGHTENGINE_API_USER=your_sightengine_user
SIGHTENGINE_API_SECRET=your_sightengine_secret
CLOUDINARY_URL=cloudinary://your_cloudinary_credentials
```

---

## 📡 API Endpoints

| Method | Path                        | Description                      | Auth |
| ------ | --------------------------- | -------------------------------- | ---- |
| POST   | `/api/auth/register/`       | User registration                | No   |
| POST   | `/api/auth/login/`          | JWT token issuance               | No   |
| GET    | `/api/search/?q=`           | Main seller lookup + trust score | No   |
| POST   | `/api/analyze/text/`        | Scam text analysis               | No   |
| POST   | `/api/analyze/screenshot/`  | OCR + scam analysis on images    | No   |
| POST   | `/api/reports/`             | Submit scam report               | Yes  |
| GET    | `/api/reports/?seller_url=` | List reports for a seller        | No   |
| POST   | `/api/reviews/`             | Submit buyer review              | Yes  |
| GET    | `/api/reviews/?seller_id=`  | List reviews for a seller        | No   |
| GET    | `/api/blacklist/`           | Paginated blacklist              | No   |
| GET    | `/api/history/`             | User search history              | Yes  |

Full interactive docs available at `http://localhost:8000/docs`

---

## 📊 Model Performance

### MARBERTv2 Sentiment Classifier

- **Test Accuracy:** 99.2% (375-sample held-out set)
- **F1 Macro:** 0.992
- **Training data:** 2,125 samples of Algerian e-commerce text (Arabic/Darija/French)

### Gradient Boosting Trust Scorer

- **CV F1-Weighted (5-fold):** ~0.87
- **Training samples:** 1,338 (1,296 synthetic + 42 real)
- **Top features:** `weighted_report_score`, `avg_credibility_score`, `avg_stars`, `account_age_days`

### Scam Text Analyzer (LLM Few-Shot)

- **Label Accuracy:** 100% (14/14 examples)
- **Scam Type Accuracy:** 100% (9/9 applicable)

---

## 👥 Team

| Role                       | Name          |
| -------------------------- | ------------- |
| AI + Backend Engineer      | Amal MESSAOUD |
| AI + Backend Engineer      | Amina MEDABIS |
| Design + Frontend Engineer | Zhour SACI    |

---

## 🏫 About

Built for the **I-ACE 2026 Competition** by the **Intellect Scientific Club** at M'Hamed Bougara University of Boumerdès (UMBB), April 2026.

---

## 📄 License

This project was developed for academic competition purposes. See individual dependency licenses in the technical report.
