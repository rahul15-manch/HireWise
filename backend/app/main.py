from fastapi import FastAPI
from backend.app.api import auth  # your auth router

app = FastAPI()

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to AI Interview Platform API!"}
