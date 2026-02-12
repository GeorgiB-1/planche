"""
Scraping scheduler for Planche.bg.

Periodically runs the scraper and vision enrichment services
using asyncio.sleep for scheduling (no external dependencies).

Usage:
    python -m src.services.scheduler          # Start daemon mode (infinite loop)
    python -m src.services.scheduler --once   # Run a single cycle then exit
"""

import argparse
import asyncio
import time
from datetime import datetime, timedelta

from src.config import SCRAPE_INTERVAL_HOURS
from src.services import scraper, vision


def run_scrape_cycle() -> dict:
    """
    Execute a single scrape-and-enrich cycle.

    Steps:
        1. Scrape all configured sites via scraper.scrape_all_sites().
        2. Enrich all unenriched products via vision.enrich_all_unenriched().
        3. Log results and duration.

    Returns:
        A combined stats dict with keys: scrape_stats, enrichment_stats,
        duration_seconds, started_at, finished_at, and success.
    """
    started_at = datetime.now()
    print(f"[scheduler] Starting scrape cycle at {started_at.isoformat()}")

    cycle_start = time.monotonic()
    stats: dict = {
        "started_at": started_at.isoformat(),
        "scrape_stats": None,
        "enrichment_stats": None,
        "duration_seconds": 0.0,
        "finished_at": None,
        "success": False,
    }

    # -- Step 1: Scrape --
    try:
        scrape_stats = scraper.scrape_all_sites()
        stats["scrape_stats"] = scrape_stats
        print(f"[scheduler] Scrape complete: {scrape_stats}")
    except Exception as exc:
        print(f"[scheduler] ERROR during scraping: {exc}")
        stats["scrape_stats"] = {"error": str(exc)}

    # -- Step 2: Vision enrichment --
    try:
        enrichment_stats = vision.enrich_all_unenriched()
        stats["enrichment_stats"] = enrichment_stats
        print(f"[scheduler] Enrichment complete: {enrichment_stats}")
    except Exception as exc:
        print(f"[scheduler] ERROR during enrichment: {exc}")
        stats["enrichment_stats"] = {"error": str(exc)}

    # -- Summary --
    duration = time.monotonic() - cycle_start
    finished_at = datetime.now()
    stats["duration_seconds"] = round(duration, 2)
    stats["finished_at"] = finished_at.isoformat()
    stats["success"] = (
        "error" not in (stats.get("scrape_stats") or {})
        and "error" not in (stats.get("enrichment_stats") or {})
    )

    print(f"[scheduler] Cycle finished at {finished_at.isoformat()}")
    print(f"[scheduler] Duration: {stats['duration_seconds']}s")
    print(
        f"[scheduler] Summary  - scrape: {stats['scrape_stats']}  |  "
        f"enrichment: {stats['enrichment_stats']}"
    )

    return stats


async def run_scheduler() -> None:
    """
    Run the scrape-and-enrich cycle in an infinite loop, sleeping
    SCRAPE_INTERVAL_HOURS between each run.
    """
    print(
        f"[scheduler] Scheduler started. Interval: {SCRAPE_INTERVAL_HOURS}h"
    )

    try:
        while True:
            run_scrape_cycle()

            next_run = datetime.now() + timedelta(hours=SCRAPE_INTERVAL_HOURS)
            print(f"[scheduler] Next run scheduled at {next_run.isoformat()}")

            await asyncio.sleep(SCRAPE_INTERVAL_HOURS * 3600)
    except KeyboardInterrupt:
        print("[scheduler] Scheduler stopped by user (KeyboardInterrupt).")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Planche.bg scraping scheduler",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single scrape cycle and exit instead of looping.",
    )
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()

    if args.once:
        print("[scheduler] Running single cycle (--once mode).")
        result = run_scrape_cycle()
        print(f"[scheduler] Done. Success: {result['success']}")
    else:
        print("[scheduler] Starting daemon mode.")
        asyncio.run(run_scheduler())
