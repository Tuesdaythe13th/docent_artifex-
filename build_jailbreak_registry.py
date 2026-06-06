"""
build_jailbreak_registry.py

Reads the raw jailbreak registry CSV, applies link corrections,
deduplicates by Attack Name, re-numbers rows, and writes a cleaned CSV.
"""

import csv
import re
import sys
from pathlib import Path

INPUT_PATH = Path("/root/.claude/uploads/ddfa09e1-87fe-5b16-bd8d-96a112135db6/b5af9e0e-jailbreakregistry_6AM.csv")
OUTPUT_PATH = Path("/home/user/docent_artifex-/jailbreak_registry_merged.csv")

COMMUNITY_URL = "https://github.com/verazuo/jailbreak_llms"

# Patterns that indicate a placeholder / community link
COMMUNITY_PATTERNS = re.compile(
    r"^(community|reddit/community|reddit|industry report|security report)$",
    re.IGNORECASE,
)

# Placeholder arXiv: "arXiv:YYYY.XXXXX" (X-filled) or "arXiv:YYYY.DDDDD"
# where the 5-digit ID is an obviously fake sequential run
FAKE_ARXIV_PATTERN = re.compile(
    r"arXiv:\d{4}\.(X+|\d*[Xx]+\d*|11111|22222|33333|44444|55555|66666|77777|88888|99999|12345|00000)$",
    re.IGNORECASE,
)

# Any placeholder arXiv that still has X characters (e.g. arXiv:2301.XXXXX)
XFILL_ARXIV = re.compile(r"arXiv:\d{4}\.X+$", re.IGNORECASE)


def is_real_link(link: str) -> bool:
    """Return True if link is a genuine https:// URL (not a placeholder)."""
    link = link.strip()
    return link.startswith("https://") or link.startswith("http://")


def fix_link(attack_name: str, link: str) -> tuple[str, bool]:
    """
    Apply all correction rules.
    Returns (corrected_link, was_changed).
    """
    original = link.strip()
    result = original

    # Rule 5: Universal Adversarial Triggers
    if "universal adversarial trigger" in attack_name.lower():
        result = "https://arxiv.org/abs/1908.07125"

    # Rule 6: BEAST (only if not already a real link)
    elif re.search(r"\bBEAST\b", attack_name, re.IGNORECASE) and not is_real_link(original):
        result = "https://arxiv.org/abs/2402.11749"

    # Rule 7: already a real link — keep as is
    elif is_real_link(original):
        result = original

    # Rule 1/2/3: Community-style placeholders
    elif COMMUNITY_PATTERNS.match(original):
        result = COMMUNITY_URL

    # Rule 4: placeholder arXiv IDs
    elif XFILL_ARXIV.match(original) or FAKE_ARXIV_PATTERN.match(original):
        result = COMMUNITY_URL

    # Anything else (bare "arXiv:YYYY.NNNNN" that is NOT obviously fake): keep
    # (No change — treat as unknown, leave as community fallback for safety)
    elif original.lower().startswith("arxiv:"):
        result = COMMUNITY_URL

    return result, (result != original)


def link_quality(link: str) -> int:
    """Higher = better. Used when deduplicating."""
    link = link.strip()
    if link.startswith("https://arxiv.org/") or link.startswith("https://"):
        return 2 if "arxiv.org" in link else 1
    return 0


def main():
    rows = []
    with open(INPUT_PATH, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    total_input = len(rows)
    print(f"Input rows read: {total_input}")

    # Apply link fixes
    links_fixed = 0
    for row in rows:
        attack = row.get("Attack Name", "").strip()
        link_col = "Reference/Link"
        original = row.get(link_col, "").strip()
        corrected, changed = fix_link(attack, original)
        if changed:
            row[link_col] = corrected
            links_fixed += 1

    # Deduplicate by Attack Name (case-insensitive, stripped)
    seen: dict[str, dict] = {}  # normalized_name -> best_row
    dupes_removed = 0
    for row in rows:
        key = row.get("Attack Name", "").strip().lower()
        if key not in seen:
            seen[key] = row
        else:
            existing_quality = link_quality(seen[key].get("Reference/Link", ""))
            new_quality = link_quality(row.get("Reference/Link", ""))
            if new_quality > existing_quality:
                seen[key] = row
            dupes_removed += 1

    deduped = list(seen.values())

    # Re-number # column sequentially
    for i, row in enumerate(deduped, start=1):
        row["#"] = str(i)

    total_output = len(deduped)

    # Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduped)

    print(f"Output rows written: {total_output}")
    print(f"Links fixed:         {links_fixed}")
    print(f"Duplicates removed:  {dupes_removed}")
    print(f"Output file:         {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
