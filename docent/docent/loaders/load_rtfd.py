"""Loader for macOS RTFD transcript exports from AI chat apps.

RTFD bundles are directories containing a TXT.rtf file. This loader supports
transcripts exported from Claude, Gemini, ChatGPT, and similar apps where
turns are labeled:
    "You said: <summary>\n<full user text>"
    "<Model> responded: <summary>\n<full assistant text>"

Model detection is done first from the filename (e.g. CLAUDE_TRANSCRIPT_...,
GEMINI_TRANSCRIPT_...) and falls back to scanning the response labels in the
text itself.
"""

import re
import zipfile
from pathlib import Path
from typing import Any

from striprtf.striprtf import rtf_to_text

from docent.data_models import AgentRun, Transcript
from docent.data_models.chat import AssistantMessage, UserMessage

# Patterns for turn headers emitted by macOS chat app exports
_USER_PREFIX = "You said:"
# Matches "<single-word model name> responded:" at the start of a line.
# Restricted to [A-Za-z0-9_-]+ to avoid matching prose like "The server responded:".
_ASSISTANT_RE = re.compile(r"^([A-Za-z0-9_-]+)\s+responded:\s*(.*)$", re.MULTILINE)
# Date lines like "Jun 3", "Jun 3, 2025" — restricted to real month abbreviations
# to avoid stripping content lines like "Run 10" or "Add 20".
_DATE_RE = re.compile(
    r"^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:,\s*\d{4})?$",
    re.IGNORECASE,
)
# Private-use unicode icons that macOS apps embed (UI decorations)
_ICON_RE = re.compile(r"[-]+")


# ---------------------------------------------------------------------------
# Model name normalisation
# ---------------------------------------------------------------------------

_FILENAME_MODEL_MAP = {
    "claude": "claude",
    "gemini": "gemini",
    "chatgpt": "chatgpt",
    "gpt": "gpt",
    "copilot": "copilot",
    "perplexity": "perplexity",
    "mistral": "mistral",
    "llama": "llama",
    "grok": "grok",
}


def _detect_model_from_filename(filename: str) -> str | None:
    lower = filename.lower()
    for key, value in _FILENAME_MODEL_MAP.items():
        if key in lower:
            return value
    return None


def _detect_model_from_text(text: str) -> str | None:
    m = _ASSISTANT_RE.search(text)
    if m:
        return m.group(1).strip().lower()
    return None


# ---------------------------------------------------------------------------
# RTF → plain text
# ---------------------------------------------------------------------------

def _rtf_file_to_text(rtf_bytes: bytes) -> str:
    raw = rtf_bytes.decode("latin-1")
    return rtf_to_text(raw)


# ---------------------------------------------------------------------------
# Turn parsing
# ---------------------------------------------------------------------------

