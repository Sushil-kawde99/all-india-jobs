import os
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config
import db
import auth
import data

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm seed check quietly once on worker start
    db.is_turso_connected()
    yield
    # Ensure Turso async session closes cleanly so Windows hot-reload releases port 8000 immediately
    db.close_turso_client()

app = FastAPI(title="JobDisha India", description="All-India Job Search & Career Platform", lifespan=lifespan)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.auto_reload = True
templates.env.globals["GOOGLE_SITE_VERIFICATION"] = config.GOOGLE_SITE_VERIFICATION
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def get_public_base_url(request: Request) -> str:
    env_url = (config.SITE_URL or "").strip().rstrip("/")
    if env_url and "localhost" not in env_url and "127.0.0.1" not in env_url:
        return env_url
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc or "localhost:8000"
    return f"{proto}://{host}".rstrip("/")

def get_client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "local"

@app.middleware("http")
async def prevent_stale_html_cache(request: Request, call_next):
    response = await call_next(request)
    if not request.url.path.startswith("/static/images"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response

def get_current_admin(request: Request) -> Optional[dict]:
    token = request.cookies.get(auth.COOKIE_NAME)
    return auth.get_session_admin(token)

def is_super_admin(admin: Optional[dict]) -> bool:
    return bool(admin and admin.get("role") == "super_admin")

# ==========================================
# PUBLIC ROUTES
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    stats = db.get_job_stats()
    latest_result = db.get_jobs(limit=6, is_active=1, sort="latest")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "stats": stats,
            "latest_jobs": latest_result["data"],
            "all_states": data.ALL_STATES,
            "categories": data.JOB_CATEGORIES,
        }
    )

@app.get("/jobs", response_class=HTMLResponse)
async def jobs_list(
    request: Request,
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
    per_page: int = 12
):
    from urllib.parse import urlencode
    per_page = per_page if per_page in (12, 24, 48, 50) else 12
    result = db.get_jobs(
        q=q,
        state=state,
        city=city,
        category=category,
        experience=experience,
        qualification=qualification,
        salary_range=salary_range,
        employment_type=employment_type,
        sort=sort,
        page=page,
        limit=per_page,
        is_active=1
    )
    raw_params = {k: v for k, v in request.query_params.items() if k != "page" and v}
    base_qs = urlencode(raw_params)

    return templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context={
            "result": result,
            "q": q,
            "state": state,
            "city": city,
            "category": category,
            "experience": experience,
            "salary_range": salary_range,
            "sort": sort,
            "per_page": per_page,
            "base_qs": base_qs,
            "all_states": data.ALL_STATES,
            "categories": data.JOB_CATEGORIES,
        }
    )

@app.get("/jobs/{slug}", response_class=HTMLResponse)
async def job_detail(request: Request, slug: str):
    job = db.get_job_by_slug(slug)
    if not job:
        return RedirectResponse(url="/jobs?error=not-found", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="job_detail.html",
        context={
            "job": job,
        }
    )

@app.get("/resume-builder", response_class=HTMLResponse)
async def resume_builder(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="resume_builder.html",
        context={}
    )

@app.get("/tools", response_class=HTMLResponse)
async def tools_hub(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="tools.html",
        context={}
    )

@app.get("/tools/in-hand-salary-calculator", response_class=HTMLResponse)
@app.get("/salary-calculator", response_class=HTMLResponse)
async def salary_calculator(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="salary_calculator.html",
        context={}
    )

@app.get("/tools/career-checklist", response_class=HTMLResponse)
@app.get("/career-checklist", response_class=HTMLResponse)
async def career_checklist(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="career_checklist.html",
        context={}
    )

@app.get("/saved-jobs", response_class=HTMLResponse)
async def saved_jobs(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="saved_jobs.html",
        context={}
    )

# ==========================================
# ADMIN AUTH & DASHBOARD
# ==========================================

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    if get_current_admin(request):
        return RedirectResponse(url="/admin", status_code=303)
    contact = db.get_portal_contact()
    return templates.TemplateResponse(
        request=request,
        name="admin_login.html",
        context={"error": None, "contact": contact}
    )

