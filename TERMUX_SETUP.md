# Koala on Android/Termux — 24/7 Server Setup (exact guide)

This is the project-specific version of the general "Android phone as bot server"
guide. Phases 0–4 and 10 are unchanged from the general guide. Phases 5–9 (and the
Phase 11 checklist) use Koala's real files, commands, and paths — follow them as
written, no substitutions needed.

**Architecture note (read first):** Koala is NOT one long-running `main.py`.
It has two parts, and the guide reflects this:

1. **The trader** — `python run_paper.py --once` — runs one full cycle (all 3
   coins) and exits. It is fired **every 4 hours by cron** via `run_koala.sh`,
   which also pushes fresh dashboard data to GitHub.
   ⚠️ Never leave `python run_paper.py` (without `--once`) running unattended —
   loop mode re-reports to Notion/dashboard every 60 seconds and will flood them.
2. **The Telegram listener** — `python run_listener.py` — the only long-running
   process. It answers your `/update` messages. This is what Termux:Boot starts
   and what the watchdog guards.

---

## PHASE 0 — Phone Prep

1. **Factory reset the phone** (if it's not already clean) — Settings → System → Reset options → Erase all data.
2. **Update Android** to the latest version available for the device.
3. **Sign in with a Google account** (or skip — Termux doesn't need Play services).
4. **Turn on the SIM's mobile data**; Wi-Fi optional (Android uses Wi-Fi when available, SIM as fallback).
5. **Disable lock screen** (Settings → Security → Screen lock → None).
6. **Settings → Display → Screen timeout → "Never"** (recommended for dedicated hardware).
7. Battery optimization: leave for now — Termux-specific exceptions come in Phase 3.
8. **Developer Options** (tap Build Number 7×) → enable **Stay awake**, optionally **USB debugging**.

## PHASE 1 — Install Termux (correct source only)

⚠️ **Do NOT install Termux from Google Play** — that build is outdated/broken.

1. Install **F-Droid** from `f-droid.org` (allow "install unknown apps" when prompted).
2. Let F-Droid update its index.
3. Install: **Termux**, **Termux:Boot**, **Termux:API**.
4. Open Termux once to finish first-time setup.

## PHASE 2 — Termux Initial Setup

```bash
termux-setup-storage
pkg update -y && pkg upgrade -y
pkg install -y git wget curl nano
```

## PHASE 3 — Battery/Background Settings (critical — do not skip)

1. Settings → Apps → **Termux** → Battery → **Unrestricted**.
2. Settings → Apps → **Termux:Boot** → Battery → **Unrestricted**.
3. Check **dontkillmyapp.com** for your phone brand's extra autostart/background toggles.
4. Pin/lock Termux in the Recent Apps screen if your phone supports it.

## PHASE 4 — Install Python Runtime

```bash
pkg install -y python
python --version
pip install --upgrade pip
```

---

## PHASE 5 — Get Koala onto the Phone

### 5.0 ⚠️ Cutover — shut down the laptop copy FIRST

Two Koalas running at once means duplicate Notion rows, git push conflicts, and a
broken Telegram listener (two pollers fight over the same bot and both go deaf).
On the **laptop**, before the phone goes live:

```powershell
# stop the 4-hourly trading runs
schtasks /Change /TN "Koala Paper Trader" /DISABLE
# stop the running Telegram listener
Get-Process pythonw -ErrorAction SilentlyContinue | Stop-Process -Force
# stop it from auto-starting at logon
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\koala_listener.vbs"
```

(Reverse these if you ever move Koala back to the laptop.)

### 5.1 Clone the repo

```bash
cd ~
git clone https://github.com/MaouSan02/Trade-Bot.git
cd Trade-Bot
```

The folder is `~/Trade-Bot` — every later phase assumes this path.

### 5.2 Install dependencies (Termux-specific — do NOT just pip install)

`requirements.txt` (ccxt + pandas) is correct on PC, but on Termux
`pip install -r requirements.txt` will try to **compile pandas and several C/Rust
extensions from source and fail (or take hours)**. Use Termux's prebuilt packages
plus a slim ccxt install instead:

```bash
# Termux User Repository (has prebuilt pandas for ARM)
pkg install -y tur-repo
pkg update -y
pkg install -y python-numpy python-pandas python-cryptography

# ccxt WITHOUT its heavy async deps (aiohttp/aiodns need C builds).
# Koala only uses ccxt's synchronous REST API, which runs on `requests`.
pip install requests certifi setuptools typing-extensions
pip install --no-deps ccxt
```

Verify before moving on:

```bash
python -c "import ccxt, pandas; print('ccxt', ccxt.__version__, '| pandas', pandas.__version__)"
```

### 5.3 Secrets — create `.env` (gitignored, so NOT in the clone)

```bash
nano .env
```

Paste exactly these three lines, with the real values copied from the laptop's
`C:\Users\Buzor\Trade-Bot\.env`:

```
NOTION_TOKEN=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

Save: Ctrl+O, Enter, Ctrl+X.

### 5.4 Wallet state — transfer `paper_wallet.json` (also gitignored!)

This file holds Koala's open positions (it currently holds ETH and BTC).
Skipping this step makes the phone-Koala forget them and start fresh.

```bash
nano paper_wallet.json
```

Paste the exact contents of the laptop's `C:\Users\Buzor\Trade-Bot\paper_wallet.json`,
save, exit.

### 5.5 Git push access (dashboard updates depend on this)

The phone needs its own GitHub credential — the laptop's is not transferable.
Create a **fine-grained personal access token** at
github.com → Settings → Developer settings → Personal access tokens →
Fine-grained tokens → Generate: repository `MaouSan02/Trade-Bot` only,
permission **Contents: Read and write**.

```bash
git config user.name "Buzor"
git config user.email "foodlordsensei@gmail.com"
git config credential.helper store
```

The first `git push` (Phase 6) will prompt: username `MaouSan02`, password = the
token. It's then stored and never asked again.

---

## PHASE 6 — Test Run (before automating anything)

One full trading cycle (all three coins, then exits):

```bash
cd ~/Trade-Bot
python run_paper.py --once
```

Expected output: one `Koala single run...` line, then one HOLD/BUY/SELL line per
coin (BTC, ETH, DOGE) with no `WARN:` lines. Notion's Run Journal should gain
3 rows.

Then test the full scheduled path including the dashboard push:

```bash
sh run_koala.sh
git log --oneline -1     # should show "koala: dashboard data update"
```

Confirm the commit appears on github.com/MaouSan02/Trade-Bot and the dashboard
(maousan02.github.io/Trade-Bot) shows the fresh check-in / Online pill.

Finally test the listener:

```bash
python run_listener.py
```

Send `update` to @koala_update_bot from Telegram — a status reply should arrive.
Ctrl+C to stop it (Phase 7 automates it).

---

## PHASE 7 — Auto-Start on Boot (Termux:Boot)

```bash
mkdir -p ~/.termux/boot
nano ~/.termux/boot/start-koala.sh
```

Paste:

```bash
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
crond
if ! pgrep -f "run_listener.py" > /dev/null; then
  cd ~/Trade-Bot
  nohup python run_listener.py > /dev/null 2>&1 &
fi
```

(The listener writes its own log to `~/Trade-Bot/listener.log`; the trading runs
are cron's job in Phase 8, so boot only needs wake-lock + crond + listener.)

```bash
chmod +x ~/.termux/boot/start-koala.sh
```

**Reboot the phone once** to confirm: within a minute of boot, `/update` in
Telegram should get a reply.

---

## PHASE 8 — Cron: Trading Schedule + Watchdog

```bash
pkg install -y cronie termux-services
sv-enable crond    # or just run: crond
```

Watchdog (guards the listener; the 4-hourly trader is fire-and-exit and needs no
guard — a failed run simply retries next candle):

```bash
nano ~/watchdog.sh
```

```bash
#!/data/data/com.termux/files/usr/bin/bash
if ! pgrep -f "run_listener.py" > /dev/null; then
  termux-wake-lock
  cd ~/Trade-Bot
  nohup python run_listener.py > /dev/null 2>&1 &
fi
# Healthchecks.io dead-man ping (Phase 9) - phone alive = ping every 5 min
curl -fsS -m 10 --retry 3 https://hc-ping.com/YOUR-UNIQUE-CHECK-ID > /dev/null
```

Note the pgrep string: the process appears as `python run_listener.py`, so the
guide's original `pgrep -f "python main.py"` would never match — use
`run_listener.py` as shown.

```bash
chmod +x ~/watchdog.sh
crontab -e
```

Add **both** lines:

```
*/5 * * * * sh ~/watchdog.sh
10 1,5,9,13,17,21 * * * sh ~/Trade-Bot/run_koala.sh
```

The second line is the trading schedule: 10 minutes past each 4h candle close,
**in Africa/Lagos (WAT, UTC+1) local time**. Run `date` on the phone first — if
the phone's timezone is not WAT, shift the hours so they land at
00:10/04:10/08:10/12:10/16:10/20:10 **UTC**.

---

## PHASE 9 — Crash/Downtime Alerts

### Telegram alerts — already built in, nothing to add

Koala ships with full Telegram integration (`bot/notifier.py` + the listener):
- every BUY/SELL pushes an alert automatically,
- `/update` or `update` returns wallet/positions/prices/countdown on demand,
- reporting failures are logged with `WARN:` in `koala_runs.log`.

The bot token and chat ID come from `.env` (Phase 5.3) — do not hardcode them.

### Dead-man's-switch monitoring (Healthchecks.io — free tier)

1. Sign up at `healthchecks.io`, create a check named "Koala phone", schedule:
   every 5 minutes, grace: 15 minutes.
2. Copy its ping URL into the `hc-ping.com/YOUR-UNIQUE-CHECK-ID` line already in
   `~/watchdog.sh` (Phase 8).
3. If the phone dies, loses data, or Termux is killed, you get an email within
   ~20 minutes. (The dashboard's Online/Offline pill gives the same signal at
   4-hour granularity — Healthchecks is the fast alarm.)

---

## PHASE 10 — (Optional) Remote Access via Tailscale

```bash
pkg install -y tailscale
tailscale up
```

Follow the login link; the phone gets a private IP reachable from your laptop for
SSH/log-checking. (The dashboard needs no Tailscale — it's public GitHub Pages.)

---

## PHASE 11 — Final Verification Checklist

- [ ] Phone reboots → `/update` in Telegram answers within ~1 minute (Termux:Boot works)
- [ ] `pkill -f run_listener.py` → watchdog revives it within 5 minutes (`/update` answers again)
- [ ] Wait for a scheduled slot (…:10 past a 4h candle) → 3 new rows in Notion Run Journal + new commit on GitHub + dashboard pill shows Online with fresh check-in
- [ ] Turn Wi-Fi off → confirm SIM data keeps `/update` working
- [ ] `tail -n 30 ~/Trade-Bot/koala_runs.log` after a day — runs every 4h, no `WARN:`/`ERROR` lines
- [ ] Healthchecks.io shows "up"; laptop's scheduled task still shows **Disabled**

**Files Koala writes (all inside `~/Trade-Bot`, all Termux-writable):**
`paper_wallet.json` (positions — the critical one), `trades.log`,
`koala_runs.log`, `listener.log`, `docs/data.json` (pushed to GitHub).
Nothing is written outside the repo folder; no `/proc`, systemd, GUI, or
Windows-only dependency is used at runtime. `run_koala.bat` and `venv/` are
Windows leftovers — ignore them on the phone.
