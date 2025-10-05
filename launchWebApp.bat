@echo off
REM Launch FastAPI app (command from README)
cd /d "%~dp0"
cd app && python -m uvicorn app:app --reload
