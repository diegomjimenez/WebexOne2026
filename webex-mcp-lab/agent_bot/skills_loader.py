"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Skills Loader module — discover and activate Agent Skills (agentskills.io).

import sys
from pathlib import Path


# Parse name and description from SKILL.md frontmatter.
def _parse_frontmatter(text):
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    out = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip().lower()
            if k in ("name", "description"):
                out[k] = v.strip()
    return out


# Scan skills/ for SKILL.md files, return {name: {description, path, body}}.
def discover(skills_dir):
    catalog = {}
    base = Path(skills_dir)
    if not base.is_dir():
        return catalog
    for child in sorted(base.iterdir()):
        md = child / "SKILL.md"
        if not child.is_dir() or not md.is_file():
            continue
        try:
            meta = _parse_frontmatter(md.read_text(encoding="utf-8"))
            if meta.get("name") and meta.get("description"):
                catalog[meta["name"]] = {
                    "description": meta["description"], "path": str(md), "body": None,
                }
            else:
                print(f"Skipping {child.name}: missing name/description", file=sys.stderr)
        except Exception as exc:
            print(f"Skipping {child.name}: {exc}", file=sys.stderr)
    print(f"Skills: {len(catalog)} — {list(catalog.keys())}", file=sys.stderr)
    return catalog


# Load the full SKILL.md body on demand (Level 2 activation).
def load_skill(catalog, name):
    if name not in catalog:
        return f"[Skill Error] Unknown skill '{name}'. Available: {', '.join(catalog) or '(none)'}"
    s = catalog[name]
    if s["body"] is None:
        text = Path(s["path"]).read_text(encoding="utf-8")
        parts = text.split("---", 2)
        s["body"] = parts[2].strip() if len(parts) >= 3 else text
    return s["body"]


# Build the OpenAI function-calling spec for load_skill.
def tool_spec(catalog):
    return {"type": "function", "function": {
        "name": "load_skill",
        "description": "Load full instructions for an Agent Skill by name.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "enum": list(catalog.keys()),
                     "description": "Skill name from the catalog"},
        }, "required": ["name"]},
    }}


# Build a text block listing available skills for the system prompt.
def catalog_prompt(catalog):
    if not catalog:
        return ""
    lines = ["\n## Available Skills", "Call `load_skill` to get full instructions.\n"]
    for name, info in catalog.items():
        lines.append(f"- **{name}**: {info['description']}")
    return "\n".join(lines)
