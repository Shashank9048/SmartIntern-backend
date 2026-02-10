from beanie import Document
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# --- AUTH MODELS ---
class User(Document):
    email: EmailStr
    hashed_password: str
    created_at: datetime = datetime.now()

    class Settings:
        name = "users"

class UserAuth(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# --- APPLICATION MODELS ---
class Application(Document):
    user_email: str  # Link app to specific user
    company: str
    role: str
    status: str = "Applied"  # Applied, Interview, Offer, Rejected
    applied_date: datetime = datetime.now()
    job_description: Optional[str] = None
    resume_text: Optional[str] = None
    match_score: int = 0
    missing_keywords: List[str] = []
    
    # Reminder System
    next_action_date: Optional[datetime] = None  # e.g., Interview Date
    reminder_note: Optional[str] = None

    class Settings:
        name = "applications"