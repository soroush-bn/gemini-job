import os
from fpdf import FPDF
from config import CV_WORKSPACE, COVERLETTER_TEMPLATE, FACTS_FILE

def get_career_facts() -> str:
    """Reads the user's career facts and experience from facts.txt."""
    path = os.path.join(CV_WORKSPACE, FACTS_FILE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "Error: facts.txt not found."

def get_coverletter_template() -> str:
    """Reads the base cover letter template."""
    path = os.path.join(CV_WORKSPACE, COVERLETTER_TEMPLATE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "Error: coverletter.txt template not found."

def save_coverletter_as_pdf(text_content: str, target_dir: str, company_name: str) -> str:
    """
    Converts the tailored cover letter text into a PDF and saves it.
    Also saves a .txt version for reference.
    """
    try:
        if not target_dir or target_dir == ".":
            return "Error: target_dir is invalid."

        os.makedirs(target_dir, exist_ok=True)
        file_base = f"Cover_Letter_{company_name.replace(' ', '_')}"
        txt_path = os.path.join(target_dir, f"{file_base}.txt")
        pdf_path = os.path.join(target_dir, f"{file_base}.pdf")

        # Save Text
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text_content)

        # Save PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for line in text_content.split('\n'):
            # Replace non-latin-1 characters to avoid FPDF errors
            clean_line = line.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, txt=clean_line)
        pdf.output(pdf_path)

        return f"Success! Cover Letter converted to PDF and saved in {target_dir}"
    except Exception as e:
        return f"Error during PDF conversion/save: {str(e)}"
