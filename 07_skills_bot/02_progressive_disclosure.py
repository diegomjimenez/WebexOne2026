"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

How do skills load? Progressive disclosure in three stages.
This example uses SkillLoader to show the Discovery-stage summary versus the
Activation-stage full body, and compares their size.
No LLM, no network, no credentials needed.

Reference: https://agentskills.io/home  (How do Agent Skills work?)
"""

from pathlib import Path
from skill_loader import SkillLoader

SKILLS_DIR = Path(__file__).parent / "skills"
SKILL_NAME = "meeting-review"


def approximate_tokens(text):
    """Rough token estimate: ~4 characters per token for English."""
    return max(1, len(text) // 4)


if __name__ == "__main__":
    print("=" * 60)
    print("Agent Skills — Progressive Disclosure")
    print("=" * 60)

    loader = SkillLoader(str(SKILLS_DIR))
    skill = loader.get_skill(SKILL_NAME)
    if not skill:
        raise SystemExit(f"Skill '{SKILL_NAME}' not found in {SKILLS_DIR}")

    # --- Stage 1: Discovery (startup) ---
    summary = f"- {skill.name}: {skill.description}"
    summary_chars = len(summary)
    summary_tokens = approximate_tokens(summary)

    print(f"\nSkill: {skill.name}\n")

    print("-" * 60)
    print("STAGE 1 — Discovery (loaded at startup, ~100 tokens)")
    print("-" * 60)
    print("What the agent sees in its system prompt:\n")
    print(f"  {summary}")
    print(f"\n  [{summary_chars} chars, ~{summary_tokens} tokens]")

    # --- Stage 2: Activation (on demand) ---
    body = skill.instructions
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
