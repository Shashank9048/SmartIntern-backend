from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os

app = FastAPI()

# 1. CORS Setup (Essential for Frontend connection)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (v0, localhost, vercel)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Database Connection
# We use "get" so it returns None if missing, preventing immediate crash
MONGO_URL = os.getenv("MONGODB_URL")

# Only connect if URL exists (prevents build errors during deployment checks)
if MONGO_URL:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["jobtracker"] # Your actual DB name
else:
    db = None
    print("⚠️ WARNING: MONGODB_URL not found in environment variables")

# 3. Health Check Endpoint
@app.get("/")
async def root():
    return {"status": "Backend is running!", "database": "Connected" if db is not None else "Disconnected"}

# 4. Your API Endpoint
@app.get("/api/test")
async def test_db():
    if not db:
        return {"error": "Database not connected"}
    
    # Try fetching one document to prove connection works
    # Replace 'applications' with your actual collection name
    data = await db["applications"].find_one()
    return {"message": "Database access successful", "sample_data": str(data)}