from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="candidate")
    interviews_created = relationship("Interview", back_populates="recruiter", foreign_keys="Interview.recruiter_id")
    interviews_assigned = relationship("Interview", back_populates="candidate", foreign_keys="Interview.candidate_id")

class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("users.id"))
    candidate_id = Column(Integer, ForeignKey("users.id"))
    job_role = Column(String)
    difficulty = Column(String)
    questions = Column(String) # JSON string of questions
    responses = Column(String) # JSON string of answers
    evaluation = Column(String) # JSON string of evaluation result
    pdf_file = Column(String, nullable=True) # Path to uploaded PDF
    resume_file = Column(String, nullable=True) # Path to uploaded Resume PDF
    candidate_summary = Column(String, nullable=True) # AI-generated professional summary from resume
    status = Column(String, default="pending") # pending, completed, cleared, rejected, cheating_detected
    recruiter_feedback = Column(String, nullable=True) # Optional feedback from recruiter
    cheat_flagged = Column(Boolean, default=False) # True if candidate was caught cheating
    cheat_log = Column(String, nullable=True) # JSON array of timestamped violation events
    recording_file = Column(String, nullable=True) # Path to candidate's interview video recording

    recruiter = relationship("User", back_populates="interviews_created", foreign_keys=[recruiter_id])
    candidate = relationship("User", back_populates="interviews_assigned", foreign_keys=[candidate_id])

class QuestionTemplate(Base):
    __tablename__ = "question_templates"

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)           # Template name e.g. "Python Senior SDE"
    job_role = Column(String)       # Optional label
    questions = Column(String)      # JSON list of question strings

    recruiter = relationship("User", foreign_keys=[recruiter_id])