@app.post("/admin/login")
async def admin_login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    contact = db.get_portal_contact()
    client_ip = get_client_ip(request)
    if not auth.check_rate_limit(client_ip):
        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context={"error": "Too many failed attempts. Wait 1 min.", "contact": contact}
        )

    admin_user = auth.authenticate_admin(username, password)
    if admin_user:
        auth.reset_attempts(client_ip)
        token = auth.create_session_token(admin_user["username"])
        is_https = (request.headers.get("x-forwarded-proto") or request.url.scheme) == "https"
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(key=auth.COOKIE_NAME, value=token, httponly=True, secure=is_https, max_age=60*60*24*7, samesite="lax")
        return response

    auth.record_failed_attempt(client_ip)
    return templates.TemplateResponse(
        request=request,
        name="admin_login.html",
        context={"error": "Invalid admin username or password.", "contact": contact}
    )

@app.post("/admin/logout")
async def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key=auth.COOKIE_NAME)
    return response

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, tab: str = "all"):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=303)

    super_admin = is_super_admin(admin)
    if not super_admin and tab in ("admins", "archive"):
        tab = "all"

    scoped = db.get_admin_scoped_data(admin, tab=tab)
    is_turso = db.is_turso_connected()
    admin_users = db.get_admin_users() if super_admin else []
    contact = db.get_portal_contact() if super_admin else None

    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "admin": admin,
            "is_super_admin": super_admin,
            "admin_users": admin_users,
            "contact": contact,
            "stats": scoped["stats"],
            "jobs": scoped["jobs"],
            "archived_jobs": scoped["archived_jobs"],
            "active_tab": tab,
            "grace_days": db.EXPIRED_GRACE_DAYS,
            "is_turso": is_turso,
            "request": request,
        }
    )

@app.post("/admin/settings/contact")
async def admin_update_contact(
    request: Request,
    contact_name: str = Form(...),
    contact_phone: str = Form(""),
    contact_note: str = Form("")
):
    admin = get_current_admin(request)
    if not is_super_admin(admin):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    db.update_portal_contact(contact_name, contact_phone, contact_note)
    return RedirectResponse(url="/admin?tab=admins&msg=contact_saved", status_code=303)

@app.post("/admin/admins/create")
async def admin_create_company_admin(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    company_name: str = Form(...),
    can_view_all_jobs: Optional[str] = Form(None),
    can_add_jobs: Optional[str] = Form(None),
):
    admin = get_current_admin(request)
    if not is_super_admin(admin):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    try:
        pw_hash = auth.hash_password(password)
        db.create_admin_user(
            username=username,
            password_hash=pw_hash,
            company_name=company_name,
            can_view_all_jobs=1 if can_view_all_jobs else 0,
            can_add_jobs=1 if can_add_jobs else 0,
        )
        return RedirectResponse(url="/admin?tab=admins&msg=admin_created", status_code=303)
    except ValueError as ve:
        from urllib.parse import quote_plus
        return RedirectResponse(url=f"/admin?tab=admins&error_msg={quote_plus(str(ve))}", status_code=303)

@app.post("/admin/admins/toggle")
async def admin_toggle_company_admin(
    request: Request,
    admin_id: int = Form(...),
    column: str = Form(...)
):
    admin = get_current_admin(request)
    if not is_super_admin(admin):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    db.toggle_admin_flag(admin_id, column)
    return RedirectResponse(url="/admin?tab=admins&msg=perm_updated", status_code=303)

@app.post("/admin/admins/delete")
async def admin_delete_company_admin(request: Request, admin_id: int = Form(...)):
    admin = get_current_admin(request)
    if not is_super_admin(admin):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    db.delete_admin_user(admin_id)
    return RedirectResponse(url="/admin?tab=admins&msg=admin_deleted", status_code=303)

@app.post("/admin/reset-all-jobs")
async def admin_reset_all_jobs(request: Request):
    admin = get_current_admin(request)
    if not is_super_admin(admin):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    cleared = db.archive_all_and_clear_jobs()
    return RedirectResponse(url=f"/admin?reset_count={cleared}", status_code=303)

@app.post("/admin/sync-jobs")
async def admin_sync_jobs_post(request: Request):
    admin = get_current_admin(request)
    if not is_super_admin(admin):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    import sync_service
    result = sync_service.sync_latest_vacancies(limit=25)
    return RedirectResponse(url=f"/admin?synced={result['new_inserted']}", status_code=303)

