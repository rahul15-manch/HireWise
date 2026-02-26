from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, File, UploadFile
import shutil
import uuid
from pypdf import PdfReader
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app import models, database

# Database Setup
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password, hashed_password):
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
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    
    # Successful Login (Redirect to Dashboard placeholder)
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="user_email", value=user.email) # Simple Session
    return response

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

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
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already registered"})
    
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
    if user.role == "recruiter":
        interviews = db.query(models.Interview).filter(models.Interview.recruiter_id == user.id).all()
    else:
        interviews = db.query(models.Interview).filter(models.Interview.candidate_id == user.id).all()

    msg = request.query_params.get("msg")
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "interviews": interviews, "msg": msg, "json": json})

import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
from groq import Groq

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@app.post("/interviews/create")
async def create_interview(
    request: Request,
    candidate_email: str = Form(...),
    job_role: str = Form(...),
    difficulty: str = Form(...),
    generate_ai: bool = Form(False),
    manual_questions: str = Form(None),
    pdf_file: UploadFile = File(None),
    resume_file: UploadFile = File(None),
    db: Session = Depends(database.get_db)
):
    user_email = request.cookies.get("user_email")
    recruiter = db.query(models.User).filter(models.User.email == user_email).first()
    
    if not recruiter or recruiter.role != "recruiter":
        return RedirectResponse(url="/dashboard") # Unauthorized

    candidate = db.query(models.User).filter(models.User.email == candidate_email, models.User.role == "candidate").first()
    if not candidate:
        return templates.TemplateResponse("dashboard.html", {"request": request, "user": recruiter, "interviews": [], "error": "Candidate not found!"})

    questions_list = []
    resume_text = ""
    saved_resume_filename = None

    # Handle Resume Upload and Text Extraction
    if resume_file and resume_file.filename:
        os.makedirs("app/static/uploads", exist_ok=True)
        file_ext = os.path.splitext(resume_file.filename)[1]
        saved_resume_filename = f"resume_{uuid.uuid4()}{file_ext}"
        resume_path = os.path.join("app/static/uploads", saved_resume_filename)
        
        with open(resume_path, "wb") as buffer:
            shutil.copyfileobj(resume_file.file, buffer)
        
        try:
            reader = PdfReader(resume_path)
            for page in reader.pages:
                resume_text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Resume Extraction Error: {e}")

    if generate_ai:
        try:
            chat = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a world-class senior technical interviewer and recruiter at a top-tier tech company. "
                            "Your job is to generate high-quality, personalized interview questions. "
                            "If a candidate's resume is provided, analyze it to tailor questions to their specific experience and skills. "
                            "If no resume is provided, generate sharp, scenario-based questions based on the job role and difficulty. "
                            "Return ONLY a JSON object with two keys: 'candidate_summary' (a brief professional summary, or null if no resume) and 'questions' (a list of 7 question strings)."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Generate exactly 7 high-quality technical interview questions for a {difficulty}-level {job_role} candidate.\n\n"
                            f"Resume Context (use this to personalize questions if provided):\n"
                            f"{resume_text[:4000] if resume_text else 'No resume provided.'}\n\n"
                            f"Requirements:\n"
                            f"- Match the {difficulty} difficulty honestly.\n"
                            f"- If a resume is provided, ask deep questions about their specific projects, tools, and experience.\n"
                            f"- Mix question types: conceptual, coding, and behavioral-technical hybrids.\n"
                            f"- Write as if you're interviewing at a top-tier tech firm.\n\n"
                            f"Return ONLY this JSON: {{\"candidate_summary\": \"...\", \"questions\": [\"q1\", ..., \"q7\"]}}"
                        )
                    }
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            result = json.loads(chat.choices[0].message.content)
            questions_list = result.get("questions", [])
            candidate_summary = result.get("candidate_summary", "")
            print(f"Groq generated {len(questions_list)} questions for {job_role} ({difficulty})")
        except Exception as e:
            print(f"Groq Question Generation Error: {e}")
            questions_list = [
                f"Walk me through how you would design a scalable {job_role} system from scratch.",
                f"Describe a challenging bug you encountered in a {difficulty}-level project. How did you debug it?",
                f"What are the key performance trade-offs you consider when working as a {job_role}?",
                "How do you ensure code quality in a fast-moving team?",
                "Tell me about a time you had to learn a new technology under time pressure.",
            ]
            candidate_summary = None

    elif manual_questions:
        questions_list = [q.strip() for q in manual_questions.split('\n') if q.strip()]
    
    saved_pdf_filename = None
    if pdf_file and pdf_file.filename:
        # Ensure uploads directory exists
        os.makedirs("app/static/uploads", exist_ok=True)
        
        # Generate unique filename
        file_ext = os.path.splitext(pdf_file.filename)[1]
        saved_pdf_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join("app/static/uploads", saved_pdf_filename)
        
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
    
    print(f"DEBUG: Saved interview {new_interview.id} with questions: {new_interview.questions}")
    
    return RedirectResponse(url="/dashboard?msg=Interview+Created+Successfully", status_code=status.HTTP_303_SEE_OTHER)
    
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

    return templates.TemplateResponse("interview.html", {"request": request, "interview": interview})

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
        chat_completion = groq_client.chat.completions.create(
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


@app.post("/interview/{interview_id}/upload-recording")
async def upload_recording(interview_id: int, file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    """Receive the candidate's interview video recording and save it."""
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Save to app/static/recordings/
    recordings_dir = os.path.join(os.path.dirname(__file__), "static", "recordings")
    os.makedirs(recordings_dir, exist_ok=True)

    ext = ".webm"  # MediaRecorder default in Chrome
    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(recordings_dir, filename)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    interview.recording_file = filename
    db.commit()
    print(f"[RECORDING] Interview {interview_id} recording saved: {filename} ({len(contents)//1024}KB)")
    return {"status": "saved", "filename": filename}

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
        return RedirectResponse(url="/dashboard")

    all_users = db.query(models.User).filter(models.User.role != "admin").order_by(models.User.id).all()
    all_interviews = db.query(models.Interview).all()

    # Build candidate -> interview map
    candidate_interviews = {}
    for iv in all_interviews:
        candidate_interviews.setdefault(iv.candidate_id, []).append(iv)

    msg = request.query_params.get("msg")
    return templates.TemplateResponse("admin.html", {
        "request": request,
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

