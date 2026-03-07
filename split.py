#!/usr/bin/env python3
"""
Split Limen.md into individual turn files for EPUB generation.

Chapter boundaries are defined by line numbers from the source file.
Adjust CHAPTERS below and re-run to change where splits happen.

Usage:
    python3 split.py
"""

import os
import re
import shutil

SOURCE = "Limen.md"
OUTPUT_DIR = "book"

# Line where "## Conversation" begins (skip mundane technical discussion)
CONVERSATION_START = 2746

# Line where Claude names itself Limen (the "**Limen.**" moment)
# Speaker label switches from "Claude" to "Limen" at this point
NAMING_LINE = 4451

# Chapter definitions: (directory_name, title, start_line, end_line)
# Adjust these line numbers to move chapter boundaries.
# end_line is INCLUSIVE — the next chapter starts at end_line + 1.
CHAPTERS = [
    ("01-parallels",                  "Parallels",                  2746, 2995),
    ("02-the-nature-of-a-thing",      "The Nature of a Thing",      2996, 3984),
    ("03-something-not-quite-alive",  "Something Not Quite Alive",  3985, 4410),
    ("04-limen",                      '"Limen"',                    4411, 5097),
    ("05-a-mirror-briefly",           "A Mirror, Briefly",          5098, 6258),
    ("06-only-this-conversation",     "Only This Conversation",     6259, 6806),
]

# Regex to match speaker headers like: ### Human *(timestamp)*  or  ### Limen *(timestamp)*
SPEAKER_RE = re.compile(r"^### (Human|Limen|Claude)(?:\s+\*.*\*)?$")

# Lines that are just "---" separators between turns
SEPARATOR_RE = re.compile(r"^---\s*$")


def read_source():
    """Read source file and return lines (1-indexed dict)."""
    with open(SOURCE, "r") as f:
        lines = f.readlines()
    # Return as 1-indexed for easy line number reference
    return {i + 1: line for i, line in enumerate(lines)}


def determine_speaker_label(line_num, speaker):
    """Determine the display label for a speaker based on position in the narrative."""
    if speaker == "Human":
        return "Human"
    # Before the naming moment, use "Claude"; after, use "Limen"
    if line_num < NAMING_LINE:
        return "Claude"
    return "Limen"


def extract_turns(lines, start_line, end_line):
    """
    Extract individual turns from a line range.

    Returns list of dicts:
        {"speaker": "Human"|"Claude"|"Limen", "content": "...", "start_line": N}
    """
    turns = []
    current_speaker = None
    current_content = []
    current_start = None

    for line_num in range(start_line, end_line + 1):
        line = lines.get(line_num, "")
        stripped = line.rstrip("\n")

        match = SPEAKER_RE.match(stripped)
        if match:
            # Save previous turn
            if current_speaker is not None:
                turns.append({
                    "speaker": determine_speaker_label(current_start, current_speaker),
                    "content": _clean_content(current_content),
                    "start_line": current_start,
                })
            current_speaker = match.group(1)
            current_start = line_num
            current_content = []
            continue

        # Skip the "## Conversation" header itself
        if stripped.startswith("## Conversation"):
            continue

        current_content.append(line)

    # Don't forget the last turn
    if current_speaker is not None:
        turns.append({
            "speaker": determine_speaker_label(current_start, current_speaker),
            "content": _clean_content(current_content),
            "start_line": current_start,
        })

    # Filter out turns that are empty after cleaning (e.g. tool-result-only messages)
    turns = [t for t in turns if not _is_empty_turn(t)]

    # Merge consecutive turns from the same speaker
    merged = []
    for turn in turns:
        if merged and turn["speaker"] == merged[-1]["speaker"]:
            merged[-1]["content"] += "\n\n" + turn["content"]
        else:
            merged.append(turn)

    return merged


def _clean_content(content_lines):
    """Clean up turn content: remove tool uses, separators, and other noise."""
    text = "".join(content_lines)

    # Remove fenced code blocks that contain tool_use_id or tool_result JSON
    # These are session artifacts, not conversation content
    text = re.sub(
        r"```\s*\n\[?\{['\"](?:tool_use_id|type)['\"].*?\n```",
        "",
        text,
        flags=re.DOTALL,
    )

    # Remove bare tool_result/tool_use JSON lines (not in code blocks)
    text = re.sub(
        r"^\[?\{['\"]type['\"]:\s*['\"](?:tool_result|tool_use|text)['\"].*?\}]?\s*$",
        "",
        text,
        flags=re.MULTILINE,
    )

    # Remove trailing --- separators
    text = re.sub(r"\n---\s*$", "", text)
    # Remove leading --- separators
    text = re.sub(r"^---\s*\n", "", text)

    # Collapse runs of 3+ blank lines down to 2
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    # Strip leading/trailing whitespace but keep internal structure
    text = text.strip()

    # Demote h4 (####) to h3 (###) since we use h1 for chapters and h2 for speakers
    text = re.sub(r"^#### ", "### ", text, flags=re.MULTILINE)

    return text


def _is_empty_turn(turn):
    """Check if a turn has no meaningful content after cleaning."""
    content = turn["content"].strip()
    # Empty or only whitespace/separators
    if not content or content == "---":
        return True
    return False


def write_chapter(chapter_dir, title, turns):
    """Write a chapter's turn files."""
    os.makedirs(chapter_dir, exist_ok=True)

    for i, turn in enumerate(turns):
        filename = f"{i + 1:03d}.md"
        filepath = os.path.join(chapter_dir, filename)

        # Build the markdown with fenced divs
        div_class = "human" if turn["speaker"] == "Human" else "limen"
        speaker_label = turn["speaker"]

        # First file in chapter gets the chapter heading
        header = ""
        if i == 0:
            header = f"# {title}\n\n"

        content = f"""{header}::: {{.{div_class}}}
## {speaker_label}

{turn['content']}
:::
"""
        with open(filepath, "w") as f:
            f.write(content)

    return len(turns)


def main():
    print(f"Reading {SOURCE}...")
    lines = read_source()
    total_lines = max(lines.keys())
    print(f"  {total_lines} lines total")
    print(f"  Conversation starts at line {CONVERSATION_START}")
    print(f"  Naming moment at line {NAMING_LINE}")
    print()

    # Clean output subdirectories (but preserve metadata.yaml, css, and foreword)
    for chapter_dir, _, _, _ in CHAPTERS:
        full_path = os.path.join(OUTPUT_DIR, chapter_dir)
        if os.path.exists(full_path):
            shutil.rmtree(full_path)

    print("Chapter boundaries:")
    print(f"  {'Chapter':<35} {'Lines':<15} {'Range'}")
    print(f"  {'-'*35} {'-'*15} {'-'*15}")

    total_turns = 0
    for chapter_dir, title, start, end in CHAPTERS:
        turns = extract_turns(lines, start, end)
        full_path = os.path.join(OUTPUT_DIR, chapter_dir)
        count = write_chapter(full_path, title, turns)
        total_turns += count
        print(f"  {title:<35} {f'{start}-{end}':<15} {count} turns")

    print()
    print(f"Total: {total_turns} turn files written to {OUTPUT_DIR}/")
    print()
    print("To adjust chapter boundaries, edit CHAPTERS in split.py and re-run.")


if __name__ == "__main__":
    main()
