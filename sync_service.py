import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import httpx
import bs4
import db
from data import ALL_STATES, INDIAN_LOCATIONS

SOURCES = [
    {
        "name": "FreeJobAlert Pan-India Govt Notifications",
        "url": "https://www.freejobalert.com/feed",
        "category_default": "Government Jobs"
    }
]

NON_JOB_KEYWORDS = [
    "answer key", "admit card", "result", "datesheet", "syllabus",
    "cut off", "cutoff", "merit list", "select list", "score card",
    "marks", "call letter", "hall ticket", "mock test", "exam date",
    "time table", "timetable", "practice links"
]

BLOCKED_LINK_DOMAINS = (
    "freejobalert.com", "t.me", "telegram.", "whatsapp.com",
    "facebook.com", "instagram.com", "youtube.com", "twitter.com",
    "x.com", "linkedin.com", "play.google.com", "pinterest.com",
    "threads.net", "sarkariresult"
)

JOB_KEYWORDS = [
    "recruitment", "vacancy", "vacancies", "posts", "apply online", 
    "apply offline", "hiring", "officer", "engineer", "clerk", 
    "associate", "trainee", "apprentice", "scientist", "specialist", 
    "executive", "assistant", "manager", "constable", "inspector"
]

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = bs4.BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ").strip()

def detect_state_and_city(text: str) -> tuple[str, str]:
    text_lower = text.lower()
    for loc in INDIAN_LOCATIONS:
        for city in loc["cities"]:
            if city.lower() in text_lower:
                return loc["name"], city
    for state in ALL_STATES:
        if state.lower() in text_lower:
            return state, state
    if "delhi" in text_lower or "new delhi" in text_lower:
        return "Delhi", "New Delhi"
    return "All India", "Pan-India"

def detect_category(title: str, text: str) -> str:
    combined = f"{title} {text}".lower()
    if any(k in combined for k in ["railway", "rrb", "irctc", "rail", "loco"]):
        return "Railway Jobs"
    if any(k in combined for k in ["bank", "sbi", "ibps", "rbi", "pnb", "bob"]):
        return "Banking"
    if any(k in combined for k in ["apprentice", "apprenticeship"]):
        return "Apprenticeships"
    if any(k in combined for k in ["software", "developer", "programmer", "it officer", "python", "java"]):
        return "IT / Software"
    if any(k in combined for k in ["doctor", "nurse", "aiims", "medical", "hospital", "health"]):
        return "Healthcare"
    if any(k in combined for k in ["professor", "teacher", "lecturer", "faculty"]):
        return "Teaching"
    if any(k in combined for k in ["psu", "ongc", "bhel", "ntpc", "iocl", "sail", "gail"]):
        return "PSU Jobs"
    return "Government Jobs"

def detect_qualification(text: str) -> str:
    text_lower = text.lower()
    if any(k in text_lower for k in ["b.e", "b.tech", "engineering", "m.tech"]):
        return "B.E. / B.Tech / Diploma in Engineering"
    if any(k in text_lower for k in ["iti", "trade"]):
        return "10th Pass + ITI (Relevant Trade)"
    if any(k in text_lower for k in ["12th", "intermediate", "hsc"]):
        return "12th Pass / Intermediate"
    if any(k in text_lower for k in ["10th", "matriculation", "ssc"]):
        return "10th Pass (Matriculation)"
    if any(k in text_lower for k in ["mbbs", "md", "ms"]):
        return "MBBS / Post Graduate Degree"
    if any(k in text_lower for k in ["graduate", "degree", "b.a", "b.sc", "b.com"]):
        return "Any Bachelor's Degree / Graduate"
    return "Any Graduate / Relevant Qualification"

