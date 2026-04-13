#!/bin/bash
# Gemini Job Agent - macOS/Ubuntu Initialization Script

echo -e "\033[0;36mCreating Directories...\033[0m"
mkdir -p cv_workspace
mkdir -p jobs_evaluated
mkdir -p tracker

echo -e "\033[0;36mCreating Placeholder Files...\033[0m"

# user_profile.json
if [ ! -f "user_profile.json" ]; then
    echo '{"first_name": "John", "last_name": "Doe", "email": "john.doe@example.com", "phone": "+1-000-000-0000", "location": "City, Country", "linkedin": "https://linkedin.com/in/johndoe", "github": "https://github.com/johndoe", "website": "https://johndoe.me"}' > user_profile.json
    echo "  [+] Created: user_profile.json"
else
    echo "  [ok] Exists: user_profile.json"
fi

# cv_workspace/facts.txt
if [ ! -f "cv_workspace/facts.txt" ]; then
    echo "Write your career facts, skills, and experience here in plain text." > cv_workspace/facts.txt
    echo "  [+] Created: cv_workspace/facts.txt"
fi

# cv_workspace templates
if [ ! -f "cv_workspace/androidCV.tex" ]; then
    echo -e "% Placeholder Android CV Template\n\documentclass{article}\n\begin{document}\nAndroid CV Placeholder\n\end{document}" > cv_workspace/androidCV.tex
    echo "  [+] Created: cv_workspace/androidCV.tex"
fi

if [ ! -f "cv_workspace/MLCV.tex" ]; then
    echo -e "% Placeholder ML CV Template\n\documentclass{article}\n\begin{document}\nML CV Placeholder\n\end{document}" > cv_workspace/MLCV.tex
    echo "  [+] Created: cv_workspace/MLCV.tex"
fi

if [ ! -f "cv_workspace/coverletter.txt" ]; then
    echo -e "Dear [Hiring Manager],\n\nI am writing to express my interest in [Role] at [Company]..." > cv_workspace/coverletter.txt
    echo "  [+] Created: cv_workspace/coverletter.txt"
fi

echo -e "\n\033[0;32mSetup Complete! Please fill in your details in user_profile.json and cv_workspace/.\033[0m"
