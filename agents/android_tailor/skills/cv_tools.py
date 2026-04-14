import os
import shutil
import subprocess
from config import CV_WORKSPACE, OUTPUT_NAME_BASE

def save_and_compile_latex(latex_content: str, company_name: str, target_dir: str) -> str:
    """
    Saves the full LaTeX content to a file and compiles it using pdflatex.
    """
    # Force absolute path
    target_dir = os.path.abspath(target_dir)
    
    clean_company = "".join(x for x in company_name if x.isalnum() or x in " _-").strip().replace(" ", "_")
    output_filename = f"{OUTPUT_NAME_BASE}_{clean_company}"
    tex_file = os.path.join(target_dir, f"{output_filename}.tex")
    
    try:
        # Save the full LaTeX content
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_content)

        # Copy assets (.cls, fonts, images) from workspace to target dir
        if os.path.exists(CV_WORKSPACE):
            for item in os.listdir(CV_WORKSPACE):
                # Copy everything that might be needed for compilation (cls, png, jpg, tex files etc.)
                if any(item.endswith(ext) for ext in [".cls", ".png", ".jpg", ".jpeg", ".tex"]):
                    if item != output_filename + ".tex": # Don't overwrite the one we just wrote if it was there
                        shutil.copy2(os.path.join(CV_WORKSPACE, item), target_dir)

        # Compile once (sufficient for most CVs)
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", f"{output_filename}.tex"],
            cwd=target_dir,
            capture_output=True,
            text=True
        )
        
        pdf_path = os.path.join(target_dir, f"{output_filename}.pdf")
        if os.path.exists(pdf_path):
            return f"Success! CV compiled to {pdf_path}"
        else:
            return f"LaTeX Error: {result.stdout[-500:]}"

    except Exception as e:
        return f"Error during save/compile: {str(e)}"