def extract_organization(title: str) -> str:
    # Most feeds have "Organization Recruitment 2026..." or "Organization – Apply Online..."
    parts = re.split(r'Recruitment|–|-|Invites|Notification', title, flags=re.IGNORECASE)
    if parts and len(parts[0].strip()) > 3:
        cleaned = re.sub(r'\b(2025|2026|Online|Offline|Apply)\b', '', parts[0], flags=re.IGNORECASE).strip()
        if len(cleaned) > 2:
            return cleaned[:50]
    return "Government of India Organization"

def parse_last_date(text: str) -> str:
    # Try finding patterns like "till 15 December 2026" or "last date: 20-12-2026"
    date_match = re.search(r'(?:till|before|last date|closing date|extended to|extended till)[:\s]+([0-9]{1,2}[\s\/\-][A-Za-z0-9]+[\s\/\-][0-9]{2,4})', text, re.IGNORECASE)
    if date_match:
        raw = date_match.group(1).strip()
        parsed = db.parse_date_safe(raw)
        if parsed:
            return parsed.strftime("%Y-%m-%d")
    # Default to 30 days from today
    future_date = datetime.now() + timedelta(days=30)
    return future_date.strftime("%Y-%m-%d")

def is_blocked_url(url: str) -> bool:
    u_lower = url.lower()
    return any(dom in u_lower for dom in BLOCKED_LINK_DOMAINS)

def extract_domain_fallback(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r'\b(?:at|@|website|visit)\s+([a-zA-Z0-9.-]+\.(?:gov\.in|nic\.in|ac\.in|edu\.in|res\.in|org\.in|edu|in|org))\b', text, re.IGNORECASE)
    if m:
        dom = m.group(1).strip().rstrip('.')
        if not is_blocked_url(dom):
            return f"https://{dom}"
    return None

