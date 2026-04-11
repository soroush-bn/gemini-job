import os
import subprocess
from langchain_core.tools import tool

WORKSPACE = "cv_workspace"

@tool
def read_latex_cv() -> str:
    """Reads the user's base LaTeX CV from the cv_workspace directory."""
    filepath = os.path.join(WORKSPACE, "androidCV.tex")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: androidCV.tex not found in {WORKSPACE}/"

@tool
def save_tailored_latex_cv(content: str) -> str:
    """Saves the newly tailored CV to a .tex file inside cv_workspace."""
    filepath = os.path.join(WORKSPACE, "tailored_android_cv.tex")
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return "Successfully saved tailored_android_cv.tex. You can now compile it."
    except Exception as e:
        return f"Failed to save LaTeX CV: {str(e)}"

@tool
def compile_latex_to_pdf() -> str:
    """Compiles the tailored_android_cv.tex file into a PDF using pdflatex."""
    try:
        # We run the command inside the WORKSPACE so it finds altacv.cls
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "tailored_android_cv.tex"],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            check=True
        )
        return "SUCCESS! The PDF has been successfully compiled and is ready in the cv_workspace folder."
    except subprocess.CalledProcessError as e:
        # If compilation fails, return the tail end of the LaTeX log so the agent can see the syntax error
        error_log = e.stdout[-1500:] if e.stdout else "Unknown compilation error."
        return f"Compilation FAILED. Here is the LaTeX error log:\n{error_log}\n\nPlease fix the syntax error in the .tex file and try saving/compiling again."
    except FileNotFoundError:
        return "Error: pdflatex is not recognized as a command. Is it installed and in your system PATH?"