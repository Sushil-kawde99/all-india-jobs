import os
import atexit
import json
import time
import sqlite3
import re
import csv
import io
import math
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
import libsql_client
from config import TURSO_DATABASE_URL, TURSO_AUTH_TOKEN, ADMIN_USERNAME, ADMIN_CONTACT_NAME, ADMIN_CONTACT_PHONE

EXPIRED_GRACE_DAYS = 16
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR = os.path.join(BASE_DIR, "archive")
ARCHIVE_CSV_PATH = os.path.join(ARCHIVE_DIR, "expired_jobs_history.csv")
EXTENDED_LOG_PATH = os.path.join(ARCHIVE_DIR, "extended_jobs.json")

ARCHIVE_CSV_FIELDS = [
    "id", "slug", "title", "company", "city", "state", "category",
    "employment_type", "experience", "qualification", "salary_min",
    "salary_max", "posted_at", "last_date", "apply_url", "source_url",
    "archived_at", "archive_reason"
]

def parse_date_safe(date_str: Optional[str]) -> Optional[date]:
    if not date_str or not str(date_str).strip():
        return None
    s = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %B %Y", "%d %b %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def load_extended_map() -> Dict[str, Dict[str, str]]:
    if not os.path.exists(EXTENDED_LOG_PATH):
        return {}
    try:
        with open(EXTENDED_LOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def record_extension(job_id: int, old_date: Optional[str], new_date: str) -> None:
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    ext_map = load_extended_map()
    ext_map[str(job_id)] = {
        "old_date": old_date or "N/A",
        "new_date": new_date,
        "extended_on": datetime.now().strftime("%Y-%m-%d"),
    }
    try:
        with open(EXTENDED_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(ext_map, f, indent=2)
    except Exception as e:
        print(f"Extension log write notice: {e}")

def enrich_job_expiry(job: Dict[str, Any], ext_map: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, Any]:
    item = dict(job)
    today = datetime.now().date()
    parsed = parse_date_safe(item.get("last_date"))
    if ext_map is None:
        ext_map = load_extended_map()

    ext_info = ext_map.get(str(item.get("id")))
    is_expired = False
    days_expired = 0
    days_remaining = None
    purge_in_days = EXPIRED_GRACE_DAYS
    expiry_status = "open"

    if parsed:
        diff = (parsed - today).days
        if diff < 0:
            is_expired = True
            days_expired = abs(diff)
            purge_in_days = max(0, EXPIRED_GRACE_DAYS - days_expired)
            expiry_status = "purge_ready" if days_expired >= EXPIRED_GRACE_DAYS else "grace_expired"
        else:
            days_remaining = diff
            expiry_status = "expiring_soon" if diff <= 3 else "open"

    item["is_expired"] = is_expired
    item["days_expired"] = days_expired
    item["days_remaining"] = days_remaining
    item["purge_in_days"] = purge_in_days
    item["expiry_status"] = expiry_status
    item["is_extended"] = bool(ext_info and not is_expired)
    item["extended_from"] = ext_info.get("old_date") if ext_info else None
    return item

SEED_JOBS = [
    {
        "id": 1,
        "slug": "tcs-software-engineer-bengaluru-2026",
        "title": "Software Engineer - Full Stack (Java / React)",
        "company": "Tata Consultancy Services (TCS)",
        "city": "Bengaluru",
        "state": "Karnataka",
        "category": "IT / Software",
        "employment_type": "Full Time",
        "experience": "1-3 Years",
        "qualification": "B.E. / B.Tech / MCA",
        "salary_min": 450000,
        "salary_max": 750000,
        "description": "Tata Consultancy Services (TCS) is hiring Software Engineers for enterprise digital engineering programs. Key responsibilities include designing scalable RESTful microservices using Spring Boot, developing responsive frontend components in React, writing unit and integration tests, and collaborating across Agile squads.",
        "apply_url": "https://ibegin.tcs.com/iBegin/jobs/search",
        "source_url": "https://www.tcs.com/careers/india",
        "posted_at": "2026-11-20",
        "last_date": "2026-12-31",
        "verified_at": "2026-11-22",
        "is_active": 1,
    },
    {
        "id": 2,
        "slug": "infosys-systems-engineer-fresher-pune",
        "title": "Systems Engineer - Freshers Recruitment",
        "company": "Infosys Limited",
        "city": "Pune",
        "state": "Maharashtra",
        "category": "IT / Software",
        "employment_type": "Full Time",
        "experience": "Fresher",
        "qualification": "B.E. / B.Tech / M.E. / M.Tech / M.Sc / MCA",
        "salary_min": 360000,
        "salary_max": 420000,
        "description": "Infosys is conducting pan-India recruitment for fresh engineering graduates for the position of Systems Engineer. Selected candidates will undergo comprehensive foundational training at the Infosys Mysore campus on Python, Java, Cloud computing, and database management before deployment on live enterprise projects.",
        "apply_url": "https://career.infosys.com/joblist",
        "source_url": "https://www.infosys.com/careers.html",
        "posted_at": "2026-11-18",
        "last_date": "2026-12-25",
        "verified_at": "2026-11-21",
        "is_active": 1,
    },
    {
        "id": 3,
        "slug": "sbi-junior-associate-customer-support-mumbai",
        "title": "Junior Associate (Customer Support & Sales)",
        "company": "State Bank of India (SBI)",
        "city": "Mumbai",
        "state": "Maharashtra",
        "category": "Banking",
        "employment_type": "Full Time",
        "experience": "Fresher",
        "qualification": "Any Graduate",
        "salary_min": 320000,
        "salary_max": 450000,
        "description": "State Bank of India invites applications from eligible Indian citizens for recruitment of Junior Associates (Customer Support & Sales) in clerical cadre. Duties include handling customer accounts, cash transactions, processing deposits/withdrawals, KYC documentation, and assisting branch operations.",
        "apply_url": "https://bank.sbi/web/careers/current-openings",
        "source_url": "https://sbi.co.in/careers",
        "posted_at": "2026-11-15",
        "last_date": "2026-12-15",
        "verified_at": "2026-11-20",
        "is_active": 1,
    },
    {
        "id": 4,
        "slug": "rrb-technician-grade-iii-ahmedabad",
        "title": "Technician Grade III (Mechanical / Electrical)",
        "company": "Railway Recruitment Boards (RRB)",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "category": "Railway Jobs",
        "employment_type": "Government",
        "experience": "Fresher",
        "qualification": "10th Pass + ITI / Diploma in Engineering",
        "salary_min": 250000,
        "salary_max": 380000,
        "description": "Ministry of Railways (Government of India) announces recruitment for Technician Grade III under Pay Matrix Level 2 (7th CPC). The role entails maintenance, inspection, and servicing of locomotive components, signaling mechanisms, track equipment, and rolling stock.",
        "apply_url": "https://www.rrbahmedabad.gov.in",
        "source_url": "https://indianrailways.gov.in",
        "posted_at": "2026-11-10",
        "last_date": "2026-12-20",
        "verified_at": "2026-11-22",
        "is_active": 1,
    },
    {
        "id": 5,
        "slug": "drdo-scientist-b-recruitment-delhi",
        "title": "Scientist 'B' (Electronics / Computer Science)",
        "company": "Defence Research and Development Organisation (DRDO)",
        "city": "New Delhi",
        "state": "Delhi",
        "category": "Government Jobs",
        "employment_type": "Government",
        "experience": "Fresher",
        "qualification": "B.E. / B.Tech in Electronics / CS with valid GATE score",
        "salary_min": 750000,
        "salary_max": 1100000,
        "description": "DRDO Recruitment & Assessment Centre (RAC) invites applications for Scientist B in Level 10 of 7th CPC. Candidates will contribute to national defense technology research including radar systems, embedded firmware, cryptography, aerospace telemetry, and autonomous robotics.",
        "apply_url": "https://rac.gov.in",
        "source_url": "https://www.drdo.gov.in/careers",
        "posted_at": "2026-11-12",
        "last_date": "2026-12-18",
        "verified_at": "2026-11-21",
        "is_active": 1,
    },
    {
        "id": 6,
        "slug": "lt-graduate-engineer-trainee-chennai",
        "title": "Graduate Engineer Trainee (Civil & Structural)",
        "company": "Larsen & Toubro (L&T) Construction",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "category": "Manufacturing",
        "employment_type": "Full Time",
        "experience": "Fresher",
        "qualification": "B.E. / B.Tech in Civil Engineering",
        "salary_min": 480000,
        "salary_max": 600000,
        "description": "L&T Construction invites fresh engineering graduates for the Graduate Engineer Trainee (GET) batch. Selected engineers will participate in mega infrastructure projects, highway engineering, metro rail structures, site surveying, quality audits, and structural quantity estimation.",
        "apply_url": "https://www.lntecc.com/careers",
        "source_url": "https://www.larsentoubro.com/corporate/careers",
        "posted_at": "2026-11-14",
        "last_date": "2026-12-28",
        "verified_at": "2026-11-22",
        "is_active": 1,
    },
    {
        "id": 7,
        "slug": "tata-motors-production-engineer-sanand",
        "title": "Production Quality & Assembly Engineer",
        "company": "Tata Motors Passenger Vehicles Ltd",
        "city": "Sanand",
        "state": "Gujarat",
        "category": "Automobile",
        "employment_type": "Full Time",
        "experience": "1-3 Years",
        "qualification": "Diploma / B.E. Mechanical or Automobile Engineering",
        "salary_min": 350000,
        "salary_max": 520000,
        "description": "Tata Motors is recruiting Production Engineers for its Sanand EV manufacturing plant. Responsibilities include supervising battery pack assembly lines, conducting weld-spot inspections, optimizing cycle times, and adhering to World Class Manufacturing (WCM) standards.",
        "apply_url": "https://careers.tatamotors.com",
        "source_url": "https://www.tatamotors.com/careers",
        "posted_at": "2026-11-16",
        "last_date": "2026-12-22",
        "verified_at": "2026-11-21",
        "is_active": 1,
    },
    {
        "id": 8,
        "slug": "flipkart-supply-chain-associate-gurugram",
        "title": "Logistics Operations & Dispatch Supervisor",
        "company": "Flipkart India Private Limited",
        "city": "Gurugram",
        "state": "Haryana",
        "category": "Logistics",
        "employment_type": "Full Time",
        "experience": "1-3 Years",
        "qualification": "Any Graduate / 12th Pass",
        "salary_min": 240000,
        "salary_max": 360000,
        "description": "Flipkart Supply Chain team is hiring Logistics Supervisors for its mother hub facility in Bilaspur/Gurugram. Responsibilities include inbound inventory receiving, dispatch coordination, fleet tracking via WMS software, SLA monitoring, and warehouse floor team supervision.",
        "apply_url": "https://www.flipkartcareers.com",
        "source_url": "https://www.flipkartcareers.com",
        "posted_at": "2026-11-19",
        "last_date": "2026-12-30",
        "verified_at": "2026-11-23",
        "is_active": 1,
    },
    {
        "id": 9,
        "slug": "ongc-graduate-trainee-dehradun",
        "title": "Executive Trainee (Geology / Petroleum Engineering)",
        "company": "Oil and Natural Gas Corporation (ONGC)",
        "city": "Dehradun",
        "state": "Uttarakhand",
        "category": "PSU Jobs",
        "employment_type": "Government",
        "experience": "Fresher",
        "qualification": "Post Graduate in Geology / Geophysics or B.Tech Petroleum",
        "salary_min": 720000,
        "salary_max": 1200000,
        "description": "ONGC, a Maharatna PSU, recruits Graduate Trainees at E1 level through GATE scores. Positions involve exploration data analysis, well logging, seismic interpretation, reservoir management, and upstream hydrocarbon field monitoring.",
        "apply_url": "https://ongcindia.com/web/eng/career",
        "source_url": "https://ongcindia.com",
        "posted_at": "2026-11-11",
        "last_date": "2026-12-19",
        "verified_at": "2026-11-20",
        "is_active": 1,
    },
    {
        "id": 10,
        "slug": "apollo-hospitals-data-entry-operator-hyderabad",
        "title": "Medical Records & Data Entry Executive",
        "company": "Apollo Hospitals Enterprise Ltd",
        "city": "Hyderabad",
        "state": "Telangana",
        "category": "Data Entry",
        "employment_type": "Full Time",
        "experience": "0-1 Year",
        "qualification": "12th Pass / Any Graduate with Typing Certification",
        "salary_min": 190000,
        "salary_max": 270000,
        "description": "Apollo Hospitals Jubilee Hills is hiring Data Entry Executives for its Health Information Management Department. Responsibilities include digitizing patient case sheets, verifying insurance claim codes, entering diagnostic lab parameters, and maintaining electronic medical records (EMR) confidentiality.",
        "apply_url": "https://www.apollohospitals.com/careers",
        "source_url": "https://www.apollohospitals.com",
        "posted_at": "2026-11-17",
        "last_date": "2026-12-24",
        "verified_at": "2026-11-22",
        "is_active": 1,
    },
    {
        "id": 11,
        "slug": "remote-frontend-developer-react-fastapi",
        "title": "Frontend Engineer (React / TypeScript / Tailwind)",
        "company": "Innovaccer Analytics India",
        "city": "Noida",
        "state": "Uttar Pradesh",
        "category": "Remote Jobs",
        "employment_type": "Full Time",
        "experience": "1-3 Years",
        "qualification": "B.Tech / BCA / B.Sc in CS or relevant experience",
        "salary_min": 650000,
        "salary_max": 1000000,
        "description": "Innovaccer is hiring Frontend Developers for a 100% remote role across India. You will build user-friendly healthcare analytics dashboards, implement responsive designs with Tailwind CSS and React, write clean modular TypeScript code, and ensure 99.9% uptime for core clinical interfaces.",
        "apply_url": "https://innovaccer.com/careers",
        "source_url": "https://innovaccer.com",
        "posted_at": "2026-11-21",
        "last_date": "2027-01-15",
        "verified_at": "2026-11-23",
        "is_active": 1,
    },
    {
        "id": 12,
        "slug": "bhel-trade-apprentice-bhopal-2026",
        "title": "Trade Apprentice (Electrician / Fitter / Welder)",
        "company": "Bharat Heavy Electricals Limited (BHEL)",
        "city": "Bhopal",
        "state": "Madhya Pradesh",
        "category": "Apprenticeships",
        "employment_type": "Apprenticeship",
        "experience": "Fresher",
        "qualification": "10th Pass + ITI in relevant trade (NCVT)",
        "salary_min": 100000,
        "salary_max": 130000,
        "description": "BHEL Bhopal invites online applications from eligible ITI passed candidates for 1-year trade apprenticeship training under the Apprentices Act 1961. Candidates receive a monthly government-stipulated stipend and structured practical factory training.",
        "apply_url": "https://bpl.bhel.com/bplweb_new/careers/index.html",
        "source_url": "https://www.bhel.com/careers",
        "posted_at": "2026-11-13",
        "last_date": "2026-12-16",
        "verified_at": "2026-11-21",
        "is_active": 1,
    },
]

LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "jobdisha_local.db")

def init_local_db():
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'non-it',
        employment_type TEXT DEFAULT 'Full Time',
        experience TEXT DEFAULT 'Fresher',
        qualification TEXT,
        salary_min INTEGER,
        salary_max INTEGER,
        description TEXT NOT NULL,
        apply_url TEXT NOT NULL,
        source_url TEXT,
        posted_at TEXT,
        last_date TEXT,
        verified_at TEXT,
        is_active INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        company_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'company_admin',
        can_view_all_jobs INTEGER NOT NULL DEFAULT 0,
        can_add_jobs INTEGER NOT NULL DEFAULT 1,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS job_owners (
        job_id INTEGER PRIMARY KEY,
        owner_username TEXT NOT NULL,
        company_name TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS portal_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    conn.commit()

    # Seed if empty
    cursor.execute("SELECT COUNT(*) FROM jobs")
    if cursor.fetchone()[0] == 0:
        for j in SEED_JOBS:
            cursor.execute("""
            INSERT OR IGNORE INTO jobs (
                id, slug, title, company, city, state, category, employment_type,
                experience, qualification, salary_min, salary_max, description,
                apply_url, source_url, posted_at, last_date, verified_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                j["id"], j["slug"], j["title"], j["company"], j["city"], j["state"],
                j["category"], j["employment_type"], j["experience"], j["qualification"],
                j["salary_min"], j["salary_max"], j["description"], j["apply_url"],
                j["source_url"], j["posted_at"], j["last_date"], j["verified_at"], j["is_active"]
            ))
        conn.commit()
    conn.close()

init_local_db()

_turso_client = None

def close_turso_client():
    global _turso_client
    if _turso_client is not None:
        try:
            _turso_client.close()
        except Exception:
            pass
        _turso_client = None

atexit.register(close_turso_client)

def get_turso_client():
    global _turso_client
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN and len(TURSO_AUTH_TOKEN.strip()) > 20:
        try:
            if _turso_client is None:
                url = TURSO_DATABASE_URL
                if url.startswith("libsql://"):
                    url = url.replace("libsql://", "https://")
                _turso_client = libsql_client.create_client_sync(url=url, auth_token=TURSO_AUTH_TOKEN)
            return _turso_client
        except Exception as e:
            print(f"Turso client init error: {e}")
            return None
    return None

_SEEDED_ONCE = False
_TURSO_STATUS_CACHE: Dict[str, Any] = {"ok": None, "ts": 0.0}
_QUERY_CACHE: Dict[Tuple[str, Tuple[Any, ...]], Tuple[float, List[Dict[str, Any]]]] = {}
CACHE_TTL_SECONDS = 30.0

def invalidate_cache() -> None:
    _QUERY_CACHE.clear()

def ensure_aux_tables():
    client = get_turso_client()
    if not client:
        return
    try:
        client.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            company_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'company_admin',
            can_view_all_jobs INTEGER NOT NULL DEFAULT 0,
            can_add_jobs INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        client.execute("""
        CREATE TABLE IF NOT EXISTS job_owners (
            job_id INTEGER PRIMARY KEY,
            owner_username TEXT NOT NULL,
            company_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        client.execute("""
        CREATE TABLE IF NOT EXISTS portal_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)
    except Exception as e:
        print(f"Aux tables init note: {e}")

def seed_turso_if_empty():
    global _SEEDED_ONCE
    if _SEEDED_ONCE:
        return
    client = get_turso_client()
    if not client:
        return
    try:
        ensure_aux_tables()
        cnt = client.execute("SELECT COUNT(*) FROM jobs").rows[0][0]
        if cnt == 0:
            for j in SEED_JOBS:
                client.execute("""
                INSERT OR IGNORE INTO jobs (
                    id, slug, title, company, city, state, category, employment_type,
                    experience, qualification, salary_min, salary_max, description,
                    apply_url, source_url, posted_at, last_date, verified_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    j["id"], j["slug"], j["title"], j["company"], j["city"], j["state"],
                    j["category"], j["employment_type"], j["experience"], j["qualification"],
                    j["salary_min"], j["salary_max"], j["description"], j["apply_url"],
                    j["source_url"], j["posted_at"], j["last_date"], j["verified_at"], j["is_active"]
                ])
            invalidate_cache()
        _SEEDED_ONCE = True
    except Exception as e:
        print(f"Turso seeding note: {e}")

def is_turso_connected() -> bool:
    now = time.monotonic()
    if _TURSO_STATUS_CACHE["ok"] is not None and (now - _TURSO_STATUS_CACHE["ts"]) < 60.0:
        return bool(_TURSO_STATUS_CACHE["ok"])
    client = get_turso_client()
    if not client:
        _TURSO_STATUS_CACHE.update({"ok": False, "ts": now})
        return False
    try:
        res = client.execute("SELECT 1")
        if res and len(res.rows) > 0:
            seed_turso_if_empty()
            _TURSO_STATUS_CACHE.update({"ok": True, "ts": now})
            return True
        _TURSO_STATUS_CACHE.update({"ok": False, "ts": now})
        return False
    except Exception:
        _TURSO_STATUS_CACHE.update({"ok": False, "ts": now})
        return False

def execute_query(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    now = time.monotonic()
    key = (sql, tuple(params))
    cached = _QUERY_CACHE.get(key)
    if cached and (now - cached[0]) < CACHE_TTL_SECONDS:
        return [dict(r) for r in cached[1]]

    client = get_turso_client()
    if client:
        try:
            res = client.execute(sql, list(params))
            cols = res.columns
            rows = []
            for r in res.rows:
                rows.append(dict(zip(cols, r)))
            _QUERY_CACHE[key] = (now, rows)
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"Turso execute error: {e}. Falling back to local DB.")

    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    _QUERY_CACHE[key] = (now, rows)
    return [dict(r) for r in rows]

def execute_mutation(sql: str, params: tuple = ()) -> int:
    invalidate_cache()
    client = get_turso_client()
    if client:
        try:
            res = client.execute(sql, list(params))
            return res.last_insert_rowid if hasattr(res, 'last_insert_rowid') else 1
        except Exception as e:
            print(f"Turso mutation error: {e}. Falling back to local DB.")
            print(f"Turso mutation error: {e}. Falling back to local DB.")

    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(sql, params)
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def generate_slug(title: str, company: str) -> str:
    base = f"{title} {company}".lower()
    base = re.sub(r'[^\w\s-]', '', base).strip()
    base = re.sub(r'\s+', '-', base)[:70]
    import random
    suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=5))
    return f"{base}-{suffix}"

def get_jobs(
    q: str = "",
    state: str = "",
    city: str = "",
    category: str = "",
    experience: str = "",
    qualification: str = "",
    salary_range: str = "",
    employment_type: str = "",
    sort: str = "latest",
    page: int = 1,
    limit: int = 12,
    is_active: Optional[int] = 1
) -> Dict[str, Any]:
    conditions = []
    params = []

    if is_active is not None:
        conditions.append("is_active = ?")
        params.append(is_active)

    if q and q.strip():
        term = f"%{q.strip()}%"
        conditions.append("(title LIKE ? OR company LIKE ? OR description LIKE ? OR city LIKE ? OR state LIKE ?)")
        params.extend([term, term, term, term, term])

    if state and state != "All India" and state != "all":
        if state.lower() == "remote":
            conditions.append("(category LIKE ? OR city LIKE ? OR title LIKE ?)")
            params.extend(["%remote%", "%remote%", "%remote%"])
        else:
            conditions.append("LOWER(state) = LOWER(?)")
            params.append(state.strip())

    if city and city.strip():
        conditions.append("LOWER(city) = LOWER(?)")
        params.append(city.strip())

    if category and category != "all":
        cat = category.strip()
        conditions.append("(LOWER(category) LIKE LOWER(?) OR LOWER(title) LIKE LOWER(?))")
        params.extend([f"%{cat}%", f"%{cat}%"])

    if employment_type and employment_type != "all":
        conditions.append("LOWER(employment_type) = LOWER(?)")
        params.append(employment_type.strip())

    if experience and experience != "all":
        if "fresher" in experience.lower():
            conditions.append("(LOWER(experience) LIKE ? OR LOWER(experience) LIKE ?)")
            params.extend(["%fresher%", "%0%"])
        else:
            conditions.append("LOWER(experience) LIKE LOWER(?)")
            params.append(f"%{experience.strip()}%")

    if qualification and qualification != "all":
        conditions.append("LOWER(qualification) LIKE LOWER(?)")
        params.append(f"%{qualification.strip()}%")

    if salary_range and salary_range != "all":
        if salary_range == "below-15k":
            conditions.append("(salary_min < 180000 OR (salary_max IS NOT NULL AND salary_max < 180000))")
        elif salary_range == "15k-25k":
            conditions.append("(salary_min >= 180000 AND salary_min <= 300000)")
        elif salary_range == "25k-40k":
            conditions.append("(salary_min >= 300000 AND salary_min <= 480000)")
        elif salary_range == "40k-60k":
            conditions.append("(salary_min >= 480000 AND salary_min <= 720000)")
        elif salary_range == "60k-plus":
            conditions.append("(salary_max >= 720000 OR salary_min >= 720000)")
        elif salary_range == "not-disclosed":
            conditions.append("(salary_min IS NULL AND salary_max IS NULL)")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Sort
    order_by = "ORDER BY posted_at DESC, id DESC"
    if sort == "salary_high":
        order_by = "ORDER BY salary_max DESC, salary_min DESC"
    elif sort == "deadline":
        order_by = "ORDER BY last_date ASC"

    # Fetch matching rows and apply expiry grace rules cleanly
    data_sql = f"SELECT * FROM jobs {where_clause} {order_by}"
    raw_rows = execute_query(data_sql, tuple(params))

    ext_map = load_extended_map()
    enriched = [enrich_job_expiry(r, ext_map) for r in raw_rows]

    # Public routes (is_active == 1) hide jobs past the 15-18 day grace period
    if is_active == 1:
        enriched = [j for j in enriched if not j["is_expired"] or j["days_expired"] < EXPIRED_GRACE_DAYS]
        if sort in ("latest", "deadline"):
            # Show open/active jobs first, then grace-period expired jobs
            enriched.sort(key=lambda j: (1 if j["is_expired"] else 0))

    total = len(enriched)
    page = max(1, page)
    limit = max(1, min(100, limit))
    offset = (page - 1) * limit
    data = enriched[offset:offset + limit]

    total_pages = math.ceil(total / limit) if total > 0 else 1

    return {
        "data": data,
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": total_pages,
        "hasPrev": page > 1,
        "hasNext": page < total_pages,
    }

def get_job_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    rows = execute_query("SELECT * FROM jobs WHERE slug = ? LIMIT 1", (slug,))
    return enrich_job_expiry(rows[0]) if rows else None

def get_job_by_id(job_id: int) -> Optional[Dict[str, Any]]:
    rows = execute_query("SELECT * FROM jobs WHERE id = ? LIMIT 1", (job_id,))
    return enrich_job_expiry(rows[0]) if rows else None

def get_archived_jobs() -> List[Dict[str, Any]]:
    if not os.path.exists(ARCHIVE_CSV_PATH):
        return []
    try:
        with open(ARCHIVE_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            rows.reverse()
            return rows
    except Exception as e:
        print(f"Archive read note: {e}")
        return []

def archive_job_records(jobs_list: List[Dict[str, Any]], reason: str = f"Expired ({EXPIRED_GRACE_DAYS}+ Days)") -> int:
    if not jobs_list:
        return 0
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    existing_keys = set()
    file_exists = os.path.exists(ARCHIVE_CSV_PATH)
    if file_exists:
        try:
            with open(ARCHIVE_CSV_PATH, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    existing_keys.add((str(r.get("id", "")), str(r.get("slug", ""))))
        except Exception:
            pass

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    written = 0
    with open(ARCHIVE_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ARCHIVE_CSV_FIELDS)
        if not file_exists or os.path.getsize(ARCHIVE_CSV_PATH) == 0:
            writer.writeheader()
        for j in jobs_list:
            key = (str(j.get("id", "")), str(j.get("slug", "")))
            if key in existing_keys:
                continue
            row = {k: j.get(k, "") for k in ARCHIVE_CSV_FIELDS}
            row["archived_at"] = now_str
            row["archive_reason"] = reason
            writer.writerow(row)
            existing_keys.add(key)
            written += 1
    return written

def archive_and_purge_expired_jobs(grace_days: int = EXPIRED_GRACE_DAYS) -> Dict[str, Any]:
    all_rows = execute_query("SELECT * FROM jobs ORDER BY id ASC")
    ext_map = load_extended_map()
    to_purge = []
    for r in all_rows:
        item = enrich_job_expiry(r, ext_map)
        if item["is_expired"] and item["days_expired"] >= grace_days:
            to_purge.append(item)

    if not to_purge:
        return {"archived_and_deleted": 0, "purged_titles": []}

    archive_job_records(to_purge, reason=f"Expired ({grace_days}+ Days)")
    purged_titles = []
    for j in to_purge:
        execute_mutation("DELETE FROM jobs WHERE id = ?", (j["id"],))
        purged_titles.append(j["title"])

    return {"archived_and_deleted": len(to_purge), "purged_titles": purged_titles}

def extend_job_deadline(job_id: int, new_last_date: str) -> bool:
    existing = get_job_by_id(job_id)
    if not existing:
        return False
    old_date = existing.get("last_date") or ""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = now[:10]
    execute_mutation(
        "UPDATE jobs SET last_date = ?, is_active = 1, verified_at = ?, updated_at = ? WHERE id = ?",
        (new_last_date.strip(), today, now, job_id)
    )
    record_extension(job_id, old_date, new_last_date.strip())
    return True

def get_job_stats() -> Dict[str, int]:
    all_rows = execute_query("SELECT * FROM jobs")
    ext_map = load_extended_map()
    enriched = [enrich_job_expiry(r, ext_map) for r in all_rows]

    total = len(enriched)
    active_all = [j for j in enriched if j["is_active"] == 1]
    open_jobs = [j for j in active_all if not j["is_expired"]]
    expired_grace = [j for j in enriched if j["is_expired"] and j["days_expired"] < EXPIRED_GRACE_DAYS]
    purge_ready = [j for j in enriched if j["is_expired"] and j["days_expired"] >= EXPIRED_GRACE_DAYS]

    govt = sum(1 for j in open_jobs if any(k in (j.get("category") or "").lower() for k in ["govt", "government", "railway", "psu"]))
    it_cnt = sum(1 for j in open_jobs if any(k in (j.get("category") or "").lower() for k in ["it", "software", "development"]))
    fresher_cnt = sum(1 for j in open_jobs if "fresher" in (j.get("experience") or "").lower() or "0" in (j.get("experience") or "").lower())
    states_set = {j.get("state") for j in active_all if j.get("state")}
    archived_cnt = len(get_archived_jobs())

    return {
        "totalJobs": total,
        "activeJobs": len(open_jobs),
        "publishedTotal": len(active_all),
        "expiredGraceJobs": len(expired_grace),
        "purgeReadyJobs": len(purge_ready),
        "archivedHistoryCount": archived_cnt,
        "inactiveJobs": max(0, total - len(active_all)),
        "governmentJobs": govt,
        "itJobs": it_cnt,
        "privateJobs": max(0, len(open_jobs) - govt),
        "fresherJobs": fresher_cnt,
        "statesCovered": len(states_set),
    }

def create_job(data: Dict[str, Any]) -> int:
    slug = data.get("slug") or generate_slug(data["title"], data["company"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = now[:10]

    sql = """
    INSERT INTO jobs (
        slug, title, company, city, state, category, employment_type,
        experience, qualification, salary_min, salary_max, description,
        apply_url, source_url, posted_at, last_date, verified_at,
        is_active, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        slug,
        data["title"],
        data["company"],
        data["city"],
        data["state"],
        data.get("category", "non-it"),
        data.get("employment_type", "Full Time"),
        data.get("experience", "Fresher"),
        data.get("qualification"),
        data.get("salary_min"),
        data.get("salary_max"),
        data["description"],
        data["apply_url"],
        data.get("source_url"),
        data.get("posted_at") or today,
        data.get("last_date"),
        data.get("verified_at") or today,
        data.get("is_active", 1),
        now,
        now,
    )
    return execute_mutation(sql, params)

def update_job(job_id: int, data: Dict[str, Any]) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fields = []
    params = []
    allowed_keys = [
        "title", "company", "city", "state", "category", "employment_type",
        "experience", "qualification", "salary_min", "salary_max", "description",
        "apply_url", "source_url", "last_date", "is_active"
    ]
    for k in allowed_keys:
        if k in data and data[k] is not None:
            fields.append(f"{k} = ?")
            params.append(data[k])

    if fields:
        fields.append("updated_at = ?")
        params.append(now)
        params.append(job_id)
        sql = f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?"
        execute_mutation(sql, tuple(params))

def delete_job(job_id: int, archive_first: bool = True) -> None:
    if archive_first:
        job = get_job_by_id(job_id)
        if job:
            reason = f"Expired ({job['days_expired']}+ Days)" if job.get("is_expired") else "Deleted by Admin"
            archive_job_records([job], reason=reason)
    execute_mutation("DELETE FROM jobs WHERE id = ?", (job_id,))
    execute_mutation("DELETE FROM job_owners WHERE job_id = ?", (job_id,))

def toggle_job_active(job_id: int, current_status: int) -> None:
    new_status = 0 if current_status == 1 else 1
    execute_mutation("UPDATE jobs SET is_active = ? WHERE id = ?", (new_status, job_id))

def bulk_import_csv(csv_text: str) -> Dict[str, Any]:
    lines = [l for l in csv_text.splitlines() if l.strip()]
    if len(lines) < 2:
        return {"imported": 0, "skipped": 0, "errors": ["CSV file contains no data rows."]}

    reader = csv.DictReader(lines)
    imported = 0
    skipped = 0
    errors = []

    for idx, row in enumerate(reader, start=2):
        title = (row.get("title") or "").strip()
        company = (row.get("company") or "").strip()
        city = (row.get("city") or "").strip()
        state = (row.get("state") or "").strip()
        apply_url = (row.get("apply_url") or "").strip()
        description = (row.get("description") or "").strip()

        if not (title and company and city and state and apply_url and description):
            skipped += 1
            errors.append(f"Row {idx} skipped: Required fields missing.")
            continue

        slug = (row.get("slug") or "").strip() or generate_slug(title, company)

        # Duplicate check by slug or title+company+city
        existing = get_job_by_slug(slug)
        content_dup = execute_query(
            "SELECT id FROM jobs WHERE LOWER(title)=LOWER(?) AND LOWER(company)=LOWER(?) AND LOWER(city)=LOWER(?) LIMIT 1",
            (title, company, city)
        )

        if existing or content_dup:
            skipped += 1
            errors.append(f"Row {idx} skipped: Duplicate vacancy detected ({title} at {company}).")
            continue

        try:
            sal_min = int(row["salary_min"]) if row.get("salary_min") and row["salary_min"].strip() else None
            sal_max = int(row["salary_max"]) if row.get("salary_max") and row["salary_max"].strip() else None
            is_active = int(row["is_active"]) if row.get("is_active") and row["is_active"].strip() else 1

            create_job({
                "slug": slug,
                "title": title,
                "company": company,
                "city": city,
                "state": state,
                "category": row.get("category", "non-it"),
                "employment_type": row.get("employment_type", "Full Time"),
                "experience": row.get("experience", "Fresher"),
                "qualification": row.get("qualification"),
                "salary_min": sal_min,
                "salary_max": sal_max,
                "description": description,
                "apply_url": apply_url,
                "source_url": row.get("source_url"),
                "last_date": row.get("last_date"),
                "is_active": is_active,
            })
            imported += 1
        except Exception as e:
            skipped += 1
            errors.append(f"Row {idx} error: {str(e)}")

    return {"imported": imported, "skipped": skipped, "errors": errors}

def export_all_jobs_csv() -> str:
    jobs = execute_query("SELECT * FROM jobs ORDER BY id ASC")
    output = io.StringIO()
    if jobs:
        headers = list(jobs[0].keys())
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        for j in jobs:
            writer.writerow(j)
    return output.getvalue()

# ==========================================
# PORTAL SETTINGS, COMPANY ADMINS & OWNERSHIP
# ==========================================

def get_portal_contact() -> Dict[str, str]:
    rows = execute_query("SELECT key, value FROM portal_settings WHERE key IN ('contact_name', 'contact_phone', 'contact_note')")
    kv = {r["key"]: r["value"] for r in rows}
    phone = (kv.get("contact_phone") or ADMIN_CONTACT_PHONE or "").strip()
    digits = re.sub(r"\D", "", phone)
    wa_digits = ("91" + digits) if len(digits) == 10 else digits
    return {
        "name": (kv.get("contact_name") or ADMIN_CONTACT_NAME or "Portal Owner").strip(),
        "phone": phone,
        "wa_digits": wa_digits,
        "note": (kv.get("contact_note") or "कंपनी किंवा नवीन ॲडमिन पोर्टलचा ॲक्सेस घेण्यासाठी पोर्टल मालकाशी संपर्क साधा.").strip(),
    }

def update_portal_contact(name: str, phone: str, note: str) -> None:
    pairs = [
        ("contact_name", name.strip() or "Portal Owner"),
        ("contact_phone", phone.strip()),
        ("contact_note", note.strip()),
    ]
    for k, v in pairs:
        execute_mutation("INSERT OR REPLACE INTO portal_settings (key, value) VALUES (?, ?)", (k, v))

def get_admin_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    rows = execute_query("SELECT * FROM admin_users WHERE LOWER(username) = LOWER(?) LIMIT 1", (username.strip(),))
    return rows[0] if rows else None

def get_admin_users() -> List[Dict[str, Any]]:
    users = execute_query("SELECT id, username, company_name, role, can_view_all_jobs, can_add_jobs, is_active, created_at FROM admin_users ORDER BY id DESC")
    owners = execute_query("SELECT owner_username, COUNT(*) as cnt FROM job_owners GROUP BY owner_username")
    cnt_map = {r["owner_username"]: r["cnt"] for r in owners}
    for u in users:
        u["jobs_count"] = cnt_map.get(u["username"], 0)
    return users

def create_admin_user(
    username: str,
    password_hash: str,
    company_name: str,
    can_view_all_jobs: int = 0,
    can_add_jobs: int = 1
) -> int:
    uname = username.strip()
    if uname.lower() == ADMIN_USERNAME.strip().lower():
        raise ValueError("Cannot reuse Super Admin username.")
    if get_admin_user_by_username(uname):
        raise ValueError("Username already exists.")
    return execute_mutation(
        """
        INSERT INTO admin_users (username, password_hash, company_name, role, can_view_all_jobs, can_add_jobs, is_active, created_at)
        VALUES (?, ?, ?, 'company_admin', ?, ?, 1, ?)
        """,
        (uname, password_hash, company_name.strip(), int(bool(can_view_all_jobs)), int(bool(can_add_jobs)), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

def toggle_admin_flag(admin_id: int, column: str) -> None:
    if column not in {"can_view_all_jobs", "can_add_jobs", "is_active"}:
        raise ValueError("Invalid permission column.")
    rows = execute_query(f"SELECT {column} as val FROM admin_users WHERE id = ? LIMIT 1", (admin_id,))
    if not rows:
        return
    new_val = 0 if int(rows[0]["val"]) == 1 else 1
    execute_mutation(f"UPDATE admin_users SET {column} = ? WHERE id = ?", (new_val, admin_id))

def delete_admin_user(admin_id: int) -> None:
    execute_mutation("DELETE FROM admin_users WHERE id = ?", (admin_id,))

def set_job_owner(job_id: int, owner_username: str, company_name: str = "") -> None:
    if not job_id:
        return
    execute_mutation(
        "INSERT OR REPLACE INTO job_owners (job_id, owner_username, company_name, created_at) VALUES (?, ?, ?, ?)",
        (job_id, owner_username.strip(), company_name.strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

def get_job_owner(job_id: int) -> Optional[str]:
    rows = execute_query("SELECT owner_username FROM job_owners WHERE job_id = ? LIMIT 1", (job_id,))
    return rows[0]["owner_username"] if rows else None

def can_admin_modify_job(admin: Optional[Dict[str, Any]], job_id: int) -> bool:
    if not admin:
        return False
    if admin.get("role") == "super_admin":
        return True
    if admin.get("is_active") != 1:
        return False
    owner = get_job_owner(job_id)
    return bool(owner and owner.lower() == admin["username"].lower())

def get_admin_scoped_data(admin: Dict[str, Any], tab: str = "all") -> Dict[str, Any]:
    all_rows = execute_query("SELECT * FROM jobs ORDER BY posted_at DESC, id DESC")
    owner_rows = execute_query("SELECT job_id, owner_username, company_name FROM job_owners")
    owner_map = {int(r["job_id"]): r for r in owner_rows}

    ext_map = load_extended_map()
    enriched = []
    is_super = admin.get("role") == "super_admin"
    can_view_all = is_super or admin.get("can_view_all_jobs") == 1

    for r in all_rows:
        item = enrich_job_expiry(r, ext_map)
        own_info = owner_map.get(int(item["id"]))
        owner_uname = own_info["owner_username"] if own_info else ADMIN_USERNAME.strip()
        item["owner_username"] = owner_uname
        item["owner_company"] = own_info["company_name"] if own_info and own_info.get("company_name") else "Owner Portal"
        item["can_modify"] = is_super or (owner_uname.lower() == admin["username"].lower())

        if can_view_all or owner_uname.lower() == admin["username"].lower():
            enriched.append(item)

    total = len(enriched)
    active_all = [j for j in enriched if j["is_active"] == 1]
    open_jobs = [j for j in active_all if not j["is_expired"]]
    expired_grace = [j for j in enriched if j["is_expired"] and j["days_expired"] < EXPIRED_GRACE_DAYS]
    purge_ready = [j for j in enriched if j["is_expired"] and j["days_expired"] >= EXPIRED_GRACE_DAYS]
    govt = sum(1 for j in open_jobs if any(k in (j.get("category") or "").lower() for k in ["govt", "government", "railway", "psu"]))
    it_cnt = sum(1 for j in open_jobs if any(k in (j.get("category") or "").lower() for k in ["it", "software", "development"]))
    states_set = {j.get("state") for j in active_all if j.get("state")}
    archived_jobs = get_archived_jobs() if is_super else []

    filtered = enriched
    if tab == "active":
        filtered = open_jobs
    elif tab == "expired":
        filtered = [j for j in enriched if j["is_expired"]]

    return {
        "stats": {
            "totalJobs": total,
            "activeJobs": len(open_jobs),
            "publishedTotal": len(active_all),
            "expiredGraceJobs": len(expired_grace),
            "purgeReadyJobs": len(purge_ready),
            "archivedHistoryCount": len(archived_jobs),
            "inactiveJobs": max(0, total - len(active_all)),
            "governmentJobs": govt,
            "itJobs": it_cnt,
            "statesCovered": len(states_set),
        },
        "jobs": {"data": filtered, "filtered_total": len(filtered), "total": total},
        "archived_jobs": archived_jobs,
    }

def archive_all_and_clear_jobs() -> int:
    all_rows = execute_query("SELECT * FROM jobs ORDER BY id ASC")
    count = len(all_rows)
    if all_rows:
        archive_job_records(all_rows, reason="Handover Reset by Owner")
    execute_mutation("DELETE FROM jobs")
    execute_mutation("DELETE FROM job_owners")
    return count


