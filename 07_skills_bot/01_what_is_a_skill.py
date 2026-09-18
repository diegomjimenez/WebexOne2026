"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

What is a skill? A folder containing a SKILL.md file.
This example uses the SkillLoader class to discover skills and print the catalog.
No LLM, no network, no credentials needed.

Reference: https://agentskills.io/home  (What are Agent Skills?)
"""

from pathlib import Path
from skill_loader import SkillLoader

SKILLS_DIR = Path(__file__).parent / "skills"

if __name__ == "__main__":
    print("=" * 60)
    print("Agent Skills — What is a skill?")
    print("=" * 60)
    print(f"\nScanning: {SKILLS_DIR}\n")

    loader = SkillLoader(str(SKILLS_DIR))

    if not loader.skills:
        print("No skills found.")
    else:
        print(f"Found {len(loader.skills)} skill(s):\n")
        for name, skill in loader.skills.items():
            print(f"  Name:        {name}")
            print(f"  Description: {skill.description}")
            print()

    print("-" * 60)
    print(
        "A skill is just a folder with a SKILL.md file.\n"
        "The frontmatter (name + description) is all an agent needs\n"
        "to know WHEN to use it. The full body loads only on demand.\n"
        "\nLearn more: https://agentskills.io/specification"
    )