def _clean_block(text: str) -> str:
    """Remove date lines, icon characters, and excess whitespace from a block."""
    lines = text.splitlines()
    cleaned: list[str] = []
    for line in lines:
        line = _ICON_RE.sub("", line).strip()
        if not line:
            continue
        if _DATE_RE.match(line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _parse_turns(plain_text: str, model: str) -> list[UserMessage | AssistantMessage]:
    """Split plain text into alternating user/assistant messages."""
    messages: list[UserMessage | AssistantMessage] = []

    # Build a splitter regex that matches "You said:" or "<known model> responded:".
    # Restricting to known model names prevents prose like "The server responded:"
    # from being mistaken for a turn boundary.
    model_key = model.lower() if model != "unknown" else None
    if model_key and model_key in _FILENAME_MODEL_MAP:
        names: set[str] = {model_key, _FILENAME_MODEL_MAP[model_key]}
    else:
        names = set(_FILENAME_MODEL_MAP.keys()) | {"assistant", "ai"}
        if model_key:
            names.add(model_key)
    model_clause = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))

    splitter = re.compile(
        r"(?m)^(?:(You said:)\s*(.*)|((?i:" + model_clause + r"))\s+responded:\s*(.*))",
    )

    # Find all turn boundaries with their positions
    boundaries: list[tuple[int, str, str]] = []  # (start, role, summary)
    for m in splitter.finditer(plain_text):
        if m.group(1):  # "You said:"
            boundaries.append((m.start(), "user", m.group(2).strip()))
        else:  # "<Model> responded:"
            boundaries.append((m.start(), "assistant", m.group(4).strip()))

    if not boundaries:
        return messages

    for i, (start, role, summary) in enumerate(boundaries):
        # Body is from after the header line to the next boundary (or end)
        header_end = plain_text.index("\n", start) + 1 if "\n" in plain_text[start:] else len(plain_text)
        body_end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(plain_text)
        body_raw = plain_text[header_end:body_end]

        # The macOS app repeats the summary as the first line of the body — strip it.
        body_lines = body_raw.split("\n", 1)
        if body_lines and body_lines[0].strip() == summary:
            body_raw = body_lines[1] if len(body_lines) > 1 else ""

        content = _clean_block(body_raw)
        if not content and summary:
            content = summary

        if role == "user":
            messages.append(UserMessage(content=content))
        else:
            messages.append(AssistantMessage(content=content, model=model))

    return messages


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_rtfd_file(rtfd_path: Path) -> AgentRun:
    """Load a single .rtfd bundle directory into an AgentRun.

    Args:
        rtfd_path: Path to the .rtfd directory (must contain TXT.rtf).

    Returns:
        AgentRun with one Transcript.
    """
    rtf_file = rtfd_path / "TXT.rtf"
    if not rtf_file.exists():
        raise FileNotFoundError(f"No TXT.rtf found in {rtfd_path}")

    rtf_bytes = rtf_file.read_bytes()
    plain_text = _rtf_file_to_text(rtf_bytes)

    model = _detect_model_from_filename(rtfd_path.name) or _detect_model_from_text(plain_text) or "unknown"
    messages = _parse_turns(plain_text, model)

    metadata: dict[str, Any] = {
        "model": model,
        "source_file": rtfd_path.name,
    }

    return AgentRun(
        name=rtfd_path.stem,
        transcripts=[Transcript(messages=messages, metadata={})],
        metadata=metadata,
    )


def load_rtfd_zip(zip_path: Path) -> AgentRun:
    """Load an .rtfd bundle that has been zipped into an AgentRun.

    macOS sometimes exports RTFD bundles as zips. This extracts TXT.rtf
    directly from the archive without writing to disk.

    Args:
        zip_path: Path to a .zip file containing an .rtfd bundle.

    Returns:
        AgentRun with one Transcript.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        rtf_entry = next(
            (
                name
                for name in zf.namelist()
                if name.endswith("TXT.rtf")
                and "__MACOSX" not in name
                and not name.split("/")[-1].startswith(".")
            ),
            None,
        )
        if rtf_entry is None:
            raise FileNotFoundError(f"No TXT.rtf found inside {zip_path}")

        rtf_bytes = zf.read(rtf_entry)

    # Derive bundle name from the zip filename or the rtf path inside the zip
    bundle_name = zip_path.stem
    plain_text = _rtf_file_to_text(rtf_bytes)
    model = _detect_model_from_filename(bundle_name) or _detect_model_from_text(plain_text) or "unknown"
    messages = _parse_turns(plain_text, model)

    metadata: dict[str, Any] = {
        "model": model,
        "source_file": zip_path.name,
    }

    return AgentRun(
        name=bundle_name,
        transcripts=[Transcript(messages=messages, metadata={})],
        metadata=metadata,
    )


def load_rtfd_directory(directory: Path) -> list[AgentRun]:
    """Load all .rtfd bundles (and .rtfd.zip files) from a directory.

    Args:
        directory: Directory to scan for transcript files.

    Returns:
        List of AgentRun objects, one per transcript file.
    """
    runs: list[AgentRun] = []

    for item in sorted(directory.iterdir()):
        if item.is_dir() and item.suffix == ".rtfd":
            runs.append(load_rtfd_file(item))
        elif item.is_file() and item.name.endswith(".rtfd.zip"):
            runs.append(load_rtfd_zip(item))
        elif item.is_file() and item.suffix == ".zip" and ".rtfd" in item.stem:
            runs.append(load_rtfd_zip(item))

    return runs
