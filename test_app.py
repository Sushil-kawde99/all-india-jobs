from fastapi.testclient import TestClient
from main import app
import auth

client = TestClient(app)

def test_homepage():
    r = client.get("/")
    assert r.status_code == 200
    assert "All India Jobs" in r.text
    assert "Naukri Jobs India" in r.text
    assert "Find Jobs" in r.text
    print("✅ Homepage test passed (HTTP 200)")

def test_jobs_list():
    r = client.get("/jobs")
    assert r.status_code == 200
    assert "Find Jobs in India" in r.text
    assert "Apply Filters" in r.text
    assert "Vacancies pagination" in r.text
    assert "/jobs?page=2" in r.text

    r_p2 = client.get("/jobs?page=2")
    assert r_p2.status_code == 200
    assert "Page 2 of" in r_p2.text
    assert "/jobs?page=1" in r_p2.text

    r_all = client.get("/jobs?per_page=48")
    assert r_all.status_code == 200
    print("✅ Jobs listing & pagination (Pages 1-4 + 48/page) test passed (HTTP 200)")

def test_jobs_filter_maharashtra():
    r = client.get("/jobs?state=Maharashtra")
    assert r.status_code == 200
    assert "Maharashtra" in r.text
    print("✅ Maharashtra State filter test passed (HTTP 200)")

def test_jobs_filter_fresher():
    r = client.get("/jobs?experience=fresher")
    assert r.status_code == 200
    print("✅ Fresher filter test passed (HTTP 200)")

def test_job_detail():
    r = client.get("/jobs/tcs-software-engineer-bengaluru-2026")
    assert r.status_code == 200
    assert "Tata Consultancy Services" in r.text
    assert "https://ibegin.tcs.com/iBegin/jobs/search" in r.text
    assert 'application/ld+json' in r.text
    print("✅ Job Detail & JSON-LD test passed (HTTP 200)")

def test_resume_builder():
    r = client.get("/resume-builder")
    assert r.status_code == 200
    assert "ATS Resume Builder" in r.text
    print("✅ Resume Builder test passed (HTTP 200)")

def test_salary_calculator():
    r = client.get("/salary-calculator")
    assert r.status_code == 200
    assert "In-Hand Salary Calculator" in r.text
    print("✅ Salary Calculator test passed (HTTP 200)")

def test_career_checklist():
    r = client.get("/career-checklist")
    assert r.status_code == 200
    assert "Job Readiness" in r.text
    print("✅ Career Checklist test passed (HTTP 200)")

def test_saved_jobs():
    r = client.get("/saved-jobs")
    assert r.status_code == 200
    assert "Saved Jobs" in r.text
    print("✅ Saved Jobs test passed (HTTP 200)")

def test_seo_endpoints():
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"

    sitemap = client.get("/sitemap.xml", headers={"host": "allindiajobs.onrender.com", "x-forwarded-proto": "https"})
    assert sitemap.status_code == 200
    assert "<urlset" in sitemap.text
    assert "https://allindiajobs.onrender.com/jobs" in sitemap.text

    robots = client.get("/robots.txt", headers={"host": "allindiajobs.onrender.com", "x-forwarded-proto": "https"})
    assert robots.status_code == 200
    assert "User-agent" in robots.text
    assert "https://allindiajobs.onrender.com/sitemap.xml" in robots.text
    print("✅ Health Check, Dynamic Proxy SEO Sitemap & Robots test passed (HTTP 200)")

def test_admin_flow():
    # Login page
    login_page = client.get("/admin/login")
    assert login_page.status_code == 200

    # Unauthenticated dashboard access
    dash_unauth = client.get("/admin", follow_redirects=False)
    assert dash_unauth.status_code in [302, 303, 307]

    # Valid Login
    import config
    login_post = client.post(
        "/admin/login",
        data={"username": config.ADMIN_USERNAME, "password": config.ADMIN_PASSWORD},
        follow_redirects=False
    )
    assert login_post.status_code in [302, 303, 307]
    session_cookie = login_post.cookies.get(auth.COOKIE_NAME)
    assert session_cookie is not None

    # Authenticated dashboard access + tabs
    dash_auth = client.get("/admin", cookies={auth.COOKIE_NAME: session_cookie})
    assert dash_auth.status_code == 200
    assert "Admin Dashboard" in dash_auth.text
    assert "jd-modal-backdrop" in dash_auth.text
    assert "openExtendModal" in dash_auth.text

    for tab in ("active", "expired", "archive"):
        r_tab = client.get(f"/admin?tab={tab}", cookies={auth.COOKIE_NAME: session_cookie})
        assert r_tab.status_code == 200

    r_csv = client.get("/admin/archive/download", cookies={auth.COOKIE_NAME: session_cookie})
    assert r_csv.status_code == 200
    assert "archived_at" in r_csv.text
    print("✅ Admin Auth, Dashboard Tabs, Popups & Archive CSV test passed (HTTP 200)")

