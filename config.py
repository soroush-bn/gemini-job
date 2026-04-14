import os
from dotenv import load_dotenv

load_dotenv()

# Get the directory where config.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Shared Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash-lite" 
MATCH_MODEL_NAME = "gemini-2.5-flash" # Pro is much better at LaTeX and code manipulation

# Workspace Paths
CV_WORKSPACE = os.path.join(BASE_DIR, "cv_workspace")
JOBS_EVALUATED_DIR = os.path.join(BASE_DIR, "jobs_evaluated")
TRACKER_FILE_PATH = os.path.join(BASE_DIR, "tracker", "job_tracker.md")
TEMPLATE_NAME = "androidCV.tex"
ML_TEMPLATE_NAME = "MLCV.tex"
COVERLETTER_TEMPLATE = "coverletter.txt"
FACTS_FILE = "facts.txt"
OUTPUT_NAME_BASE = "Soroush_Baghernezhad_CV"
