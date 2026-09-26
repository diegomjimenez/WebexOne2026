"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Connect to the Webex Meetings MCP server and list its tools.
"""

"""Print the name and description of every skill in skills/."""

from pathlib import Path

from skill_loader import SkillLoader

SKILLS_DIR = Path(__file__).resolve().parent / "skills"


def main():
    loader = SkillLoader(SKILLS_DIR)
    if not loader.skills:
        raise SystemExit(f"No skills found in {SKILLS_DIR}")

    for name in sorted(loader.skills):
        skill = loader.skills[name]
        print(f"{skill.name}: {skill.description}")


if __name__ == "__main__":
    main()
