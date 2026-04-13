import os
import subprocess
import shutil
from config import CV_WORKSPACE, TEMPLATE_NAME, OUTPUT_NAME_BASE, FACTS_FILE

def read_facts() -> str:
    """Reads additional facts about the user for better tailoring."""
    file_path = os.path.join(CV_WORKSPACE, FACTS_FILE)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "No additional facts found."

def read_latex_template(template_name: str = TEMPLATE_NAME) -> str:
    """Reads the LaTeX template from the cv_workspace."""
    file_path = os.path.normpath(os.path.join(CV_WORKSPACE, template_name))
    print(f"\n[TOOL CALL] Reading template from: {file_path}")
    
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
    return f"Error: Template '{template_name}' not found."

def save_and_compile_latex(latex_content: str, company_name: str, target_dir: str) -> str:
    """Saves and compiles the LaTeX CV into the specified job-specific folder."""
    clean_company = "".join(x for x in company_name if x.isalnum() or x in " _-").strip().replace(" ", "_")
    output_filename = f"{OUTPUT_NAME_BASE}_{clean_company}"
    tex_file = os.path.join(target_dir, f"{output_filename}.tex")
    
    print(f"\n[TOOL CALL] Writing CV to: {tex_file}...")
    
    try:
        # Save the .tex file to the target_dir
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_content)
        
        # Copy the .cls file and other assets to target_dir for compilation
        for item in os.listdir(CV_WORKSPACE):
            if item.endswith(".cls") or item.endswith(".tex") and item != TEMPLATE_NAME:
                shutil.copy2(os.path.join(CV_WORKSPACE, item), target_dir)

        # Run pdflatex from target_dir
        last_result = None
        for _ in range(2):
            last_result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", f"{output_filename}.tex"],
                cwd=target_dir,
                capture_output=True,
                text=True
            )
        
        if last_result and last_result.returncode == 0:
            return f"Success! PDF generated at: {target_dir}"
        else:
            return f"Error during compilation. Log tail:\n{last_result.stdout[-500:] if last_result else 'No log.'}"
            
    except Exception as e:
        return f"An error occurred: {str(e)}"
