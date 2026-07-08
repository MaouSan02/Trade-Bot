@echo off
rem Koala scheduled run: one paper-trading cycle, output appended to koala_runs.log
cd /d C:\Users\Buzor\Trade-Bot
venv\Scripts\python.exe run_paper.py --once >> koala_runs.log 2>&1

rem Publish fresh dashboard data (no-op until a GitHub remote is configured)
git add docs/data.json >nul 2>&1
git commit -m "koala: dashboard data update" >nul 2>&1
git push >nul 2>&1
