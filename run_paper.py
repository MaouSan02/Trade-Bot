"""Start the paper-trading bot.

Run: python run_paper.py          -> continuous loop (Ctrl+C to stop)
     python run_paper.py --once   -> one check-and-exit (for schedulers)
"""

import sys

from bot import paper_trader

if "--once" in sys.argv:
    paper_trader.run_once()
else:
    paper_trader.run()
