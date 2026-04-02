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
