from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import asyncio
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Import our logic
from agent_logic import run_agent_cycle

app = FastAPI(title="Email Agent Backend")

# CORS for Chrome Extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to extension ID
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock Database (JSON file)
DB_FILE = "users.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Models
class LoginRequest(BaseModel):
    email: str
    app_password: str
    openrouter_key: str
    interval: int = 30  # Default 30 min

class ToggleRequest(BaseModel):
    email: str
    active: bool

class SettingsRequest(BaseModel):
    email: str
    interval: int

# Scheduler
scheduler = AsyncIOScheduler()

async def active_user_job():
    """Runs every 1 minute to check for users needing updates."""
    db = load_db()
    now = datetime.datetime.now()
    updated = False
    
    for email, user in db.items():
        if not user.get("active", False):
            continue
            
        last_str = user.get("last_run")
        interval = user.get("interval_minutes", 30)
        
        should_run = False
        if not last_str:
            should_run = True # First run
        else:
            last_run = datetime.datetime.fromisoformat(last_str)
            next_run_time = last_run + datetime.timedelta(minutes=interval)
            if now >= next_run_time:
                should_run = True
                
        if should_run:
            print(f"🔄 Processing for {email}...")
            try:
                # Run in thread pool
                logs, timestamp = await asyncio.to_thread(
                    run_agent_cycle, 
                    user['email'], 
                    user['app_password'], 
                    user['openrouter_key']
                )
                print(f"✅ Finished {email}: {len(logs)} actions.")
                user["last_run"] = timestamp
                updated = True
            except Exception as e:
                print(f"❌ Error user {email}: {e}")

    if updated:
        save_db(db)

@app.on_event("startup")
def start_scheduler():
    # Run loop often to check various user schedules
    scheduler.add_job(active_user_job, IntervalTrigger(minutes=1))
    scheduler.start()
    print("⏰ Scheduler started (1 min check loop)")

@app.post("/login")
async def login(req: LoginRequest):
    print(f"🔐 Attempting Login: {req.email} | Pass Length: {len(req.app_password)}")
    # Test credentials by trying to login
    try:
        from imap_tools import MailBox
        with MailBox("imap.gmail.com").login(req.email, req.app_password):
            pass # Success
    except Exception as e:
        print(f"❌ Login failed: {e}")
        raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")

    # Save to "Database"
    db = load_db()
    
    # Preserve existing settings if re-logging in
    existing = db.get(req.email, {})
    
    db[req.email] = {
        "email": req.email,
        "app_password": req.app_password,
        "openrouter_key": req.openrouter_key,
        "active": True,
        "interval_minutes": req.interval,
        "last_run": existing.get("last_run")
    }
    save_db(db)
    
    # Trigger an immediate run in background if never run
    if not existing.get("last_run"):
        await active_user_job()
    
    return {"status": "success", "message": "Logged in and Agent Started"}

@app.post("/settings")
async def update_settings(req: SettingsRequest):
    db = load_db()
    if req.email not in db:
        raise HTTPException(status_code=404, detail="User not found")
    
    db[req.email]["interval_minutes"] = req.interval
    save_db(db)
    return {"status": "updated", "interval": req.interval}

@app.post("/status")
async def get_status(email: str):
    db = load_db()
    user = db.get(email)
    if not user:
        return {"active": False}
    
    # Calculate next run
    last_run_str = user.get("last_run")
    next_run_str = "Pending..."
    if last_run_str:
        last_dt = datetime.datetime.fromisoformat(last_run_str)
        interval = user.get("interval_minutes", 30)
        next_dt = last_dt + datetime.timedelta(minutes=interval)
        
        # Friendly format
        delta = next_dt - datetime.datetime.now()
        minutes_left = int(delta.total_seconds() / 60)
        
        if minutes_left <= 0:
            next_run_str = "Now/Soon"
        else:
            next_run_str = f"in {minutes_left} mins"

    return {
        "active": user.get("active", False),
        "last_run": last_run_str,
        "next_run": next_run_str,
        "interval": user.get("interval_minutes", 30)
    }

@app.post("/toggle")
async def toggle_agent(req: ToggleRequest):
    db = load_db()
    if req.email not in db:
        raise HTTPException(status_code=404, detail="User not found")
    
    db[req.email]["active"] = req.active
    save_db(db)
    return {"status": "updated", "active": req.active}

@app.get("/")
def home():
    return {"message": "Email Agent API Running"}
