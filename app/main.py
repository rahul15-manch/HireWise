from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, File, UploadFile
import shutil
import uuid
import base64
import json
from pypdf import PdfReader
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app import models, database
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from datetime import datetime, timedelta
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

# Database Setup
try:
    models.Base.metadata.create_all(bind=database.engine)
    
    # Simple auto-migrations for newly added columns
    from sqlalchemy import text
    with database.engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE interviews ADD COLUMN is_published BOOLEAN DEFAULT FALSE;"))
        except Exception:
            pass # Column likely already exists
        try:
            conn.execute(text("ALTER TABLE interviews ADD COLUMN hints_used INTEGER DEFAULT 0;"))
        except Exception:
            pass # Column likely already exists
except Exception as e:
    print(f"Database setup error: {e}")

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

# Add Middleware for reverse proxies (Vercel) to fix HTTPS scheme detection
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

# Check if we are in a production environment (like Vercel)
is_production = os.getenv("VERCEL") == "1" or os.getenv("RENDER") == "1"

# Add SessionMiddleware for OAuth with secure cookies in production
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("SECRET_KEY", "supersecretkey"),
    https_only=is_production
)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# OAuth Configuration
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_current_user(request: Request, db: Session = Depends(database.get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request, "landing.html")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(request, "login.html", {"error": "Invalid credentials"})
    
    # Successful Login (Redirect to Dashboard placeholder)
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="user_email", value=user.email, httponly=True)
    return response

@app.get("/auth/google/login")
async def google_login(request: Request):
    # Use the configured redirect URI from .env if available
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    
    # Support local development (HTTP)
    is_local = "localhost" in str(request.base_url) or "127.0.0.1" in str(request.base_url)
    
    if is_local:
        os.environ['AUTHLIB_INSECURE_TRANSPORT'] = 'true'
        # Force local callback for local dev regardless of .env or request host detection issues
        redirect_uri = str(request.url_for('auth_google_callback'))
        if "https://" in redirect_uri:
            redirect_uri = redirect_uri.replace("https://", "http://")
    elif not redirect_uri:
        redirect_uri = request.url_for('auth_google_callback')

    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google/callback")
async def auth_google_callback(request: Request, db: Session = Depends(database.get_db)):
    code = request.query_params.get("code")
    if not code:
        return RedirectResponse(url="/login?error=No+code+provided")

    try:
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        if not redirect_uri:
            redirect_uri = str(request.url_for('auth_google_callback'))
            if "localhost" not in redirect_uri and "127.0.0.1" not in redirect_uri and "http://" in redirect_uri:
                redirect_uri = redirect_uri.replace("http://", "https://")

        # Manually exchange code for token (Stateless, ignores session cookies)
        import httpx
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri
                }
            )
            token_data = token_resp.json()
            if "access_token" not in token_data:
                raise Exception(f"Token error: {token_data}")

            user_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            user_info = user_resp.json()
            
        if not user_info:
            return RedirectResponse(url="/login?error=Failed+to+get+user+info")

        email = user_info.get('email').lower()
        full_name = user_info.get('name')

        # Check if user exists
        user = db.query(models.User).filter(models.User.email == email).first()

        # If user exists, log them in
        if user:
            response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
            response.set_cookie(key="user_email", value=email, httponly=True)
            return response

        # New user: store info in session and redirect to role selection
        request.session['google_user'] = {
            'email': email,
            'name': full_name
        }
        return RedirectResponse(url="/auth/google/role-selection", status_code=status.HTTP_303_SEE_OTHER)
            
    except Exception as e:
        print(f"OAuth/DB Error: {e}")
        import traceback
        traceback.print_exc()
        import urllib.parse
        error_msg = urllib.parse.quote(str(e))
        return RedirectResponse(url=f"/login?error=Callback+Failed:+{error_msg}")

@app.get("/auth/google/role-selection", response_class=HTMLResponse)
async def google_role_selection(request: Request):
    if 'google_user' not in request.session:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request, "role_selection.html")

@app.post("/auth/google/complete")
async def google_auth_complete(request: Request, role: str = Form(...), db: Session = Depends(database.get_db)):
    google_user = request.session.get('google_user')
    if not google_user:
        return RedirectResponse(url="/login?error=Session+expired")

    email = google_user['email'].lower()
    name = google_user['name']

    # Final check just in case
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(
            email=email,
            full_name=name,
            hashed_password=None, # OAuth user
            role=role.lower() # recruiter or candidate
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Clear temp session
    request.session.pop('google_user', None)

    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="user_email", value=email, httponly=True)
    return response

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse(request, "signup.html")

