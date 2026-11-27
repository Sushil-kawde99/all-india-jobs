import sys
from config import TURSO_DATABASE_URL, TURSO_AUTH_TOKEN
import db

def main():
    print("==================================================")
    print("   JOBDISHA INDIA - TURSO DATABASE CONNECTION TEST")
    print("==================================================")
    print(f"\n1. Database URL: {TURSO_DATABASE_URL}")

    token_display = f"{TURSO_AUTH_TOKEN[:10]}...{TURSO_AUTH_TOKEN[-6:]}" if len(TURSO_AUTH_TOKEN) > 20 else "(Not configured yet)"
    print(f"2. Auth Token:   {token_display}")

    if not TURSO_AUTH_TOKEN or len(TURSO_AUTH_TOKEN.strip()) < 20:
        print("\n⚠️  TURSO AUTH TOKEN PENDING:")
        print("   - Go to your Turso Cloud Dashboard (as in your screenshot)")
        print("   - Click the '+ Create Token' button")
        print("   - Copy the token and paste it in: jobdisha-india-fastapi/.env")
        print("     TURSO_AUTH_TOKEN=your_token_here")
        print("\n   [Note] Currently running with local SQLite fallback store so the website works immediately!")
    else:
        print("\n⏳ Testing connection to Turso Cloud...")
        try:
            connected = db.is_turso_connected()
            if connected:
                print("✅ SUCCESS! Connected to Turso Cloud: my-portfolio-db")
                stats = db.get_job_stats()
                print(f"   - Total Vacancies in Cloud DB: {stats['totalJobs']}")
                print(f"   - Active Jobs: {stats['activeJobs']}")
                print(f"   - Government Jobs: {stats['governmentJobs']}")
            else:
                print("❌ Could not connect to Turso. Please verify your token has read/write permissions.")
        except Exception as e:
            print(f"❌ Connection error: {e}")

    print("\n--------------------------------------------------")
    stats = db.get_job_stats()
    print(f"Database Stats (Total: {stats['totalJobs']} jobs across {stats['statesCovered']} states):")
    jobs = db.get_jobs(limit=5)
    for j in jobs["data"]:
        print(f"  • [{j['id']}] {j['title']} at {j['company']} ({j['city']}, {j['state']})")
    print("==================================================\n")

if __name__ == "__main__":
    main()

