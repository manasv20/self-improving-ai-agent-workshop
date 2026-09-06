"""Run a live demo learning round with temporary memory/history.

Requires the installed project and a running LM Studio server with both models.
Leaves the workshop's prompt, learnings, and scoreboard ready for the student.
"""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from unittest.mock import patch

from parcelco import data_io, history
from parcelco.doctor import check_setup
from parcelco.graphs import outer


def main() -> None:
    check_setup()
    with TemporaryDirectory(prefix="parcelco-verify-") as directory, ExitStack() as stack:
        root = Path(directory)
        shutil.copy2(data_io.PROMPT_PATH, root / "system_prompt.md")
        shutil.copy2(data_io.LEARNINGS_PATH, root / "learnings.md")
        stack.enter_context(patch.object(data_io, "PROMPT_PATH", root / "system_prompt.md"))
        stack.enter_context(patch.object(data_io, "LEARNINGS_PATH", root / "learnings.md"))
        stack.enter_context(patch.object(history, "MEMORY_DIR", root))
        stack.enter_context(patch.object(history, "ROUNDS_DB", root / "rounds.sqlite"))
        stack.enter_context(patch.dict(os.environ, {"PARCELCO_SUITE": "demo"}))
        original_run = outer.run_ticket

        def report_ticket(ticket, **kwargs):
            result = original_run(ticket, **kwargs)
            print(json.dumps({
                "ticket": result.ticket_id, "passed": result.passed,
                "heals": result.heal_count, "details": result.checklist.details,
            }), flush=True)
            return result

        stack.enter_context(patch.object(outer, "run_ticket", report_ticket))
        rows = outer.improve(rounds=1)
        print("Live verification results:", flush=True)
        print(json.dumps(rows, indent=2), flush=True)


if __name__ == "__main__":
    main()
