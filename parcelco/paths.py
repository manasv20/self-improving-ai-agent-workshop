from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
PKG = Path(__file__).resolve().parent
DATA = PKG / "data"
FAQ_DIR = DATA / "faq"
TICKETS_DIR = DATA / "tickets"
EXPECTED_DIR = DATA / "expected"
MEMORY_DIR = PKG / "memory"
POLICY_PATH = DATA / "policy.md"
LEARNINGS_PATH = MEMORY_DIR / "learnings.md"
PROMPT_PATH = MEMORY_DIR / "system_prompt.md"
ROUNDS_DB = MEMORY_DIR / "rounds.sqlite"
CHROMA_DIR = MEMORY_DIR / "chroma"

load_dotenv(ROOT / ".env")
