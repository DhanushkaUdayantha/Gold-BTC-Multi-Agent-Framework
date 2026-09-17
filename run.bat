@echo off
title Trade Matrix Starter
echo =======================================================
echo          STARTING TRADE MATRIX SYSTEM
echo =======================================================
echo.

echo [1/2] Starting Backend API (http://127.0.0.1:8000)...
start "Trade Matrix Backend" cmd /k ".\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000"

echo [2/2] Starting Frontend UI (http://localhost:3000)...
start "Trade Matrix Frontend" cmd /k "npm run dev"

echo.
echo =======================================================
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:3000
echo =======================================================
echo Services launched. You can open http://localhost:3000 in your browser!