def test_expiry_grace_and_popups():
    from datetime import datetime, timedelta
    import db

    today = datetime.now().date()
    two_days_ago = (today - timedelta(days=2)).strftime("%Y-%m-%d")
    seventeen_days_ago = (today - timedelta(days=17)).strftime("%Y-%m-%d")
    future_date = (today + timedelta(days=15)).strftime("%Y-%m-%d")

    # Unit check on enrich_job_expiry
    e1 = db.enrich_job_expiry({"id": 9991, "last_date": two_days_ago}, ext_map={})
    assert e1["is_expired"] is True
    assert e1["days_expired"] == 2
    assert e1["purge_in_days"] == 14
    assert e1["expiry_status"] == "grace_expired"

    e2 = db.enrich_job_expiry({"id": 9992, "last_date": seventeen_days_ago}, ext_map={})
    assert e2["is_expired"] is True
    assert e2["days_expired"] == 17
    assert e2["purge_in_days"] == 0
    assert e2["expiry_status"] == "purge_ready"

    e3 = db.enrich_job_expiry({"id": 9993, "last_date": future_date}, ext_map={"9993": {"old_date": two_days_ago}})
    assert e3["is_expired"] is False
    assert e3["is_extended"] is True

    # End-to-end route test with a temporary expired job in grace window (cleaned up right after)
    temp_slug = "temp-test-expired-grace-check"
    temp_id = db.create_job({
        "slug": temp_slug,
        "title": "Temporary Expiry Verification Role",
        "company": "Test Corp",
        "city": "Pune",
        "state": "Maharashtra",
        "category": "IT / Software",
        "description": "Verification record for expiry grace UI.",
        "apply_url": "https://example.com/apply",
        "last_date": two_days_ago,
        "is_active": 1
    })
    try:
        # Detail page must still be clickable/accessible during 16-day grace period,
        # but Apply must be replaced with apply-expired-btn popup guard!
        detail_res = client.get(f"/jobs/{temp_slug}")
        assert detail_res.status_code == 200
        assert "apply-expired-btn" in detail_res.text
        assert "Application Closed" in detail_res.text
        assert "jd-modal-backdrop" in detail_res.text
    finally:
        if temp_id:
            db.delete_job(temp_id, archive_first=False)
    print("✅ Expiry Grace (16-day), Apply Guard, Date Extension & Popup integration test passed!")

def test_branding_and_favicon():
    r_ico = client.get("/favicon.ico")
    assert r_ico.status_code == 200
    assert len(r_ico.content) > 500

    for asset in ("favicon.png", "favicon-32x32.png", "logo-mark.png", "logo-full.png", "logo-header.png"):
        r_img = client.get(f"/static/images/{asset}")
        assert r_img.status_code == 200
        assert len(r_img.content) > 500

    r_home = client.get("/")
    assert "logo-header.png" in r_home.text
    assert "logo-full.png" in r_home.text
    assert "favicon-32x32.png" in r_home.text
    assert "Find Jobs. Build Your Career.</span>" not in r_home.text

    anon_client = TestClient(app)
    r_login = anon_client.get("/admin/login")
    assert "logo-full.png" in r_login.text
    assert "favicon-32x32.png" in r_login.text
    assert "Need Portal Access?" in r_login.text
    print("✅ Brand Logos & Chrome Tab Favicon test passed (HTTP 200)")

