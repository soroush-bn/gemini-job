import os
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Shared Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash-lite" 
MATCH_MODEL_NAME = "gemini-2.5-pro" # Pro is much better at LaTeX and code manipulation

# Workspace Paths
CV_WORKSPACE = os.path.join(os.curdir, "cv_workspace")
TEMPLATE_NAME = "androidCV.tex"
# The base name for the output file
OUTPUT_NAME_BASE = "Soroush_Baghernezhad_CV"

