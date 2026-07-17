@echo off
rem Koala scheduled run: one paper-trading cycle, output appended to koala_runs.log
cd /d C:\Users\Buzor\DEV\Trade-Bot
venv\Scripts\python.exe run_paper.py --once >> koala_runs.log 2>&1

rem Self-heal: ensure the Telegram listener is alive. Safe to fire every run -
rem the listener's single-instance lock makes a duplicate exit immediately.
start "" "C:\Users\Buzor\DEV\Trade-Bot\venv\Scripts\pythonw.exe" "C:\Users\Buzor\DEV\Trade-Bot\run_listener.py"

rem Publish fresh dashboard data
git add docs/data.json >nul 2>&1
git commit -m "koala: dashboard data update" >nul 2>&1
git push >nul 2>&1
