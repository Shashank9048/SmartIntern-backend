import google.generativeai as genai
import os
import json

# Configure Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

async def get_gemini_response(prompt: str):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return str(e)

async def analyze_resume_ai(resume_text: str, job_desc: str):
    prompt = f"""
    Act as an ATS Scanner. Compare this Resume and Job Description (JD).
    Resume: {resume_text[:2000]}...
    JD: {job_desc[:2000]}...
    
    Output ONLY valid JSON format:
    {{
        "match_score": (integer 0-100),
        "missing_keywords": ["list", "of", "missing", "skills"],
        "advice": "1 sentence advice"
    }}
    """
    raw_text = await get_gemini_response(prompt)
    # Cleanup JSON (remove markdown ticks)
    clean_json = raw_text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(clean_json)
    except:
        return {"match_score": 0, "missing_keywords": [], "advice": "Error parsing AI response"}

async def generate_cold_email_ai(job_desc: str, user_role: str = "Developer"):
    prompt = f"""
    Write a professional, concise cold email to a recruiter for this Job Description.
    My Role: {user_role}
    Job Description: {job_desc}
    
    Output ONLY the email body text. No subject line placeholders.
    """
    return await get_gemini_response(prompt)

async def chat_with_gemini(message: str, context: str = ""):
    """
    General AI Assistant Chat. 
    """
    system_instruction = "You are a helpful Career Coach assistant named 'SmartIntern'."
    
    prompt = f"""
    {system_instruction}
    Context: {context}
    
    User: {message}
    Assistant:
    """
    return await get_gemini_response(prompt)