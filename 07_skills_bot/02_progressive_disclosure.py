"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

How do skills load? Progressive disclosure in three stages.
This example shows the Discovery-stage summary (what the agent sees at startup)
versus the Activation-stage full body (loaded on demand), and compares their size.
No LLM, no network, no credentials needed.

Reference: https://agentskills.io/home  (How do Agent Skills work?)
"""

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
        if current_key and line.startswith(("  ", "\t")):
            stripped = line.strip()
            if stripped:
                prev = meta.get(current_key, "")
                meta[current_key] = (prev + " " + stripped).strip()
            continue
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            key = key.strip().lower()
            val = value.strip()
            if key in ("name", "description"):
                current_key = key
                if val in (">-", ">", "|"):
                    meta.setdefault(key, "")
                else:
                    meta[key] = val
            else:
                current_key = None
    return meta


def load_body(text):
    """Extract the body (everything after the closing --- of frontmatter)."""
    parts = text.split("---", 2)
    return parts[2].strip() if len(parts) >= 3 else text


def approximate_tokens(text):
    """Rough token estimate: ~4 characters per token for English."""
    return max(1, len(text) // 4)


if __name__ == "__main__":
    print("=" * 60)
    print("Agent Skills — Progressive Disclosure")
    print("=" * 60)

    # Find the first valid skill to demonstrate with.
    skill_path = None
    for child in sorted(SKILLS_DIR.iterdir()):
        md = child / "SKILL.md"
        if child.is_dir() and md.is_file():
            skill_path = md
            break

    if not skill_path:
        raise SystemExit(f"No skills found in {SKILLS_DIR}")

    raw = skill_path.read_text(encoding="utf-8")
    meta = parse_frontmatter(raw)
    body = load_body(raw)
    name = meta.get("name", "(unknown)")
    desc = meta.get("description", "(no description)")

    # --- Stage 1: Discovery (startup) ---
    summary = f"- {name}: {desc}"
    summary_chars = len(summary)
    summary_tokens = approximate_tokens(summary)

    print(f"\nSkill: {name}")
    print(f"Path:  {skill_path}\n")

    print("-" * 60)
    print("STAGE 1 — Discovery (loaded at startup, ~100 tokens)")
    print("-" * 60)
    print("What the agent sees in its system prompt:\n")
    print(f"  {summary}")
    print(f"\n  [{summary_chars} chars, ~{summary_tokens} tokens]")

    # --- Stage 2: Activation (on demand) ---
    body_chars = len(body)
    body_tokens = approximate_tokens(body)

    print()
    print("-" * 60)
    print("STAGE 2 — Activation (loaded when the task matches)")
    print("-" * 60)
    print("Full SKILL.md body loaded into context:\n")
    for line in body.split("\n"):
        print(f"  {line}")
    print(f"\n  [{body_chars} chars, ~{body_tokens} tokens]")

    # --- Comparison ---
    ratio = body_chars / summary_chars if summary_chars else 0

    print()
    print("=" * 60)
    print("COMPARISON")
    print("=" * 60)
    print(f"  Discovery summary:  {summary_chars:>5} chars  (~{summary_tokens} tokens)")
    print(f"  Full body:          {body_chars:>5} chars  (~{body_tokens} tokens)")
    print(f"  Full body is {ratio:.0f}x larger than the summary.")
    print()
    print(
        "With 10 skills, loading all bodies at startup would cost\n"
        f"~{body_tokens * 10:,} tokens. Progressive disclosure keeps it\n"
        f"at ~{summary_tokens * 10:,} tokens — loading the full body only\n"
        "when the agent decides the skill is relevant."
    )
    print(f"\nReference: https://agentskills.io/specification")
