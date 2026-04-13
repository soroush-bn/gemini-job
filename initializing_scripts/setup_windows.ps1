# Gemini Job Agent - Windows Initialization Script
$RequiredFolders = @("cv_workspace", "jobs_evaluated", "tracker")
$RequiredFiles = @{
    "user_profile.json" = '{"first_name": "John", "last_name": "Doe", "email": "john.doe@example.com", "phone": "+1-000-000-0000", "location": "City, Country", "linkedin": "https://linkedin.com/in/johndoe", "github": "https://github.com/johndoe", "website": "https://johndoe.me"}'
    "cv_workspace/facts.txt" = "Write your career facts, skills, and experience here in plain text."
    "cv_workspace/androidCV.tex" = "% Placeholder Android CV LaTeX Template`n\documentclass{article}`n\begin{document}`nAndroid CV Placeholder`n\end{document}"
    "cv_workspace/MLCV.tex" = "% Placeholder ML CV LaTeX Template`n\documentclass{article}`n\begin{document}`nML CV Placeholder`n\end{document}"
    "cv_workspace/coverletter.txt" = "Dear [Hiring Manager],`n`nI am writing to express my interest in [Role] at [Company]..."
}

Write-Host "Creating Directories..." -ForegroundColor Cyan
foreach ($folder in $RequiredFolders) {
    if (!(Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder | Out-Null
        Write-Host "  [+] Created: $folder"
    } else {
        Write-Host "  [ok] Exists: $folder"
    }
}

Write-Host "`nCreating Placeholder Files..." -ForegroundColor Cyan
foreach ($file in $RequiredFiles.Keys) {
    if (!(Test-Path $file)) {
        $RequiredFiles[$file] | Out-File -FilePath $file -Encoding utf8
        Write-Host "  [+] Created: $file"
    } else {
        Write-Host "  [ok] Exists: $file"
    }
}

Write-Host "`nSetup Complete! Please fill in your details in user_profile.json and cv_workspace/." -ForegroundColor Green
