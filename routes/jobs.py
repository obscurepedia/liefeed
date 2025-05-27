from flask import Blueprint
import subprocess

jobs_bp = Blueprint("jobs", __name__)

@jobs_bp.route("/generate-reel")
def trigger_reel():
    subprocess.Popen(["python", "-m", "utils.image.auto_reel"])
    return "🎬 Reel job started in background", 200