@app.post("/admin/purge-expired")
async def admin_purge_expired_post(request: Request):
    admin = get_current_admin(request)
    if not is_super_admin(admin):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    res = db.archive_and_purge_expired_jobs(db.EXPIRED_GRACE_DAYS)
    return RedirectResponse(url=f"/admin?purged={res['archived_and_deleted']}", status_code=303)

@app.post("/admin/jobs/extend")
async def admin_extend_job_deadline(
    request: Request,
    id: int = Form(...),
    last_date: str = Form(...)
):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=303)
    if not db.can_admin_modify_job(admin, id):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    db.extend_job_deadline(id, last_date)
    return RedirectResponse(url="/admin?extended=1", status_code=303)

@app.get("/admin/archive/download")
async def admin_download_archive_csv(request: Request):
    admin = get_current_admin(request)
    if not is_super_admin(admin):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    if os.path.exists(db.ARCHIVE_CSV_PATH):
        with open(db.ARCHIVE_CSV_PATH, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = ",".join(db.ARCHIVE_CSV_FIELDS) + "\n"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=jobdisha_expired_archive.csv"}
    )

@app.get("/admin/jobs/new", response_class=HTMLResponse)
async def admin_new_job_page(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=303)
    if not is_super_admin(admin) and admin.get("can_add_jobs") != 1:
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="admin_new_job.html",
        context={
            "admin": admin,
            "default_company": "" if is_super_admin(admin) else admin.get("company_name", ""),
            "all_states": data.ALL_STATES,
            "categories": data.JOB_CATEGORIES,
        }
    )

@app.post("/admin/jobs/new")
async def admin_new_job_post(
    request: Request,
    title: str = Form(...),
    company: str = Form(...),
    category: str = Form("IT / Software"),
    state: str = Form(...),
    city: str = Form(...),
    apply_url: str = Form(...),
    description: str = Form(...),
    salary_min: Optional[int] = Form(None),
    salary_max: Optional[int] = Form(None),
    experience: str = Form("Fresher"),
    qualification: Optional[str] = Form(None),
    source_url: Optional[str] = Form(None),
    last_date: Optional[str] = Form(None),
):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=303)
    if not is_super_admin(admin) and admin.get("can_add_jobs") != 1:
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)

    new_id = db.create_job({
        "title": title,
        "company": company,
        "category": category,
        "state": state,
        "city": city,
        "apply_url": apply_url,
        "description": description,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "experience": experience,
        "qualification": qualification,
        "source_url": source_url,
        "last_date": last_date,
        "is_active": 1,
    })
    db.set_job_owner(new_id, admin["username"], admin.get("company_name", company))
    return RedirectResponse(url="/admin?msg=created", status_code=303)

@app.get("/admin/jobs/edit/{job_id}", response_class=HTMLResponse)
async def admin_edit_job_page(request: Request, job_id: int):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=303)
    if not db.can_admin_modify_job(admin, job_id):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    job = db.get_job_by_id(job_id)
    if not job:
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="admin_edit_job.html",
        context={
            "job": job,
            "all_states": data.ALL_STATES,
            "categories": data.JOB_CATEGORIES,
        }
    )

@app.post("/admin/jobs/edit/{job_id}")
async def admin_edit_job_post(
    request: Request,
    job_id: int,
    title: str = Form(...),
    company: str = Form(...),
    category: str = Form(...),
    state: str = Form(...),
    city: str = Form(...),
    apply_url: str = Form(...),
    description: str = Form(...),
    salary_min: Optional[int] = Form(None),
    salary_max: Optional[int] = Form(None),
    experience: str = Form("Fresher"),
    qualification: Optional[str] = Form(None),
    source_url: Optional[str] = Form(None),
    last_date: Optional[str] = Form(None),
):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=303)
    if not db.can_admin_modify_job(admin, job_id):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)

    db.update_job(job_id, {
        "title": title,
        "company": company,
        "category": category,
        "state": state,
        "city": city,
        "apply_url": apply_url,
        "description": description,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "experience": experience,
        "qualification": qualification,
        "source_url": source_url,
        "last_date": last_date,
    })
    return RedirectResponse(url="/admin?msg=updated", status_code=303)

