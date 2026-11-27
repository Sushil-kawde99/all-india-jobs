# JobDisha India 🇮🇳 (Python FastAPI + Turso Edition)

> **"Find Jobs. Build Your Career."**  
> Complete All-India Job Search & Career Platform built with **Python, FastAPI, Jinja2, Tailwind CSS**, and **Turso Cloud (libSQL)**.

---

## 🚀 1-Click Start (Windows)

Simply open PowerShell in this folder and run:

```powershell
cd c:\Users\Admin\Desktop\jobdisha-india-fastapi
python -m uvicorn main:app --reload
```
*(Or double-click on `run.bat`)*

Then open your browser to:
- **Public Portal:** [http://localhost:8000](http://localhost:8000)
- **Job Search & Filters:** [http://localhost:8000/jobs](http://localhost:8000/jobs)
- **Free ATS Resume Builder:** [http://localhost:8000/resume-builder](http://localhost:8000/resume-builder)
- **In-Hand Salary Calculator:** [http://localhost:8000/tools/in-hand-salary-calculator](http://localhost:8000/tools/in-hand-salary-calculator)
- **Admin Dashboard:** [http://localhost:8000/admin](http://localhost:8000/admin)

### Default Admin Login Credentials
- **Username:** `admin`
- **Password:** `Admin@JobDisha2026!`

---

## 🗄️ Connecting Your Turso Cloud Database (`my-portfolio-db`)

Your database URL is already configured in `.env`:
```env
TURSO_DATABASE_URL=libsql://my-portfolio-db-sushil-99.aws-ap-south-1.turso.io
```

### Just 2 Steps to Connect:
1. In your **Turso Cloud Dashboard** (as seen in your screenshot), click the **`+ Create Token`** button.
2. Open `.env` in this folder, and paste the token:
   ```env
   TURSO_AUTH_TOKEN=eyJhbGciOiJFZERT...
   ```

### Test Connection Anytime:
Run:
```powershell
python test_db.py
```
This script will test your cloud database connection and print your live vacancies!

---

## 🌟 Key Features Included

1. **Pan-India Geographic Coverage:** Filter jobs across all 28 States and 8 Union Territories.
2. **23 Career Categories:** Software, Data Entry, Back Office, Manufacturing, Banking, PSUs, Apprenticeships, and Remote.
3. **Free In-Browser ATS Resume Builder:** Real-time preview and 1-click A4 PDF print. Zero data uploaded to servers.
4. **Indian In-Hand Salary Calculator:** Computes monthly take-home from Annual CTC considering EPF, PT, and standard tax deductions.
5. **Saved Jobs:** Bookmarks vacancies in browser memory without requiring user login.
6. **Secure Admin Portal:** Add/edit jobs, toggle active/draft status, delete with confirmation, and CSV bulk import/export.
7. **SEO Ready:** Dynamic sitemap at `/sitemap.xml`, `/robots.txt`, and Google-compliant `JobPosting` structured schema.

