import os
from fpdf import FPDF
from config import CV_WORKSPACE, COVERLETTER_TEMPLATE, FACTS_FILE

def read_facts() -> str:
    """Reads additional facts about the user for better tailoring."""
    file_path = os.path.join(CV_WORKSPACE, FACTS_FILE)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "No additional facts found."

def read_coverletter_template() -> str:
    """Reads the base cover letter text template."""
    file_path = os.path.join(CV_WORKSPACE, COVERLETTER_TEMPLATE)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: {COVERLETTER_TEMPLATE} not found in {CV_WORKSPACE}."

def save_coverletter_outputs(text_content: str, target_dir: str, company_name: str):
    """Saves tailored cover letter as both .txt and .pdf in the job folder."""
    clean_company = "".join(x for x in company_name if x.isalnum() or x in " _-").strip().replace(" ", "_")
    base_name = f"Cover_Letter_{clean_company}"
    
    # Save .txt
    txt_path = os.path.join(target_dir, f"{base_name}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text_content)
    
    # Save .pdf
    pdf_path = os.path.join(target_dir, f"{base_name}.pdf")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    
    # Handle multi-line text and encoding
    for line in text_content.split('\n'):
        # Normalize to avoid common PDF character issues
        clean_line = line.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 5, txt=clean_line)
    
    pdf.output(pdf_path)
    return f"Success! Cover Letter saved as .txt and .pdf in {target_dir}"