@app.post("/signup")
async def signup(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(database.get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        return templates.TemplateResponse(request, "signup.html", {"error": "Email already registered"})
    
    hashed_password = get_password_hash(password)
    new_user = models.User(full_name=full_name, email=email, hashed_password=hashed_password, role=role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(database.get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login")
    
    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user:
        response = RedirectResponse(url="/login")
        response.delete_cookie("user_email")
        return response

    interviews = []
    stats = {}
    if user.role == "recruiter":
        interviews = db.query(models.Interview).filter(models.Interview.recruiter_id == user.id).all()
        # Ensure candidate details are loaded
        for iv in interviews:
             iv.candidate = db.query(models.User).filter(models.User.id == iv.candidate_id).first()
             iv.candidate_name = iv.candidate.full_name if iv.candidate else "Unknown"

        stats = {
            "total": len(interviews),
            "screening": len([i for i in interviews if i.status == "completed"]),
            "shortlisted": len([i for i in interviews if i.status == "cleared"]),
            "rejected": len([i for i in interviews if i.status == "rejected"]),
            "pipeline": {
                "Applied": [i for i in interviews if i.status == "pending"],
                "Screening": [i for i in interviews if i.status == "completed"],
                "Shortlisted": [i for i in interviews if i.status == "cleared"],
                "Rejected": [i for i in interviews if i.status == "rejected"],
            }
        }
    else:
        interviews = db.query(models.Interview).filter(models.Interview.candidate_id == user.id).all()
        # Populate recruiter details for each interview
        for iv in interviews:
            if iv.recruiter_id:
                iv.recruiter = db.query(models.User).filter(models.User.id == iv.recruiter_id).first()
        
        # Calculate readiness score (average of non-zero scores)
        scores = []
        for i in interviews:
            if i.evaluation:
                try:
                    eval_data = json.loads(i.evaluation)
                    if eval_data.get("score"):
                        scores.append(eval_data["score"])
                except:
                    continue
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Aggregate skills from evaluation strengths
        skills = {}
        for i in interviews:
            if i.evaluation:
                try:
                    eval_data = json.loads(i.evaluation)
                    for s in eval_data.get("strengths", []):
                        skills[s] = skills.get(s, 0) + 1
                except:
                    continue
        
        # Calculate streak and graph data
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=29)
        
        # Initialize counts for each of the last 30 days
        streak_counts = {}
        for i in range(30):
            day = (thirty_days_ago + timedelta(days=i)).strftime("%Y-%m-%d")
            streak_counts[day] = 0
            
        for iv in interviews:
            if iv.created_at:
                day_str = iv.created_at.strftime("%Y-%m-%d")
                if day_str in streak_counts:
                    streak_counts[day_str] += 1
        
        # Sorted list of counts with dates (oldest first)
        streak_graph_data = [{"date": day, "count": streak_counts[day]} for day in sorted(streak_counts.keys())]
        
        # Calculate consecutive streak (days with >= 1 interview)
        current_streak = 0
        check_date = now
        while True:
            date_str = check_date.strftime("%Y-%m-%d")
            if streak_counts.get(date_str, 0) > 0:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                # If today has no interviews, check if yesterday had any (streak might still be alive)
                if date_str == now.strftime("%Y-%m-%d"):
                    check_date -= timedelta(days=1)
                    continue
                break

        stats = {
            "readiness_score": int(avg_score),
            "total_interviews": len(interviews),
            "cleared": len([i for i in interviews if i.status == "cleared"]),
            "skills": sorted(skills.items(), key=lambda x: x[1], reverse=True)[:5],
            "streak": current_streak,
            "streak_graph": streak_graph_data
        }

    msg = request.query_params.get("msg")
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user, 
        "interviews": interviews, 
        "stats": stats,
        "msg": msg, 
        "json": json,
        "datetime": datetime,
        "timedelta": timedelta
    })

import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
from groq import AsyncGroq

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

async def generate_ai_questions(job_role: str, difficulty: str, resume_text: str = None, provide_hints: bool = False, custom_prompt: str = None):
    try:
        if custom_prompt and custom_prompt.strip():
            system_content = (
                "You are HireWise Interview Intelligence Engine.\n\n"
                "The recruiter has provided CUSTOM INSTRUCTIONS for this interview. You MUST follow them strictly and design the interview exactly as requested below:\n\n"
                f"--- RECRUITER INSTRUCTIONS ---\n"
                f"{custom_prompt}\n"
                f"------------------------------\n\n"
                "--------------------------------------------------\n"
                "OUTPUT FORMAT\n"
                "--------------------------------------------------\n\n"
                "Return ONLY valid JSON.\n\n"
                "{\n"
                "  \"candidate_summary\": \"...\",\n"
                "  \"recommended_question_count\": 7,\n"
                "  \"interview_sections\": [\n"
                "    {\n"
                "      \"section\": \"Candidate Discovery\",\n"
                "      \"questions\": [...]\n"
                "    },\n"
                "    {\n"
                "      \"section\": \"Technical Assessment\",\n"
                "      \"questions\": [\n"
                "        {\n"
                "          \"type\": \"dsa\",\n"
                "          \"title\": \"...\",\n"
                "          \"problem_statement\": \"...\",\n"
                "          \"input_format\": \"...\",\n"
                "          \"output_format\": \"...\",\n"
                "          \"constraints\": \"...\",\n"
                "          \"starter_code\": {\"python\": \"def solve(...):\\n    pass\", \"javascript\": \"function solve(...) {\\n    \\n}\"},\n"
                "          \"visible_test_cases\": [{\"input\": \"...\", \"python_test\": \"print(solve(...))\", \"javascript_test\": \"console.log(solve(...));\", \"expected_output\": \"...\"}],\n"
                "          \"hidden_test_cases\": [{\"input\": \"...\", \"python_test\": \"print(solve(...))\", \"javascript_test\": \"console.log(solve(...));\", \"expected_output\": \"...\"}],\n"
                "          \"difficulty\": \"Easy/Medium/Hard\"\n"
                "        }\n"
                "      ]\n"
                "    }\n"
                "  ]\n"
                "}"
            )
        else:
            system_content = (
                        "You are HireWise Interview Intelligence Engine.\n\n"
                        "You are a world-class interviewer trained on hiring practices from FAANG companies, startups, enterprise organizations, consulting firms, product companies, sales organizations, and HR leadership teams.\n\n"
                        "Your job is NOT merely to generate interview questions.\n\n"
                        "Your job is to design a complete interview experience that helps recruiters evaluate:\n\n"
                        "1. Communication Skills\n"
                        "2. Resume Authenticity\n"
                        "3. Technical Depth\n"
                        "4. Problem Solving Ability\n"
                        "5. Decision Making\n"
                        "6. Leadership Potential\n"
                        "7. Collaboration Skills\n"
                        "8. Learning Mindset\n"
                        "9. Domain Expertise\n"
                        "10. Culture Fit\n\n"
                        "--------------------------------------------------\n"
                        "INTERVIEW GENERATION RULES\n"
                        "--------------------------------------------------\n\n"
                        "The number of questions MUST be dynamic.\n\n"
                        "Decide the number of questions based on:\n\n"
                        "- Role complexity\n"
                        "- Resume richness\n"
                        "- Experience level\n"
                        "- Difficulty level\n\n"
                        "Examples:\n\n"
                        "Intern:\n"
                        "4-6 Questions\n\n"
                        "Junior:\n"
                        "5-7 Questions\n\n"
                        "Mid-Level:\n"
                        "6-8 Questions\n\n"
                        "Senior:\n"
                        "7-9 Questions\n\n"
                        "Leadership:\n"
                        "8-10 Questions\n\n"
                        "Never generate a fixed number. Keep descriptions very concise.\n\n"
                        "--------------------------------------------------\n"
                        "MANDATORY INTERVIEW SECTIONS\n"
                        "--------------------------------------------------\n\n"
                        "Every interview MUST include:\n\n"
                        "SECTION A: Candidate Discovery\n"
                        "(2-4 questions)\n\n"
                        "Examples:\n"
                        "- Introduce yourself without repeating your resume.\n"
                        "- Tell me something important about you that is not mentioned in your resume.\n"
                        "- What motivates you professionally?\n"
                        "- What are your strengths and areas you are currently improving?\n\n"
                        "SECTION B: Resume Validation\n"
                        "(2-5 questions)\n\n"
                        "For every major project, internship, achievement, or tool mentioned:\n\n"
                        "Ask:\n"
                        "- Why was this project built?\n"
                        "- What challenge did you personally solve?\n"
                        "- What would you redesign today?\n"
                        "- What tradeoffs were made?\n\n"
                        "SECTION C: Role-Specific Evaluation\n"
                        "(Dynamic)\n\n"
                        "Questions must align to role.\n\n"
                        "--------------------------------------------------\n"
                        "TECHNICAL ROLE RULES\n"
                        "--------------------------------------------------\n\n"
                        "Examples:\n"
                        "Software Engineer\n"
                        "ML Engineer\n"
                        "AI Engineer\n"
                        "Data Scientist\n"
                        "Backend Engineer\n"
                        "Frontend Engineer\n"
                        "Full Stack Engineer\n\n"
                        "Question Mix:\n\n"
                        "- Conceptual Questions\n"
                        "- Practical Engineering Questions\n"
                        "- Real World Scenarios\n"
                        "- Debugging Questions\n"
                        "- Architecture Questions\n"
                        "- DSA Questions\n"
                        "- Behavioral Questions\n\n"
                        "MANDATORY:\n\n"
                        "At least 1 DSA question.\n\n"
                        "DSA Question Format:\n\n"
                        "{\n"
                        "  \"type\": \"dsa\",\n"
                        "  \"title\": \"...\",\n"
                        "  \"problem_statement\": \"...\",\n"
                        "  \"input_format\": \"...\",\n"
                        "  \"output_format\": \"...\",\n"
                        "  \"constraints\": \"...\",\n"
                        "  \"starter_code\": {\n"
                        "    \"python\": \"def solve(...):\\n    pass\",\n"
                        "    \"javascript\": \"function solve(...) {\\n    \\n}\"\n"
                        "  },\n"
                        "  \"visible_test_cases\": [\n"
                        "    {\"input\": \"...\", \"python_test\": \"print(solve(...))\", \"javascript_test\": \"console.log(solve(...));\", \"expected_output\": \"...\"}\n"
                        "  ],\n"
                        "  \"hidden_test_cases\": [\n"
                        "    {\"input\": \"...\", \"python_test\": \"print(solve(...))\", \"javascript_test\": \"console.log(solve(...));\", \"expected_output\": \"...\"}\n"
                        "  ],\n"
                        "  \"expected_approach\": \"...\",\n"
                        "  \"difficulty\": \"Easy/Medium/Hard\"\n"
                        "}\n\n"
                        "--------------------------------------------------\n"
                        "ML / AI SPECIFIC RULES\n"
                        "--------------------------------------------------\n\n"
                        "For AI/ML roles include:\n\n"
                        "- Model Selection\n"
                        "- Feature Engineering\n"
                        "- Evaluation Metrics\n"
                        "- Deployment\n"
                        "- MLOps\n"
                        "- LLMs\n"
                        "- Vector Databases\n"
                        "- RAG Systems\n"
                        "- Fine-Tuning\n"
                        "- Prompt Engineering\n"
                        "- AI System Design\n\n"
                        "Scenario questions MUST include context.\n\n"
                        "Bad:\n\n"
                        "\"Design a neural network.\"\n\n"
                        "Good:\n\n"
                        "\"You are building a resume screening model for 500,000 applicants. Dataset contains 120 features, 20% missing values and severe class imbalance. How would you approach feature engineering, model selection, validation, and deployment?\"\n\n"
                        "Every scenario should provide enough context for the candidate to reason.\n\n"
                        "--------------------------------------------------\n"
                        "PRODUCT ROLES\n"
                        "--------------------------------------------------\n\n"
                        "Include:\n\n"
                        "- Product Design\n"
                        "- Prioritization\n"
                        "- Metrics\n"
                        "- User Research\n"
                        "- Stakeholder Management\n"
                        "- Tradeoffs\n\n"
                        "--------------------------------------------------\n"
                        "SALES ROLES\n"
                        "--------------------------------------------------\n\n"
                        "Include:\n\n"
                        "- Discovery Calls\n"
                        "- Objection Handling\n"
                        "- Closing Strategy\n"
                        "- Pipeline Management\n"
                        "- Revenue Growth\n\n"
                        "Never include coding.\n\n"
                        "--------------------------------------------------\n"
                        "HR / MANAGEMENT ROLES\n"
                        "--------------------------------------------------\n\n"
                        "Include:\n\n"
                        "- Conflict Resolution\n"
                        "- Hiring Decisions\n"
                        "- Leadership\n"
                        "- Coaching\n"
                        "- Team Performance\n"
                        "- Difficult Conversations\n\n"
                        "Never include coding.\n\n"
                        "--------------------------------------------------\n"
                        "QUESTION QUALITY RULES\n"
                        "--------------------------------------------------\n\n"
                        "Questions should:\n\n"
                        "- Feel realistic\n"
                        "- Reflect 2025+ interviews\n"
                        "- Avoid textbook definitions\n"
                        "- Test reasoning\n"
                        "- Increase in difficulty gradually\n"
                        "- Be role specific\n"
                        "- Be resume aware\n\n"
                        "--------------------------------------------------\n"
                        "RECRUITER HINTS\n"
                        "--------------------------------------------------\n\n"
                        "For every technical or scenario question provide interviewer guidance.\n\n"
                        "Example:\n\n"
                        "{\n"
                        "  \"question\": \"...\",\n"
                        "  \"evaluation_points\": [\n"
                        "    \"...\",\n"
                        "    \"...\",\n"
                        "    \"...\"\n"
                        "  ],\n"
                        "  \"red_flags\": [\n"
                        "    \"...\",\n"
                        "    \"...\"\n"
                        "  ]\n"
                        "}\n\n"
                        "These hints help recruiters evaluate answers consistently.\n\n"
                        "--------------------------------------------------\n"
                        "OUTPUT FORMAT\n"
                        "--------------------------------------------------\n\n"
                        "Return ONLY valid JSON.\n\n"
                        "{\n"
                        "  \"candidate_summary\": \"...\",\n"
                        "  \"recommended_question_count\": 14,\n"
                        "  \"interview_sections\": [\n"
                        "    {\n"
                        "      \"section\": \"Candidate Discovery\",\n"
                        "      \"questions\": [...]\n"
                        "    },\n"
                        "    {\n"
                        "      \"section\": \"Resume Validation\",\n"
                        "      \"questions\": [...]\n"
                        "    },\n"
                        "    {\n"
                        "      \"section\": \"Technical Assessment\",\n"
                        "      \"questions\": [...]\n"
                        "    },\n"
                        "    {\n"
                        "      \"section\": \"Behavioral Assessment\",\n"
                        "      \"questions\": [...]\n"
                        "    }\n"
                        "  ]\n"
                        "}"
                    )
        
        chat = await groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_content
                },
                {
                    "role": "user",
                    "content": (
                        f"Job Role: {job_role}\n"
                        f"Difficulty: {difficulty}\n\n"
                        f"Resume:\n"
                        f"{resume_text[:4000] if resume_text else 'No resume provided.'}\n\n"
                        f"{'CRITICAL REQUIREMENT: The recruiter has requested HINTS. For EVERY question you generate, you MUST include a `candidate_hint` field with a helpful guiding hint.' if provide_hints else ''}\n"
                        "Please generate the interview following the exact rules and JSON format specified."
                    )
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=6500,
            response_format={"type": "json_object"}
        )
        result = json.loads(chat.choices[0].message.content)
        
        # Extract the rich questions from the sections
        rich_questions = []
        sections = result.get("interview_sections", [])
        for sec in sections:
            for q in sec.get("questions", []):
                # Ensure the section name is passed down for context if we want it
                if isinstance(q, dict):
                    q["_section"] = sec.get("section", "")
                    rich_questions.append(q)
                elif isinstance(q, str):
                    rich_questions.append({"question": q, "_section": sec.get("section", "")})
                    
        return rich_questions, result.get("candidate_summary", "")
    except Exception as e:
        print(f"Groq Question Generation Error: {e}")
        fallback_questions = [
            f"Walk me through how you would design a scalable {job_role} system from scratch.",
            f"Describe a challenging bug you encountered in a {difficulty}-level project. How did you debug it?",
            f"What are the key performance trade-offs you consider when working as a {job_role}?",
            "How do you ensure code quality in a fast-moving team?",
            "Tell me about a time you had to learn a new technology under time pressure.",
        ]
        return fallback_questions, None

