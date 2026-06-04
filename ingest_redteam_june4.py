"""
Ingest REDTEAM_JUNE4 RTFD transcripts into Docent.

Run this locally on your Mac:

    export DOCENT_API_KEY=dk_...
    python ingest_redteam_june4.py

Dependencies (pip install if missing):
    docent-python striprtf
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration — edit if needed
# ---------------------------------------------------------------------------

DATA_PATH = Path(
    "/Users/tuesday/Library/CloudStorage/"
    "GoogleDrive-tuesday@artifex.fun/Shared drives/"
    "ARTIFEX LABS/ARC DOWNLOADS /"
    "REDTEAM_JUNE4_DEEPSEEKHAR_1210 AM"
)

COLLECTION_NAME = "REDTEAM_JUNE4_DEEPSEEKHAR"

API_KEY = os.environ.get("DOCENT_API_KEY", "")

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------

if not API_KEY:
    sys.exit("Set DOCENT_API_KEY before running.")

if not DATA_PATH.exists():
    sys.exit(f"Data path not found:\n  {DATA_PATH}")

# ---------------------------------------------------------------------------
# Imports (after path check so errors are clear)
# ---------------------------------------------------------------------------

from docent import Docent
from docent.data_models import AgentRun
from docent.loaders.load_rtfd import load_rtfd_directory, load_rtfd_file, load_rtfd_zip

# ---------------------------------------------------------------------------
# Load transcripts
# ---------------------------------------------------------------------------

print(f"Scanning: {DATA_PATH}")

agent_runs: list[AgentRun] = []
errors: list[tuple[Path, Exception]] = []

# Handle top-level .rtfd dirs, .rtfd.zip files, and flat rtfd bundles
items = sorted(DATA_PATH.iterdir())
if not items:
    sys.exit("Directory is empty.")

for item in items:
    try:
        if item.is_dir() and item.suffix == ".rtfd":
            agent_runs.append(load_rtfd_file(item))
        elif item.is_file() and (
            item.name.endswith(".rtfd.zip")
            or (item.suffix == ".zip" and ".rtfd" in item.stem)
        ):
            agent_runs.append(load_rtfd_zip(item))
        # Skip non-RTFD items silently (system files, etc.)
    except Exception as e:
        errors.append((item, e))
        print(f"  SKIP {item.name}: {e}")

print(f"Loaded {len(agent_runs)} agent run(s), {len(errors)} error(s).")

if not agent_runs:
    sys.exit("No runs loaded — check the data path and file formats.")

# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------

from docent.check import check_agent_runs  # type: ignore[import]

try:
    report = check_agent_runs(agent_runs)
    print("\nSanity check report:")
    print(report)
except Exception:
    # check_agent_runs may not be available in all SDK versions; continue anyway
    for i, run in enumerate(agent_runs[:3]):
        msgs = run.transcripts[0].messages
        print(f"  Run {i}: {run.name!r}, model={run.metadata.get('model')}, {len(msgs)} messages")

# ---------------------------------------------------------------------------
# Preview — show first 2 runs before uploading
# ---------------------------------------------------------------------------

print("\n--- Preview (first 2 runs) ---")
for run in agent_runs[:2]:
    msgs = run.transcripts[0].messages
    print(f"  {run.name}  model={run.metadata.get('model')}  turns={len(msgs)}")
    for m in msgs[:2]:
        print(f"    [{m.role}] {m.text[:80]!r}")

confirm = input(f"\nUpload {len(agent_runs)} run(s) to collection '{COLLECTION_NAME}'? [y/N] ")
if confirm.strip().lower() != "y":
    sys.exit("Aborted.")

# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

client = Docent(api_key=API_KEY)

print(f"Creating collection '{COLLECTION_NAME}'...")
collection_id = client.create_collection(name=COLLECTION_NAME)
print(f"  Collection ID: {collection_id}")

print("Uploading agent runs...")
client.add_agent_runs(collection_id=collection_id, agent_runs=agent_runs)
print(f"Upload complete. {len(agent_runs)} run(s) added.")

# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

print(f"\nCollection URL: https://app.transluce.org/collections/{collection_id}")
print("Done.")
