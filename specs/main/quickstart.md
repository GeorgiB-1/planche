# Quickstart: Planche.bg — AI Interior Design MVP

**Date**: 2026-02-12

This guide walks you through setting up and running the Planche.bg platform locally.

---

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm/pnpm
- A Supabase account (free tier: https://supabase.com)
- A Cloudflare account with R2 enabled (free tier: https://dash.cloudflare.com)
- A Google AI Studio API key (free tier: https://aistudio.google.com)
- A Firecrawl API key (https://firecrawl.dev)

---

## 1. Environment Setup

Create a `.env` file in the `backend/` directory:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGci...your-service-role-key

# Cloudflare R2
CF_ACCOUNT_ID=your-cloudflare-account-id
R2_ACCESS_KEY=your-r2-access-key-id
R2_SECRET_KEY=your-r2-secret-access-key
R2_BUCKET=furniture-platform
R2_PUBLIC_URL=https://pub-xxx.r2.dev

# Google AI (Gemini)
GEMINI_API_KEY=your-gemini-api-key

# Firecrawl
FIRECRAWL_API_KEY=fc-your-firecrawl-key
```

---

## 2. Supabase Setup

1. Create a new Supabase project at https://supabase.com
2. Go to SQL Editor and run the schema from `specs/main/data-model.md` — specifically the `CREATE TABLE` and `CREATE INDEX` statements from the implementation plan
3. Note your project URL and service role key (Settings → API)

---

## 3. Cloudflare R2 Setup

1. Go to Cloudflare Dashboard → R2
2. Create a bucket named `furniture-platform`
3. Enable public access (Settings → Public Access → Allow)
4. Create an API token (R2 → Manage R2 API Tokens) with read/write permissions
5. Note the Account ID, Access Key ID, Secret Access Key, and public URL

---

## 4. Backend Setup

```bash
cd backend/
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate

pip install -r requirements.txt
```

### requirements.txt

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6
google-genai>=0.4.0
firecrawl-py>=1.0.0
supabase>=2.0.0
boto3>=1.28.0
pydantic>=2.0.0
python-dotenv>=1.0.0
httpx>=0.25.0
Pillow>=10.0.0
```

### Run the API server

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

---

## 5. Initial Data Population

### Run the scraper

```bash
# Scrape a single category from Videnov
python -m src.services.scraper "https://videnov.bg/mebeli/divani"

# Scrape all configured targets
python -m src.services.scraper --all
```

### Run vision enrichment

```bash
# Enrich all un-enriched products
python -m src.services.vision --all

# Enrich a specific product
python -m src.services.vision --product-id abc123
```

### Verify data

```bash
# Check database stats
curl http://localhost:8000/api/stats
```

Expected output:
```json
{
  "total_products": 523,
  "vision_enriched": 498,
  "usable_for_render": 412,
  "enrichment_pct": 95.2
}
```

---

## 6. Frontend Setup

```bash
cd frontend/
npm install
# or: pnpm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_R2_URL=https://pub-xxx.r2.dev
```

### Run the dev server

```bash
npm run dev
```

Frontend available at: http://localhost:3000

---

## 7. Test the Full Flow

1. Open http://localhost:3000
2. Upload a sketch (photo of a hand-drawn room plan)
3. Select:
   - Room type (if not auto-detected)
   - Budget tier: Стандартен (Standard)
   - Budget: €2000
   - Style: Modern
4. Click "Генерирай дизайн" (Generate Design)
5. Wait ~30-60 seconds
6. View the photorealistic render + product cards
7. Click "Купи" (Buy) on any product → opens source store page
8. Click "Замени" (Swap) → see alternatives → select → re-render

---

## 8. Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/analyze` | Upload sketch → get room analysis |
| POST | `/api/furnish` | Upload sketch + budget → get render + products |
| POST | `/api/swap` | Swap a product in existing design |
| GET | `/api/products/search` | Search/filter product database |
| GET | `/api/stats` | Database statistics |
| GET | `/api/tiers` | Budget tier definitions |

Full OpenAPI spec: `specs/main/contracts/api.yaml`

---

## 9. Deployment

### Backend (Hetzner VPS)

```bash
# On VPS
git clone <repo> && cd backend
pip install -r requirements.txt
# Copy .env with production credentials
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
# Use systemd or supervisor for process management
```

### Frontend (Cloudflare Pages)

1. Connect your repo to Cloudflare Pages
2. Build command: `cd frontend && npm run build`
3. Output directory: `frontend/.next`
4. Set environment variables in Cloudflare Pages dashboard

---

## 10. Troubleshooting

| Issue | Solution |
|-------|----------|
| Scraper returns 0 products | Check Firecrawl API key. Verify target URL is accessible. |
| Vision enrichment fails | Check Gemini API key. Verify R2 images are accessible. Check rate limits (1500/day free). |
| Render looks wrong | Check visual_description quality. Try adjusting the prompt in generator.py. |
| Products missing dimensions | Run vision enrichment — it estimates dimensions from images. |
| Bulgarian text garbled | Ensure UTF-8 encoding throughout. Supabase handles Cyrillic natively. |
| R2 images not loading | Check public access is enabled on the bucket. Verify R2_PUBLIC_URL. |
