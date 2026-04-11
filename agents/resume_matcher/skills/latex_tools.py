import os
import subprocess
from config import CV_WORKSPACE, TEMPLATE_NAME, OUTPUT_NAME_BASE

def read_latex_template(template_name: str = TEMPLATE_NAME) -> str:
    """Reads the LaTeX template from the cv_workspace."""
    file_path = os.path.normpath(os.path.join(CV_WORKSPACE, template_name))
    
    print(f"\n[TOOL CALL] Attempting to read template from: {file_path}")
    
    if os.path.exists(file_path):
        print(f"[TOOL CALL] SUCCESS: File found at {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
    else:
        print(f"[TOOL CALL] ERROR: File NOT found at {file_path}")
        # List files in workspace for debugging
        if os.path.exists(CV_WORKSPACE):
            files = os.listdir(CV_WORKSPACE)
            return f"Error: Template '{template_name}' not found. Files in workspace: {files}"
        else:
            return f"Error: Workspace directory '{CV_WORKSPACE}' does not exist."

def save_and_compile_latex(latex_content: str, company_name: str) -> str:
    """Saves the tailored LaTeX content and compiles it."""
    clean_company = "".join(x for x in company_name if x.isalnum() or x in " _-").strip().replace(" ", "_")
    output_filename = f"{OUTPUT_NAME_BASE}_{clean_company}"
    tex_file = os.path.normpath(os.path.join(CV_WORKSPACE, f"{output_filename}.tex"))
    
    print(f"\n[TOOL CALL] Writing to: {tex_file} and compiling...")
    
    try:
        # Ensure directory exists
        os.makedirs(CV_WORKSPACE, exist_ok=True)
        
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_content)
        
        # Run pdflatex twice
        last_result = None
        for _ in range(2):
            last_result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", f"{output_filename}.tex"],
                cwd=CV_WORKSPACE,
                capture_output=True,
                text=True
            )
        
        if last_result and last_result.returncode == 0:
            pdf_path = os.path.join(CV_WORKSPACE, f"{output_filename}.pdf")
            return f"Success! PDF generated at: {pdf_path}"
        else:
            error_log = last_result.stdout if last_result else "No output from pdflatex."
            return f"Error during LaTeX compilation.\nLog snippet:\n{error_log[-500:]}"
            
    except Exception as e:
        return f"An error occurred: {str(e)}"