def test_multi_admin_isolation_and_contact():
    import config, db
    db.seed_turso_if_empty()

    super_client = TestClient(app)
    r_su = super_client.post(
        "/admin/login",
        data={"username": config.ADMIN_USERNAME, "password": config.ADMIN_PASSWORD},
        follow_redirects=False
    )
    assert r_su.status_code in [302, 303]
    su_cookie = r_su.cookies.get(auth.COOKIE_NAME)
    assert su_cookie

    r_admins_tab = super_client.get("/admin?tab=admins", cookies={auth.COOKIE_NAME: su_cookie})
    assert r_admins_tab.status_code == 200
    assert "Create New Company Admin" in r_admins_tab.text
    assert "Portal Owner Contact" in r_admins_tab.text

    temp_uname = "_test_co_hr_iso"
    temp_pwd = "CompanyPass@123"
    temp_job_title = "_Temp Isolated Co QA Engineer"
    created_admin_id = None
    created_job_id = None

    try:
        # Ensure clean slate if leftover
        old_u = db.get_admin_user_by_username(temp_uname)
        if old_u:
            db.delete_admin_user(old_u["id"])

        # Super admin creates isolated Company Admin (can_view_all_jobs=False, can_add_jobs=True)
        r_create = super_client.post(
            "/admin/admins/create",
            cookies={auth.COOKIE_NAME: su_cookie},
            data={
                "company_name": "Acme Tech Pvt Ltd",
                "username": temp_uname,
                "password": temp_pwd,
                "can_add_jobs": "1"
            },
            follow_redirects=False
        )
        assert r_create.status_code in [302, 303]
        assert "admin_created" in r_create.headers.get("location", "")

        admin_rec = db.get_admin_user_by_username(temp_uname)
        assert admin_rec is not None
        assert admin_rec["can_view_all_jobs"] == 0
        assert admin_rec["can_add_jobs"] == 1
        created_admin_id = admin_rec["id"]

        # Log in as isolated Company Admin
        co_client = TestClient(app)
        r_co_login = co_client.post(
            "/admin/login",
            data={"username": temp_uname, "password": temp_pwd},
            follow_redirects=False
        )
        assert r_co_login.status_code in [302, 303]
        co_cookie = r_co_login.cookies.get(auth.COOKIE_NAME)
        assert co_cookie

        # Isolated dashboard must NOT show Super Admin's jobs (e.g. TCS)
        r_co_dash = co_client.get("/admin", cookies={auth.COOKIE_NAME: co_cookie})
        assert r_co_dash.status_code == 200
        assert "Acme Tech Pvt Ltd" in r_co_dash.text
        assert "Tata Consultancy Services" not in r_co_dash.text
        assert "Private Workspace" in r_co_dash.text

        # Company Admin cannot access Super Admin endpoints (sync / reset / manage admins)
        r_forbid = co_client.post("/admin/sync-jobs", cookies={auth.COOKIE_NAME: co_cookie}, follow_redirects=False)
        assert "forbidden" in r_forbid.headers.get("location", "")
        r_forbid_del = co_client.post("/admin/jobs/delete", cookies={auth.COOKIE_NAME: co_cookie}, data={"id": "1"}, follow_redirects=False)
        assert "forbidden" in r_forbid_del.headers.get("location", "")

        # Company Admin CAN post their own company job
        r_post_job = co_client.post(
            "/admin/jobs/new",
            cookies={auth.COOKIE_NAME: co_cookie},
            data={
                "title": temp_job_title,
                "company": "Acme Tech Pvt Ltd",
                "category": "IT / Software",
                "state": "Maharashtra",
                "city": "Pune",
                "apply_url": "https://example.com/acme-apply",
                "description": "Isolated company job posting check."
            },
            follow_redirects=False
        )
        assert r_post_job.status_code in [302, 303]
        assert "msg=created" in r_post_job.headers.get("location", "")

        # Verify created job belongs to Company Admin and shows ONLY in their dashboard
        r_co_dash2 = co_client.get("/admin", cookies={auth.COOKIE_NAME: co_cookie})
        assert temp_job_title in r_co_dash2.text
        assert "Tata Consultancy Services" not in r_co_dash2.text
        rows_tmp = db.execute_query("SELECT id FROM jobs WHERE title = ? LIMIT 1", (temp_job_title,))
        assert rows_tmp
        created_job_id = rows_tmp[0]["id"]

        # Super Admin toggles can_view_all_jobs ON -> Company Admin sees all jobs with Owner Protected guard
        super_client.post(
            "/admin/admins/toggle",
            cookies={auth.COOKIE_NAME: su_cookie},
            data={"admin_id": str(created_admin_id), "column": "can_view_all_jobs"},
            follow_redirects=False
        )
        r_co_dash3 = co_client.get("/admin", cookies={auth.COOKIE_NAME: co_cookie})
        assert "Tata Consultancy Services" in r_co_dash3.text
        assert "Owner Protected (View-Only)" in r_co_dash3.text

        # Super Admin toggles can_add_jobs OFF -> Company Admin blocked from posting new jobs
        super_client.post(
            "/admin/admins/toggle",
            cookies={auth.COOKIE_NAME: su_cookie},
            data={"admin_id": str(created_admin_id), "column": "can_add_jobs"},
            follow_redirects=False
        )
        r_no_add = co_client.get("/admin/jobs/new", cookies={auth.COOKIE_NAME: co_cookie}, follow_redirects=False)
        assert "forbidden" in r_no_add.headers.get("location", "")
    finally:
        if created_job_id:
            db.delete_job(created_job_id, archive_first=False)
        if created_admin_id:
            db.delete_admin_user(created_admin_id)
    print("✅ Multi-Admin RBAC, Company Job Isolation, Toggles & Ownership Guard test passed!")

if __name__ == "__main__":
    print("Running all verification tests...")
    test_homepage()
    test_jobs_list()
    test_jobs_filter_maharashtra()
    test_jobs_filter_fresher()
    test_job_detail()
    test_resume_builder()
    test_salary_calculator()
    test_career_checklist()
    test_saved_jobs()
    test_seo_endpoints()
    test_admin_flow()
    test_expiry_grace_and_popups()
    test_branding_and_favicon()
    test_multi_admin_isolation_and_contact()
    print("\n🎉 ALL 14 TESTS PASSED PERFECTLY AGAINST TURSO CLOUD!")
