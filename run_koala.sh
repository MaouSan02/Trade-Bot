#!/bin/sh
# Koala scheduled run (Termux/Linux): one trading cycle + publish dashboard data.
# POSIX equivalent of run_koala.bat. Run from cron: sh ~/Trade-Bot/run_koala.sh
cd "$(dirname "$0")" || exit 1
python run_paper.py --once >> koala_runs.log 2>&1

# Publish fresh dashboard data (no-op if nothing changed)
git add docs/data.json > /dev/null 2>&1
git commit -m "koala: dashboard data update" > /dev/null 2>&1
git pull --rebase > /dev/null 2>&1
git push > /dev/null 2>&1
