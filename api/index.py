import os
import sys
import traceback

try:
    from app.main import app
    startup_error = None
except Exception as e:
    startup_error = traceback.format_exc()
    from fastapi import FastAPI
    app = FastAPI()

@app.get("/debug")
async def debug():
    info = {
        "cwd": os.getcwd(),
        "python_path": sys.path[:5],
        "app_dir_exists": os.path.isdir("app"),
        "templates_dir_exists": os.path.isdir("app/templates"),
        "tmp_writable": os.access("/tmp", os.W_OK),
        "startup_error": startup_error,
    }
    if os.path.isdir("app/templates"):
        info["template_files"] = os.listdir("app/templates")
    return info
