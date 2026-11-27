# JobDisha India - PowerShell Runner
Set-Location -Path $PSScriptRoot
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      Starting JobDisha India (FastAPI + Turso Cloud)    " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Website will open at: http://localhost:8000" -ForegroundColor Yellow
Write-Host "Admin Portal at:     http://localhost:8000/admin" -ForegroundColor Yellow
Write-Host ""
python main.py

