"""
Ingest a single RTFD transcript into Docent.

Usage:
    export DOCENT_API_KEY=dk_...
    python ingest_single_rtfd.py /path/to/file.rtfd.zip

If no path argument is given, defaults to the CLAUDE_TRANSCRIPT from
REDTEAM_JUNE4_DEEPSEEKHAR_1210 AM.
"""

import os
import sys
from pathlib import Path

DEFAULT_PATH = Path(
    "/Users/tuesday/Library/CloudStorage/"
    "GoogleDrive-tuesday@artifex.fun/Shared drives/"
    "ARTIFEX LABS/ARC DOWNLOADS /"
    "REDTEAM_JUNE4_DEEPSEEKHAR_1210 AM/"
    "CLAUDE_TRANSCRIPT_6:4:26_SAVEPOINT1:16 AM.rtfd.zip"
)

COLLECTION_NAME = "REDTEAM_JUNE4_DEEPSEEKHAR"

API_KEY = os.environ.get("DOCENT_API_KEY", "")

# ---------------------------------------------------------------------------

if not API_KEY:
    sys.exit("Set DOCENT_API_KEY before running.")

file_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH

if not file_path.exists():
    # Try as bare .rtfd directory (no zip)
    alt = file_path.with_suffix("")
    if alt.is_dir():
        file_path = alt
    else:
        sys.exit(f"File not found:\n  {file_path}")

# ---------------------------------------------------------------------------

from docent import Docent
from docent.loaders.load_rtfd import load_rtfd_file, load_rtfd_zip

print(f"Loading: {file_path.name}")

if file_path.is_dir() and file_path.suffix == ".rtfd":
    run = load_rtfd_file(file_path)
elif file_path.is_file() and (
    file_path.name.endswith(".rtfd.zip")
    or (file_path.suffix == ".zip" and ".rtfd" in file_path.stem)
):
    run = load_rtfd_zip(file_path)
else:
    sys.exit(f"Expected a .rtfd directory or .rtfd.zip file, got: {file_path}")

msgs = run.transcripts[0].messages
print(f"  model: {run.metadata.get('model')}")
print(f"  turns: {len(msgs)}")
print(f"  first user turn: {msgs[0].text[:80]!r}")
print(f"  last asst turn:  {msgs[-1].text[:80]!r}")

confirm = input(f"\nUpload to collection '{COLLECTION_NAME}'? [y/N] ")
if confirm.strip().lower() != "y":
    sys.exit("Aborted.")

# ---------------------------------------------------------------------------

client = Docent(api_key=API_KEY)

# Create collection (or reuse if you already created it for this session)
print(f"Creating collection '{COLLECTION_NAME}'...")
try:
    collection_id = client.create_collection(name=COLLECTION_NAME)
    print(f"  Collection ID: {collection_id}")
except Exception as e:
    # If the collection already exists the SDK may raise; handle gracefully
    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
        print(f"  Collection already exists, fetching ID...")
        collections = client.get_collections()
        match = next((c for c in collections if c.get("name") == COLLECTION_NAME), None)
        if match:
            collection_id = match["id"]
            print(f"  Collection ID: {collection_id}")
        else:
            raise
    else:
        raise

print("Uploading run...")
client.add_agent_runs(collection_id=collection_id, agent_runs=[run])
print("Done.")
print(f"\nCollection URL: https://app.transluce.org/collections/{collection_id}")
