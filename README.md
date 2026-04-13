![Gemini Job Agent](tenor.gif)

# Gemini Job Agent


An automated pipeline that searches for jobs, researches companies, and generates tailored CVs and cover letters using Google Gemini AI.

---

## Quick Start (Initialization)

Before running the agent, you need to set up the folder structure and placeholder files. We have provided scripts for this:

- **Windows**: Run `powershell ./initializing_scripts/setup_windows.ps1`
- **macOS / Ubuntu**: Run `bash ./initializing_scripts/setup_unix.sh`

These scripts create the `cv_workspace/`, `jobs_evaluated/`, and `tracker/` folders, as well as a template `user_profile.json`.

---

## Configuration

### 1. API Keys
Create a `.env` file in the root directory and add your Gemini API Key:
```env
GEMINI_API_KEY=your_api_key_here
```

### 2. User Profile
Edit the `user_profile.json` in the root directory. This file contains the personal information the agent uses to fill application forms and tailor your CV.

### 3. CV Workspace (`cv_workspace/`)
This is where your templates live. 
- **`facts.txt`**: Put your raw resume data, bullet points, and skills here.
- **`coverletter.txt`**: A base template for your cover letter.
- **LaTeX Templates**: Place your `.tex` files here (e.g., `androidCV.tex`, `MLCV.tex`).

#### Using AltaCV Template
To use the popular [AltaCV Template](https://www.overleaf.com/latex/templates/altacv-template/trgqjpwnmtgv):
1. Download the source files from Overleaf.
2. Copy the `.tex` file into `cv_workspace/` and rename it to match the names in `config.py` (default: `androidCV.tex` or `MLCV.tex`).
3. **Important**: Ensure all supporting files (`altacv.cls`, etc.) are also placed in the `cv_workspace/` folder so the LaTeX compiler can find them.

---

## How to Run

### 1. Terminal Mode
Run the main pipeline directly:
```bash
python main.py
```
Select **T** for Terminal. You can then choose to:
1. Search for jobs automatically on DataNerd.
2. Provide a direct URL to a job posting.

### 2. GUI Mode
For a visual experience with real-time logs and token tracking:
```bash
python main.py
```
Select **G** for GUI. This launches a desktop application where you can monitor the agent's "eyes" and see screenshots of it working.

### 3. Local API (Required for Extension)
To use the Firefox extension or the web frontend, you must have the backend API running:
```bash
python api.py
```
*The API runs on `http://localhost:8088`.*

---

## 🦊 Firefox Extension

The extension allows you to trigger the pipeline directly from LinkedIn, Indeed, or any job board.

### Installation
1. Open Firefox and go to `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on...**.
3. Select the `manifest.json` file inside the `firefox/` folder.

### Usage
1. Ensure `python api.py` is running.
2. Navigate to any job description page.
3. Click the ** Run Pipeline** floating button in the bottom-right.
4. Once you are on the application form page, click **Auto-Fill** to instantly populate the fields with your profile data.
5. Click the Gemini icon in your toolbar to check the connection status.

---

## Project Structure
- `agents/`: Specialized AI agents (Reader, Researcher, Tailor, Tracker).
- `cv_workspace/`: Your LaTeX templates and personal facts.
- `jobs_evaluated/`: Every job you process gets a unique folder here with its tailored PDF.
- `tracker/`: Contains `job_tracker.md` to keep track of all applications.
- `initializing_scripts/`: Setup scripts for new users.
- `gui/`: Tkinter-based desktop interface.
- `firefox/`: Manifest V3 browser extension.
