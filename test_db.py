import json
from app import models, database
from sqlalchemy.orm import Session

def test_db():
    db = database.SessionLocal()
    try:
        # Get a recruiter and a candidate
        recruiter = db.query(models.User).filter(models.User.role == "recruiter").first()
        candidate = db.query(models.User).filter(models.User.role == "candidate").first()
        
        if not recruiter or not candidate:
            print("Need at least one recruiter and one candidate in DB.")
            return

        new_interview = models.Interview(
            recruiter_id=recruiter.id,
            candidate_id=candidate.id,
            job_role="Test Role",
            difficulty="Beginner",
            questions=json.dumps(["What is Python?", "Why coding?"]),
            status="pending"
        )
        db.add(new_interview)
        db.commit()
        db.refresh(new_interview)
        print(f"Created Interview ID: {new_interview.id}")
        print(f"Questions in DB: {new_interview.questions}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_db()
