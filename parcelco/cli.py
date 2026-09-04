from __future__ import annotations

import argparse
import json
import os
import sys

from parcelco.paths import ROOT


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="parcelco", description="ParcelCo self-improving support flywheel")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_base = sub.add_parser("baseline", help="Run baseline suite eval")
    p_base.add_argument("--suite", choices=("demo", "full"), default=None, help="Override PARCELCO_SUITE")

    p_imp = sub.add_parser("improve", help="Run outer improve loop")
    p_imp.add_argument("--rounds", type=int, default=None)
    p_imp.add_argument("--suite", choices=("demo", "full"), default=None, help="Override PARCELCO_SUITE")

    sub.add_parser("reset", help="Reset prompt/learnings/history")
    p_serve = sub.add_parser("serve", help="Start Flask dashboard")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=5050)
    p_serve.add_argument("--suite", choices=("demo", "full"), default=None, help="Override PARCELCO_SUITE")

    args = parser.parse_args(argv)

    # Ensure .env loaded via paths import side effect
    _ = ROOT

    if getattr(args, "suite", None):
        os.environ["PARCELCO_SUITE"] = args.suite

    if args.cmd == "baseline":
        from parcelco.data_io import suite_info
        from parcelco.graphs.outer import baseline

        print(json.dumps(suite_info(), indent=2))
        result = baseline()
        print(json.dumps({k: result[k] for k in ("round", "part_a_rate", "part_b_rate")}, indent=2))
        return

    if args.cmd == "improve":
        from parcelco.data_io import suite_info
        from parcelco.graphs.outer import improve

        print(json.dumps(suite_info(), indent=2))
        rows = improve(rounds=args.rounds)
        print(json.dumps(rows, indent=2))
        return

    if args.cmd == "reset":
        from parcelco.graphs.outer import reset_all

        reset_all()
        print("reset ok")
        return

    if args.cmd == "serve":
        from parcelco.data_io import suite_info
        from parcelco.web.app import app

        info = suite_info()
        print(f"ParcelCo dashboard → http://{args.host}:{args.port}")
        print(f"LLM: {os.getenv('PARCELCO_MODEL')} @ {os.getenv('OPENAI_BASE_URL')}")
        print(f"Suite: {info['mode']} — {info['active_improve']}A / {info['active_holdout']}B (catalog {info['catalog_total']})")
        app.run(host=args.host, port=args.port, debug=False, threaded=True)
        return

    parser.error(f"unknown command {args.cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