def extract_official_links(
    article_url: str,
    desc_text: str = "",
    client: Optional[httpx.Client] = None
) -> Tuple[str, str]:
    """
    Fetches the notification article page and extracts the true official
    employer/government Apply portal URL and Notification PDF/Source URL.
    Never returns Telegram, social links, or third-party blogs when an official
    portal URL is available.
    """
    apply_candidates: List[Tuple[int, str]] = []
    pdf_candidates: List[Tuple[int, str]] = []

    try:
        http = client or httpx.Client(timeout=10.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        resp = http.get(article_url)
        if client is None:
            http.close()

        if resp.status_code == 200:
            soup = bs4.BeautifulSoup(resp.text, "html.parser")
            scope = soup.find("article") or soup.find("main") or soup

            for a in scope.find_all("a", href=True):
                href = a["href"].strip()
                if not href.startswith("http") or is_blocked_url(href):
                    continue

                txt = a.get_text(" ", strip=True).lower()
                href_lower = href.lower()
                is_pdf = ".pdf" in href_lower

                score = 0
                if any(k in txt for k in ("apply online", "online application", "recruitment portal", "application website", "official application", "apply link")):
                    score += 65
                elif any(k in txt for k in ("official website", "official portal", "visit website", "visit official")):
                    score += 45
                elif any(k in txt for k in ("apply", "click here", "application form")):
                    score += 20

                if any(dom in href_lower for dom in (".gov.in", ".nic.in", ".ac.in", ".edu.in", ".res.in", ".org.in", ".edu")):
                    score += 30
                if any(k in href_lower for k in ("recruit", "career", "apply", "jobs")):
                    score += 15

                if is_pdf:
                    pdf_score = score + (30 if any(k in txt for k in ("notification", "advertisement", "circular")) else 10)
                    pdf_candidates.append((pdf_score, href))
                else:
                    apply_candidates.append((score + 15, href))
    except Exception as e:
        print(f"Official link extraction note for {article_url}: {e}")

    apply_candidates.sort(key=lambda x: x[0], reverse=True)
    pdf_candidates.sort(key=lambda x: x[0], reverse=True)

    domain_fallback = extract_domain_fallback(desc_text)

    if apply_candidates:
        official_apply = apply_candidates[0][1]
    elif pdf_candidates:
        official_apply = pdf_candidates[0][1]
    elif domain_fallback:
        official_apply = domain_fallback
    else:
        official_apply = article_url

    if pdf_candidates:
        official_source = pdf_candidates[0][1]
    elif apply_candidates:
        official_source = apply_candidates[0][1]
    else:
        official_source = article_url

    return official_apply, official_source

def fetch_and_parse_feed(feed_url: str) -> List[Dict[str, Any]]:
    jobs = []
    try:
        response = httpx.get(
            feed_url, 
            timeout=15.0, 
            headers={"User-Agent": "JobDisha-India-Bot/1.0 (+https://jobdisha.in)"}
        )
        if response.status_code != 200:
            return []

        root = ET.fromstring(response.text)
        items = root.findall(".//item")

        for item in items:
            title_elem = item.find("title")
            link_elem = item.find("link")
            desc_elem = item.find("description")
            pubdate_elem = item.find("pubDate")

            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
            link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
            raw_desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""
            desc = clean_html(raw_desc)

            # Skip non-job posts (exam results, syllabus, admit cards)
            title_lower = title.lower()
            if any(k in title_lower for k in NON_JOB_KEYWORDS):
                continue
            if not any(k in title_lower for k in JOB_KEYWORDS) and not any(k in desc.lower() for k in JOB_KEYWORDS):
                continue

            company = extract_organization(title)
            state, city = detect_state_and_city(f"{title} {desc}")
            category = detect_category(title, desc)
            qualification = detect_qualification(desc)
            last_date = parse_last_date(desc)

            posted_date = datetime.now().strftime("%Y-%m-%d")
            if pubdate_elem is not None and pubdate_elem.text:
                try:
                    # e.g. Thu, 26 Nov 2026 06:30:11 GMT
                    dt = datetime.strptime(pubdate_elem.text[:16].strip(), "%a, %d %b %Y")
                    posted_date = dt.strftime("%Y-%m-%d")
                except Exception:
                    pass

            slug = db.generate_slug(title, company)

            job_obj = {
                "slug": slug,
                "title": title[:140],
                "company": company,
                "city": city,
                "state": state,
                "category": category,
                "employment_type": "Government" if "Government" in category or "Railway" in category or "PSU" in category else "Full Time",
                "experience": "Fresher" if "apprentice" in category.lower() or "trainee" in title.lower() else "0-2 Years",
                "qualification": qualification,
                "salary_min": 350000 if "Officer" in title else 240000,
                "salary_max": 750000 if "Officer" in title else 520000,
                "description": desc[:800] if len(desc) > 50 else f"{title}. Check official circular for complete eligibility, notification PDF and apply procedure.",
                "apply_url": link,
                "source_url": link,
                "posted_at": posted_date,
                "last_date": last_date,
                "verified_at": datetime.now().strftime("%Y-%m-%d"),
                "is_active": 1
            }
            jobs.append(job_obj)

    except Exception as e:
        print(f"Error fetching feed {feed_url}: {e}")

    return jobs

def sync_latest_vacancies(limit: int = 25) -> Dict[str, Any]:
    """
    Fetches real govt vacancies, detects date extensions, checks for duplicates
    against Turso Cloud, extracts true official portal Apply links, inserts new
    authentic vacancies, and archives+purges jobs expired 16+ days ago.
    """
    total_fetched = 0
    new_inserted = 0
    extended_count = 0
    skipped_duplicates = 0
    inserted_list = []

    http_client = httpx.Client(
        timeout=12.0,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )

    try:
        for src in SOURCES:
            feed_jobs = fetch_and_parse_feed(src["url"])
            total_fetched += len(feed_jobs)

            for job in feed_jobs[:limit]:
                # Duplicate & extension check by Title & Company
                existing = db.execute_query(
                    "SELECT id, last_date FROM jobs WHERE LOWER(title) = LOWER(?) AND LOWER(company) = LOWER(?) LIMIT 1",
                    (job["title"].strip(), job["company"].strip())
                )

                if existing and len(existing) > 0:
                    old_date_obj = db.parse_date_safe(existing[0].get("last_date"))
                    new_date_obj = db.parse_date_safe(job.get("last_date"))
                    if new_date_obj and (not old_date_obj or new_date_obj > old_date_obj):
                        db.extend_job_deadline(existing[0]["id"], job["last_date"])
                        extended_count += 1
                    else:
                        skipped_duplicates += 1
                    continue

                # Resolve real official employer/government Apply link before saving
                article_ref = job["apply_url"]
                official_apply, official_source = extract_official_links(
                    article_ref,
                    job.get("description", ""),
                    client=http_client
                )
                job["apply_url"] = official_apply
                job["source_url"] = official_source

                # Insert into Turso Cloud database
                try:
                    new_id = db.create_job(job)
                    new_inserted += 1
                    inserted_list.append({
                        "id": new_id,
                        "title": job["title"],
                        "company": job["company"],
                        "state": job["state"],
                        "category": job["category"],
                        "apply_url": job["apply_url"]
                    })
                except Exception as e:
                    print(f"Failed to insert job '{job['title']}': {e}")
    finally:
        http_client.close()

    # Auto-Archive & Purge expired vacancies past the 16-day grace window
    purge_res = db.archive_and_purge_expired_jobs(db.EXPIRED_GRACE_DAYS)

    return {
        "status": "success",
        "total_fetched": total_fetched,
        "new_inserted": new_inserted,
        "extended_count": extended_count,
        "skipped_duplicates": skipped_duplicates,
        "purged_count": purge_res["archived_and_deleted"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "recent_jobs": inserted_list[:5]
    }

def repair_existing_synced_jobs() -> Dict[str, int]:
    """
    Repairs existing synced vacancies whose apply_url still points to a third-party
    feed article instead of the true official site, and removes any accidentally
    ingested exam result / mock test non-job entries.
    """
    rows = db.execute_query("SELECT id, title, description, apply_url FROM jobs ORDER BY id ASC")
    repaired = 0
    removed_non_jobs = 0

    http_client = httpx.Client(
        timeout=10.0,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )

    try:
        for r in rows:
            title_lower = (r.get("title") or "").lower()
            if any(k in title_lower for k in NON_JOB_KEYWORDS):
                db.delete_job(r["id"], archive_first=False)
                removed_non_jobs += 1
                continue

            cur_url = r.get("apply_url") or ""
            if "freejobalert.com" in cur_url.lower():
                official_apply, official_source = extract_official_links(
                    cur_url,
                    r.get("description") or "",
                    client=http_client
                )
                if official_apply and official_apply != cur_url:
                    db.execute_mutation(
                        "UPDATE jobs SET apply_url = ?, source_url = ?, updated_at = ? WHERE id = ?",
                        (official_apply, official_source, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), r["id"])
                    )
                    repaired += 1
    finally:
        http_client.close()

    return {"repaired": repaired, "removed_non_jobs": removed_non_jobs}

if __name__ == "__main__":
    print("==================================================")
    print("   JOBDISHA INDIA - DAILY VACANCY AUTO-SYNC")
    print("==================================================")
    print("Connecting to live recruitment feeds and Turso Cloud...")
    try:
        res = sync_latest_vacancies(limit=10)
        print(f"\nResult:")
        print(f"  • Total announcements processed: {res['total_fetched']}")
        print(f"  • New vacancies added to Turso:  {res['new_inserted']}")
        print(f"  • Deadlines auto-extended:       {res['extended_count']}")
        print(f"  • Duplicates skipped:            {res['skipped_duplicates']}")
        print(f"  • Expired (16d+) archived/purged:{res['purged_count']}")
        if res["recent_jobs"]:
            print("\nNew Jobs Added:")
            for j in res["recent_jobs"]:
                print(f"  + [{j['id']}] {j['title']} ({j['company']} - {j['state']})")
        print("==================================================")
    finally:
        db.close_turso_client()