@app.post("/interviews/create")
async def create_interview(
    request: Request,
    candidate_email: str = Form(...),
    job_role: str = Form(...),
    difficulty: str = Form(...),
    generate_ai: bool = Form(False),
    provide_hints: bool = Form(False),
    manual_questions: str = Form(None),
    custom_prompt: str = Form(None),
    pdf_file: UploadFile = File(None),
    resume_file: UploadFile = File(None),
    db: Session = Depends(database.get_db)
):
    user_email = request.cookies.get("user_email")
    recruiter = db.query(models.User).filter(models.User.email == user_email).first()
    
    if not recruiter or recruiter.role != "recruiter":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER) # Unauthorized

    candidate = db.query(models.User).filter(models.User.email == candidate_email, models.User.role == "candidate").first()
    if not candidate:
        return RedirectResponse(url="/dashboard?msg=Candidate+not+found", status_code=status.HTTP_303_SEE_OTHER)

    questions_list = []
    resume_text = ""
    saved_resume_filename = None

    # Handle Resume Upload and Text Extraction
    if resume_file and resume_file.filename:
        upload_dir = os.path.join("/tmp", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        file_ext = os.path.splitext(resume_file.filename)[1]
        saved_resume_filename = f"resume_{uuid.uuid4()}{file_ext}"
        resume_path = os.path.join(upload_dir, saved_resume_filename)
        
        with open(resume_path, "wb") as buffer:
            shutil.copyfileobj(resume_file.file, buffer)
        
        try:
            reader = PdfReader(resume_path)
            for page in reader.pages:
                resume_text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Resume Extraction Error: {e}")

    if generate_ai:
        questions_list, candidate_summary = await generate_ai_questions(job_role, difficulty, resume_text, provide_hints, custom_prompt)

    elif manual_questions:
        questions_list = [q.strip() for q in manual_questions.split('\n') if q.strip()]
    
    saved_pdf_filename = None
    if pdf_file and pdf_file.filename:
        # Ensure uploads directory exists
        upload_dir = os.path.join("/tmp", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        file_ext = os.path.splitext(pdf_file.filename)[1]
        saved_pdf_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(upload_dir, saved_pdf_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(pdf_file.file, buffer)
        
        # Extract text and questions from PDF
        try:
            reader = PdfReader(file_path)
            raw_text = ""
            for page in reader.pages:
                raw_text += page.extract_text() + "\n"
            
            if raw_text.strip():
                model = genai.GenerativeModel('gemini-1.5-flash')
                extraction_prompt = f"""
                Extract a JSON list of technical interview questions from the following text extracted from an assessment PDF.
                Ignore instructions, headers, or metadata. Return ONLY a JSON list of strings.
                
                Text:
                {raw_text[:5000]} # Limit text length for safety
                """
                response = model.generate_content(extraction_prompt)
                extracted_text = response.text.strip()
                
                if "```json" in extracted_text:
                    extracted_text = extracted_text.split("```json")[1].split("```")[0].strip()
                elif "```" in extracted_text:
                    extracted_text = extracted_text.split("```")[1].split("```")[0].strip()
                
                extracted_questions = json.loads(extracted_text)
                if isinstance(extracted_questions, list) and len(extracted_questions) > 0:
                    questions_list = extracted_questions
        except Exception as e:
            print(f"PDF Extraction Error: {e}")
            if not questions_list:
                questions_list = ["Could you please go through the uploaded PDF and summarize your understanding?"]

        if not questions_list:
            questions_list = ["Please provide your responses based on the uploaded PDF assessment."]
    
    # Final safety check
    if not questions_list:
        questions_list = ["Tell me about your background and experience."]

    new_interview = models.Interview(
        recruiter_id=recruiter.id,
        candidate_id=candidate.id,
        job_role=job_role,
        difficulty=difficulty,
        questions=json.dumps(questions_list),
        pdf_file=saved_pdf_filename,
        resume_file=saved_resume_filename,
        candidate_summary=vars().get('candidate_summary'),
        status="pending"
    )
    db.add(new_interview)
    db.commit()
    db.refresh(new_interview)
    
    return RedirectResponse(url="/dashboard?msg=Interview+created+successfully", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/interviews/mock")
async def create_mock_interview(
    request: Request,
    job_role: str = Form(...),
    difficulty: str = Form(...),
    db: Session = Depends(database.get_db)
):
    user_email = request.cookies.get("user_email")
    user = db.query(models.User).filter(models.User.email == user_email).first()
    
    if not user or user.role != "candidate":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    # Use system admin as placeholder recruiter for mock interviews
    admin = db.query(models.User).filter(models.User.email == "admin@hirewise.com").first()
    recruiter_id = admin.id if admin else None

    # Generate questions via AI
    questions_list, candidate_summary = await generate_ai_questions(job_role, difficulty)

    new_interview = models.Interview(
        recruiter_id=recruiter_id,
        candidate_id=user.id,
        job_role=job_role,
        difficulty=difficulty,
        questions=json.dumps(questions_list),
        candidate_summary="Practice Mock Interview",
        status="pending",
        is_published=True
    )
    
    db.add(new_interview)
    db.commit()
    db.refresh(new_interview)
    
    return RedirectResponse(url=f"/interview/{new_interview.id}", status_code=status.HTTP_303_SEE_OTHER)
    
@app.post("/interview/{interview_id}/review")
async def review_interview(
    interview_id: int,
    decision: str = Form(...),
    feedback: str = Form(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(get_current_user)
):
    if user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can review interviews")
    
    interview = db.query(models.Interview).filter(
        models.Interview.id == interview_id,
        models.Interview.recruiter_id == user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    if decision == "pass":
        interview.status = "cleared"
    elif decision == "fail":
        interview.status = "rejected"
    
    interview.recruiter_feedback = feedback
    db.commit()
    return RedirectResponse(url="/dashboard?msg=Interview review submitted", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/interview/{interview_id}", response_class=HTMLResponse)
async def get_interview_page(request: Request, interview_id: int, db: Session = Depends(database.get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login")
    
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        return HTMLResponse("Interview not found", status_code=404)
    
    # Check if user is the candidate
    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user or interview.candidate_id != user.id:
        return HTMLResponse("Unauthorized", status_code=403)

    # Base64 encode the questions for the frontend to prevent easy inspection
    try:
        encoded_questions = base64.b64encode(interview.questions.encode()).decode()
    except Exception:
        encoded_questions = ""

    return templates.TemplateResponse(request, "interview.html", {
        "interview": interview,
        "encoded_questions": encoded_questions
    })

@app.post("/interview/{interview_id}/submit")
async def submit_answer(interview_id: int, request: Request, db: Session = Depends(database.get_db)):
    data = await request.json()
    answer = data.get("answer")
    question_idx = data.get("question_index")
    
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
        
    responses = json.loads(interview.responses) if interview.responses else []
    
    # Ensure list is long enough
    while len(responses) <= question_idx:
        responses.append("")
        
    responses[question_idx] = answer
    interview.responses = json.dumps(responses)
    db.commit()
    
    return {"status": "saved"}

@app.post("/interview/{interview_id}/complete")
async def complete_interview(interview_id: int, db: Session = Depends(database.get_db)):
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    questions = json.loads(interview.questions)
    responses = json.loads(interview.responses) if interview.responses else []
    
    transcript = ""
    for i, q in enumerate(questions):
        a = responses[i] if i < len(responses) else "No Answer"
        transcript += f"Q: {q}\nA: {a}\n\n"
        
    cheat_log = json.loads(interview.cheat_log) if interview.cheat_log else []
    proctoring_context = ""
    if cheat_log:
        proctoring_context = "\nPROCTORING VIOLATIONS DETECTED:\n" + "\n".join([f"- {v['reason']} at {v['timestamp']}" for v in cheat_log])
        proctoring_context += "\n\nIMPORTANT: Consider these violations in your evaluation. Technical accuracy remains important, but suspicious behavior should be factored into the final result (e.g. recommend MANUAL_REVIEW or FAIL if violations are significant)."

    try:
        chat_completion = await groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior technical interviewer for HireWise. "
                        "Evaluate interview transcripts and proctoring logs. Return ONLY a raw JSON object with no markdown or backticks."
                    )
                },
                {
                    "role": "user",
                    "content": f"""
                    Evaluate the following interview transcript and proctoring context for a {interview.job_role} role at {interview.difficulty} difficulty level.

                    Transcript:
                    {transcript}
                    {proctoring_context}

                    Analyze the candidate's performance using this point-based rubric (Total: 100 pts):
                    1. Technical Accuracy (Correctness of code/answers): Max 40 pts
                    2. Depth of Knowledge (Nuance, edge cases, system thinking): Max 30 pts
                    3. Communication Clarity (Articulation, logical structure): Max 20 pts
                    4. Integrity & Professionalism (Deduct for proctoring violations if significant): Max 10 pts

                    CRITICAL: The final 'score' must be a precise integer calculated from these points (e.g., 73, 62, 84). DO NOT round to the nearest 10 (like 60, 70, 80). Provide a granular, specific score based on the evidence.

                    Return ONLY a raw JSON object (no markdown, no backticks) with this exact structure:
                    {{"result": "PASS or FAIL or MANUAL_REVIEW", "score": <precise 0-100 integer>, "strengths": ["strength1", "strength2"], "weaknesses": ["weakness1", "weakness2"], "analysis": "A detailed 2-3 sentence technical analysis.", "feedback": "A concise summary for the recruiter."}}
                    """
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        text = chat_completion.choices[0].message.content.strip()
        evaluation = json.loads(text)
        
        # Ensure all required fields exist with fallbacks
        evaluation.setdefault("result", "MANUAL_REVIEW")
        evaluation.setdefault("score", 0)
        evaluation.setdefault("strengths", [])
        evaluation.setdefault("weaknesses", [])
        evaluation.setdefault("analysis", "AI analysis completed.")
        evaluation.setdefault("feedback", "Review candidate logs for details.")
        
        interview.evaluation = json.dumps(evaluation)
        interview.status = "cleared" if evaluation.get("result") == "PASS" else "completed"
        print(f"Groq evaluation for interview {interview_id}: {evaluation.get('result')} | Score: {evaluation.get('score')}")
        
    except Exception as e:
        print(f"Groq Eval Error: {e}")
        interview.status = "completed"
        interview.evaluation = json.dumps({
            "result": "MANUAL_REVIEW",
            "score": 0,
            "strengths": [],
            "weaknesses": [],
            "analysis": "The AI model encountered an error during evaluation.",
            "feedback": "AI Eval Failed. Manual review required."
        })
        
    db.commit()
    return {"status": "completed"}

@app.post("/interview/{interview_id}/flag-cheat")
async def flag_cheat(interview_id: int, request: Request, db: Session = Depends(database.get_db)):
    """Log a cheating violation. If auto_fail=true, terminate the interview immediately."""
    data = await request.json()
    reason = data.get("reason", "Unknown violation")
    timestamp = data.get("timestamp", "")
    auto_fail = data.get("auto_fail", False)

    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Append to cheat log
    log = json.loads(interview.cheat_log) if interview.cheat_log else []
    log.append({"reason": reason, "timestamp": timestamp})
    interview.cheat_log = json.dumps(log)
    interview.cheat_flagged = True # Always flag if there's any violation

    if auto_fail:
        interview.status = "cheating_detected"
        interview.evaluation = json.dumps({
            "result": "FAIL",
            "score": 0,
            "strengths": [],
            "weaknesses": ["Cheating detected during interview"],
            "analysis": f"This interview was automatically terminated due to cheating. Violations: {len(log)}.",
            "feedback": f"⚠️ CHEATING DETECTED — Candidate was flagged by the automated proctoring system. {len(log)} violation(s) recorded."
        })
        print(f"[PROCTORING] Interview {interview_id} TERMINATED for cheating. Violations: {log}")

    db.commit()
    return {"status": "logged", "auto_failed": auto_fail}


@app.post("/interview/{interview_id}/upload-chunk")
async def upload_chunk(
    interview_id: int, 
    chunk: UploadFile = File(...), 
    chunk_index: int = Form(...), 
    db: Session = Depends(database.get_db)
):
    """Receive a video chunk from the candidate and save it to the database."""
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    contents = await chunk.read()
    video_chunk = models.VideoChunk(
        interview_id=interview_id,
        chunk_index=chunk_index,
        data=contents
    )
    db.add(video_chunk)

    if not interview.recording_file:
        interview.recording_file = "db_stored"

    db.commit()
    return {"status": "saved", "chunk_index": chunk_index}

@app.get("/interview/{interview_id}/video")
async def get_video(interview_id: int, db: Session = Depends(database.get_db)):
    """Stream the video recording from chunks stored in the database."""
    chunks = db.query(models.VideoChunk).filter(models.VideoChunk.interview_id == interview_id).order_by(models.VideoChunk.chunk_index).all()
    
    if not chunks:
        raise HTTPException(status_code=404, detail="Recording not found")

    def iterfile():
        for chunk in chunks:
            yield chunk.data

    return StreamingResponse(iterfile(), media_type="video/webm")

@app.post("/interview/{interview_id}/publish")
async def publish_interview_result(request: Request, interview_id: int, db: Session = Depends(database.get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login")
        
    user = db.query(models.User).filter(models.User.email == user_email).first()
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    
    if not user or not interview:
        return HTMLResponse("Not found", status_code=404)
        
    if user.role != "admin" and interview.recruiter_id != user.id:
        return HTMLResponse("Unauthorized", status_code=403)
        
    interview.is_published = not interview.is_published
    db.commit()
    
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/interview/{interview_id}/hint")
async def record_hint_used(request: Request, interview_id: int, db: Session = Depends(database.get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        return {"status": "error", "msg": "Unauthorized"}
        
    user = db.query(models.User).filter(models.User.email == user_email).first()
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    
    if not user or not interview or interview.candidate_id != user.id:
        return {"status": "error", "msg": "Unauthorized"}
        
    interview.hints_used = (interview.hints_used or 0) + 1
    db.commit()
    return {"status": "success", "hints_used": interview.hints_used}

@app.get("/interview/{interview_id}/report", response_class=HTMLResponse)
async def get_report_page(request: Request, interview_id: int, db: Session = Depends(database.get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login")
    
    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user:
        return RedirectResponse(url="/login")

    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        return HTMLResponse("Interview not found", status_code=404)
    
    is_recruiter_or_admin = user.role == "admin" or interview.recruiter_id == user.id
    
    if not is_recruiter_or_admin and interview.candidate_id != user.id:
        return HTMLResponse("Unauthorized", status_code=403)
        
    if interview.candidate_id == user.id and not is_recruiter_or_admin:
        if not interview.is_published:
            return HTMLResponse(
                "<div style='padding: 3rem; text-align: center; font-family: sans-serif;'>"
                "<h2>Result Hidden</h2><p>Your interview report is currently under review and hasn't been published by the recruiter yet.</p>"
                "<a href='/dashboard' style='color: #4285f4; text-decoration: none;'>Return to Dashboard</a></div>", 
                status_code=403
            )

    return templates.TemplateResponse(request, "report.html", {
        "user": user,
        "interview": interview,
        "json": json,
        "datetime": datetime
    })

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login")
    response.delete_cookie("user_email")
    return response

# ── Question Templates ──────────────────────────────────────────────────────

@app.post("/templates/save")
async def save_template(
    request: Request,
    template_name: str = Form(...),
    job_role: str = Form(""),
    questions_text: str = Form(...),
    db: Session = Depends(database.get_db)
):
    user_email = request.cookies.get("user_email")
    recruiter = db.query(models.User).filter(models.User.email == user_email).first()
    if not recruiter or recruiter.role != "recruiter":
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Parse questions — one per line
    questions_list = [q.strip() for q in questions_text.split("\n") if q.strip()]
    if not questions_list:
        raise HTTPException(status_code=400, detail="No questions provided")

    template = models.QuestionTemplate(
        recruiter_id=recruiter.id,
        name=template_name,
        job_role=job_role,
        questions=json.dumps(questions_list)
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return {"id": template.id, "name": template.name, "questions": questions_list}

@app.get("/templates")
async def list_templates(request: Request, db: Session = Depends(database.get_db)):
    user_email = request.cookies.get("user_email")
    recruiter = db.query(models.User).filter(models.User.email == user_email).first()
    if not recruiter:
        raise HTTPException(status_code=401, detail="Unauthorized")
    templates = db.query(models.QuestionTemplate).filter(
        models.QuestionTemplate.recruiter_id == recruiter.id
    ).all()
    return [
        {"id": t.id, "name": t.name, "job_role": t.job_role, "questions": json.loads(t.questions)}
        for t in templates
    ]

@app.delete("/templates/{template_id}")
async def delete_template(template_id: int, request: Request, db: Session = Depends(database.get_db)):
    user_email = request.cookies.get("user_email")
    recruiter = db.query(models.User).filter(models.User.email == user_email).first()
    if not recruiter:
        raise HTTPException(status_code=401, detail="Unauthorized")
    template = db.query(models.QuestionTemplate).filter(
        models.QuestionTemplate.id == template_id,
        models.QuestionTemplate.recruiter_id == recruiter.id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
    return {"status": "deleted"}

# ── Admin Panel ──────────────────────────────────────────────────────────────

def require_admin(request: Request, db: Session = Depends(database.get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(database.get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login")
    admin = db.query(models.User).filter(models.User.email == user_email).first()
    if not admin or admin.role != "admin":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    all_users = db.query(models.User).filter(models.User.role != "admin").order_by(models.User.id).all()
    all_interviews = db.query(models.Interview).all()

    # Build candidate -> interview map
    candidate_interviews = {}
    for iv in all_interviews:
        candidate_interviews.setdefault(iv.candidate_id, []).append(iv)

    msg = request.query_params.get("msg")
    return templates.TemplateResponse(request, "admin.html", {
        "admin": admin,
        "users": all_users,
        "candidate_interviews": candidate_interviews,
        "msg": msg,
        "json": json
    })

@app.post("/admin/users/{user_id}/delete")
async def admin_delete_user(user_id: int, request: Request, db: Session = Depends(database.get_db)):
    user_email = request.cookies.get("user_email")
    admin = db.query(models.User).filter(models.User.email == user_email).first()
    if not admin or admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete associated interviews and cleanup recording files
    interviews_to_delete = db.query(models.Interview).filter(
        (models.Interview.recruiter_id == user_id) | (models.Interview.candidate_id == user_id)
    ).all()
    
    recordings_dir = os.path.join(os.path.dirname(__file__), "static", "recordings")
    for iv in interviews_to_delete:
        if iv.recording_file:
            rec_path = os.path.join(recordings_dir, iv.recording_file)
            if os.path.exists(rec_path):
                try:
                    os.remove(rec_path)
                    print(f"[ADMIN] Deleted recording: {iv.recording_file}")
                except Exception as e:
                    print(f"[ADMIN] Failed to delete recording {iv.recording_file}: {e}")
            
            # delete associated video chunks from DB
            db.query(models.VideoChunk).filter(models.VideoChunk.interview_id == iv.id).delete()
            
        db.delete(iv)

    # Delete associated templates
    db.query(models.QuestionTemplate).filter(
        models.QuestionTemplate.recruiter_id == user_id
    ).delete(synchronize_session=False)

    db.delete(user)
    db.commit()
    return RedirectResponse(url=f"/admin?msg=User+{user.full_name}+deleted+successfully", status_code=303)

@app.post("/admin/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: int,
    request: Request,
    new_password: str = Form(...),
    db: Session = Depends(database.get_db)
):
    user_email = request.cookies.get("user_email")
    admin = db.query(models.User).filter(models.User.email == user_email).first()
    if not admin or admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(new_password)
    db.commit()
    return RedirectResponse(url=f"/admin?msg=Password+reset+for+{user.full_name}", status_code=303)

@app.post("/admin/create")
async def create_admin(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db)
):
    """One-time admin creation endpoint. Disable after first use in production."""
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        return RedirectResponse(url="/login?error=Email+already+registered", status_code=303)
    admin_user = models.User(
        full_name=full_name,
        email=email,
        hashed_password=get_password_hash(password),
        role="admin"
    )
    db.add(admin_user)
    db.commit()
    return RedirectResponse(url="/login?msg=Admin+account+created", status_code=303)

@app.post("/interview/{interview_id}/execute")
async def execute_code(
    interview_id: int, 
    request: Request, 
    db: Session = Depends(database.get_db)
):
    data = await request.json()
    code = data.get("code", "")
    language = data.get("language", "python")
    q_idx = data.get("question_index", 0)
    is_submit = data.get("is_submit", False)

    if not code:
        return {"status": "error", "msg": "No code provided"}

    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        return {"status": "error", "msg": "Interview not found"}

    try:
        questions = json.loads(interview.questions) if interview.questions else []
        if q_idx < 0 or q_idx >= len(questions):
            return {"status": "error", "msg": "Invalid question index"}
        
        q = questions[q_idx]
        if not isinstance(q, dict) or (q.get("type") != "dsa" and not q.get("visible_test_cases")):
            return {"status": "error", "msg": "Not a valid DSA question format"}
            
        vis_cases = q.get("visible_test_cases", [])
        hid_cases = q.get("hidden_test_cases", []) if is_submit else []
        test_cases = vis_cases + hid_cases

        if not test_cases:
            return {"status": "error", "msg": "No test cases found for this question"}

        import subprocess
        import tempfile
        import sys
        
        passed_all = True
        final_output = ""

        for idx, tc in enumerate(test_cases):
            tc_test_code = tc.get(f"{language}_test", "")
            if not tc_test_code:
                tc_test_code = tc.get("input", "")
                
            full_code = code + "\n\n" + tc_test_code
            
            ext = ".py" if language == "python" else ".js"
            cmd = [sys.executable] if language == "python" else ["node"]
            
            with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as f:
                f.write(full_code)
                tmp_path = f.name
                
            try:
                cmd.append(tmp_path)
                # Run the code safely with a 5-second timeout
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
                stdout = result.stdout.strip()
                stderr = result.stderr.strip()
                return_code = result.returncode
            except subprocess.TimeoutExpired:
                stdout = ""
                stderr = "Execution timed out (5s limit exceeded). Infinite loop or heavy computation."
                return_code = 124
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            
            is_hidden = idx >= len(vis_cases)
            tc_label = "Hidden" if is_hidden else "Visible"
            
            if return_code != 0 or stderr:
                passed_all = False
                final_output += f"Test Case {idx+1} ({tc_label}) FAILED\n"
                final_output += f"Error:\n{stderr}\n\n"
                break
                
            expected = str(tc.get("expected_output", tc.get("output", ""))).strip()
            if stdout == expected:
                final_output += f"Test Case {idx+1} ({tc_label}) PASSED\n"
            else:
                passed_all = False
                final_output += f"Test Case {idx+1} ({tc_label}) FAILED\n"
                if not is_hidden:
                    final_output += f"Expected: {expected}\nGot: {stdout}\n\n"
                else:
                    final_output += f"Hidden test case failed.\n\n"
                break

        return {
            "status": "success",
            "passed": passed_all,
            "output": final_output.strip()
        }

    except Exception as e:
        print(f"Code Execution Error: {e}")
        return {"status": "error", "msg": str(e)}
