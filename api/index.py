from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, PydanticObjectId
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os

# --- SAFE IMPORTS (Fixes Vercel 500 Error) ---
try:
    # Try relative imports (Works locally)
    from .models import Application, User, UserAuth, Token
    from .auth import get_password_hash, verify_password, create_access_token, get_current_user
    from .ai_utils import analyze_resume_ai, generate_cold_email_ai, chat_with_gemini
except ImportError:
    # Try absolute imports (Works on Vercel)
    from api.models import Application, User, UserAuth, Token
    from api.auth import get_password_hash, verify_password, create_access_token, get_current_user
    from api.ai_utils import analyze_resume_ai, generate_cold_email_ai, chat_with_gemini

# --- LIFESPAN (Database Connection) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_url = os.environ.get("MONGODB_URL")
    if mongo_url:
        try:
            client = AsyncIOMotorClient(mongo_url)
            # Initialize Beanie with all models
            await init_beanie(database=client["smart_intern_tracker"], document_models=[Application, User])
            print("✅ Database Connected")
        except Exception as e:
            print(f"❌ Database Connection Error: {e}")
    else:
        print("⚠️ WARNING: MONGODB_URL not found")
    yield

app = FastAPI(lifespan=lifespan)

# --- CORS (Allow Frontend Access) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow Vercel/v0 frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTES ---

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Backend is running!"}

# 1. AUTHENTICATION
@app.post("/api/auth/signup")
async def signup(user_data: UserAuth):
    try:
        existing_user = await User.find_one(User.email == user_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_pw = get_password_hash(user_data.password)
        new_user = User(email=user_data.email, hashed_password=hashed_pw)
        await new_user.insert()
        return {"message": "User created"}
    except Exception as e:
        print(f"Signup Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login", response_model=Token)
async def login(user_data: UserAuth):
    user = await User.find_one(User.email == user_data.email)
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# 2. APPLICATIONS CRUD (Protected)
@app.get("/api/applications")
async def get_apps(current_user: str = Depends(get_current_user)):
    return await Application.find(Application.user_email == current_user).to_list()

@app.post("/api/applications")
async def create_app(app_data: Application, current_user: str = Depends(get_current_user)):
    app_data.user_email = current_user 
    await app_data.insert()
    return app_data

@app.delete("/api/applications/{id}")
async def delete_app(id: PydanticObjectId, current_user: str = Depends(get_current_user)):
    app = await Application.get(id)
    if app and app.user_email == current_user:
        await app.delete()
        return {"message": "Deleted"}
    raise HTTPException(404, "Not found")

@app.patch("/api/applications/{id}")
async def update_status(id: PydanticObjectId, status: str, current_user: str = Depends(get_current_user)):
    app = await Application.get(id)
    if app and app.user_email == current_user:
        app.status = status
        await app.save()
        return app
    raise HTTPException(404, "Not found")

# 3. AI FEATURES
class AnalyzeRequest(BaseModel):
    resume_text: str
    job_description: str

@app.post("/api/ai/analyze")
async def ai_analyze(req: AnalyzeRequest, current_user: str = Depends(get_current_user)):
    analysis = await analyze_resume_ai(req.resume_text, req.job_description)
    return analysis

class EmailRequest(BaseModel):
    job_description: str

@app.post("/api/ai/cold-email")
async def ai_email(req: EmailRequest, current_user: str = Depends(get_current_user)):
    email_body = await generate_cold_email_ai(req.job_description)
    return {"email": email_body}

# 4. CHAT ASSISTANT
class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = ""

@app.post("/api/ai/chat")
async def ai_chat(req: ChatRequest, current_user: str = Depends(get_current_user)):
    response = await chat_with_gemini(req.message, context=req.context)
    return {"reply": response}

# 5. SMART AUTOMATION
@app.get("/api/automation/run")
async def run_automation(current_user: str = Depends(get_current_user)):
    apps = await Application.find(Application.user_email == current_user).to_list()
    notifications = []
    today = datetime.now()
    
    for app in apps:
        if app.next_action_date:
            diff = (app.next_action_date - today).total_seconds() / 3600
            if 0 < diff < 24:
                notifications.append({
                    "id": str(app.id),
                    "type": "alert",
                    "message": f"🚀 Good luck! Interview with {app.company} is tomorrow!"
                })

        days_since_applied = (today - app.applied_date).days
        if app.status == "Applied" and days_since_applied > 14:
             notifications.append({
                 "id": str(app.id),
                 "type": "info",
                 "message": f"💤 No news from {app.company} in 2 weeks. Time to follow up?"
             })

    return {"notifications": notifications}
