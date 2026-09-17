Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "          STARTING TRADE MATRIX SYSTEM" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1/2] Starting Backend on http://127.0.0.1:8000..." -ForegroundColor Green
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", ".\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000"

Write-Host "[2/2] Starting Frontend on http://localhost:3000..." -ForegroundColor Green
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "npm run dev"

Write-Host ""
Write-Host "Both services are launching in separate windows!" -ForegroundColor Yellow
Write-Host "Backend API: http://127.0.0.1:8000" -ForegroundColor Gray
Write-Host "Frontend UI: http://localhost:3000" -ForegroundColor Gray
