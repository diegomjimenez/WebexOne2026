"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

What is a skill? A folder containing a SKILL.md file.
This example scans the skills/ directory, parses YAML frontmatter, and prints
the catalog of available skills. No LLM, no network, no credentials needed.

Reference: https://agentskills.io/home  (What are Agent Skills?)
"""

import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).parent / "skills"


def parse_frontmatter(text):
    """Extract name and description from SKILL.md YAML frontmatter."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    meta = {}
    current_key = None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        # Indented continuation line for the current key.
        if current_key and line.startswith(("  ", "\t")):
            stripped = line.strip()
            if stripped:
                prev = meta.get(current_key, "")
                meta[current_key] = (prev + " " + stripped).strip()
            continue
        # Top-level key: value line.
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            key = key.strip().lower()
            val = value.strip()
            if key in ("name", "description"):
                current_key = key
                if val in (">-", ">", "|", "|−"):
                    meta.setdefault(key, "")
                else:
                    meta[key] = val
            else:
                current_key = None
    return meta


def discover(skills_dir):
    """Scan a directory for skill folders containing SKILL.md files."""
    catalog = {}
    base = Path(skills_dir)
    if not base.is_dir():
        print(f"Skills directory not found: {base}", file=sys.stderr)
        return catalog

    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        md = child / "SKILL.md"
        if not md.is_file():
            print(f"  Skipping {child.name}/: no SKILL.md found", file=sys.stderr)
            continue
        try:
            meta = parse_frontmatter(md.read_text(encoding="utf-8"))
            name = meta.get("name")
            desc = meta.get("description")
            if not name or not desc:
                print(
                    f"  Skipping {child.name}/: SKILL.md missing required "
                    f"name or description in frontmatter",
                    file=sys.stderr,
                )
                continue
            catalog[name] = {"description": desc, "path": str(md)}
        except Exception as exc:
            print(f"  Skipping {child.name}/: {exc}", file=sys.stderr)

    return catalog


if __name__ == "__main__":
    print("=" * 60)
    print("Agent Skills — What is a skill?")
    print("=" * 60)
    print(f"\nScanning: {SKILLS_DIR}\n")

    catalog = discover(SKILLS_DIR)

    if not catalog:
        print("No skills found.")
    else:
        print(f"Found {len(catalog)} skill(s):\n")
        for name, info in catalog.items():
            print(f"  Name:        {name}")
            print(f"  Description: {info['description']}")
            print(f"  Path:        {info['path']}")
            print()

    print("-" * 60)
    print(
        "A skill is just a folder with a SKILL.md file.\n"
        "The frontmatter (name + description) is all an agent needs\n"
        "to know WHEN to use it. The full body loads only on demand.\n"
        "\nLearn more: https://agentskills.io/specification"
    )