@app.post("/admin/jobs/delete")
async def admin_delete_job(request: Request, id: int = Form(...)):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=303)
    if not db.can_admin_modify_job(admin, id):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    db.delete_job(id)
    return RedirectResponse(url="/admin?msg=deleted", status_code=303)

@app.post("/admin/jobs/toggle")
async def admin_toggle_job(request: Request, id: int = Form(...), is_active: int = Form(...)):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=303)
    if not db.can_admin_modify_job(admin, id):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    db.toggle_job_active(id, is_active)
    return RedirectResponse(url="/admin?msg=updated", status_code=303)

@app.get("/admin/import-csv", response_class=HTMLResponse)
async def admin_import_csv_page(request: Request):
    admin = get_current_admin(request)
    if not is_super_admin(admin):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="admin_import_csv.html",
        context={"error": None}
    )

@app.post("/admin/import-csv")
async def admin_import_csv_post(
    request: Request,
    csv_file: Optional[UploadFile] = File(None),
    csv_text: Optional[str] = Form(None)
):
    admin = get_current_admin(request)
    if not is_super_admin(admin):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)

    content = ""
    if csv_file and csv_file.size:
        content_bytes = await csv_file.read()
        content = content_bytes.decode("utf-8", errors="ignore")
    elif csv_text and csv_text.strip():
        content = csv_text.strip()

    if not content:
        return templates.TemplateResponse(
            request=request,
            name="admin_import_csv.html",
            context={"error": "No CSV content provided."}
        )

    res = db.bulk_import_csv(content)
    if res["errors"] and res["imported"] == 0:
        return templates.TemplateResponse(
            request=request,
            name="admin_import_csv.html",
            context={"error": res["errors"][0]}
        )

    return RedirectResponse(url=f"/admin?imported={res['imported']}", status_code=303)

@app.get("/admin/export-csv")
async def admin_export_csv(request: Request):
    admin = get_current_admin(request)
    if not is_super_admin(admin):
        return RedirectResponse(url="/admin?error=forbidden", status_code=303)
    csv_data = db.export_all_jobs_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=jobdisha_vacancies.csv"}
    )

# ==========================================
# SEO DIRECTIVES
# ==========================================

@app.get("/health")
def health_check():
    return {"status": "ok", "turso": db.is_turso_connected()}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    return FileResponse(os.path.join(STATIC_DIR, "favicon.ico"), media_type="image/x-icon")

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt(request: Request):
    base = get_public_base_url(request)
    return f"User-agent: *\nAllow: /\nDisallow: /admin\nSitemap: {base}/sitemap.xml\n"

@app.get("/sitemap.xml")
def sitemap_xml(request: Request):
    base = get_public_base_url(request)
    jobs = db.get_jobs(limit=1000, is_active=1)["data"]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    static_urls = ["", "/jobs", "/resume-builder", "/tools", "/tools/in-hand-salary-calculator", "/tools/career-checklist", "/saved-jobs"]
    for u in static_urls:
        xml.append(f"  <url><loc>{base}{u}</loc><priority>0.8</priority></url>")
    for j in jobs:
        xml.append(f"  <url><loc>{base}/jobs/{j['slug']}</loc><priority>0.9</priority></url>")
    xml.append('</urlset>')
    return Response(content="\n".join(xml), media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    is_cloud = "PORT" in os.environ
    print("\n" + "="*60)
    print("   🚀 ALL INDIA JOBS - FASTAPI SERVER")
    print(f"   🌐 Website URL: http://{'0.0.0.0' if is_cloud else 'localhost'}:{port}")
    print(f"   🔑 Admin Panel: http://localhost:{port}/admin/login")
    print("   ☁️ Database:    Turso Cloud (my-portfolio-db)")
    if not is_cloud:
        print("   ⚡ Auto-Reload: .py/.env auto-restart + 0ms HTML & Cache-Control")
    print("   🛑 Press CTRL+C to stop the server")
    print("="*60 + "\n")
    uvicorn.run(
        "main:app",
        host="0.0.0.0" if is_cloud else "127.0.0.1",
        port=port,
        reload=not is_cloud,
        reload_includes=["*.py", ".env"] if not is_cloud else None,
        reload_excludes=["*.db", "*.db-*", "archive/*", "__pycache__/*", ".git/*", "scratch_*"] if not is_cloud else None,
    )
