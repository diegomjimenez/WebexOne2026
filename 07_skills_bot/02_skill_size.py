"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Compare the discovery summary with one full skill body.
"""

from pathlib import Path

from skill_loader import SkillLoader

SKILLS_DIR = Path(__file__).resolve().parent / "skills"
EXAMPLE_SKILL = "meeting-review"


def approx_tokens(text):
    return max(1, round(len(text) / 4))


def main():
    loader = SkillLoader(SKILLS_DIR)
    skill = loader.get_skill(EXAMPLE_SKILL)
    if skill is None:
        raise SystemExit(f"Skill {EXAMPLE_SKILL} was not found in {SKILLS_DIR}")

    description_tokens = approx_tokens(skill.description)
    body_tokens = approx_tokens(skill.instructions)
    summary_tokens = approx_tokens(loader.get_all_skills_summary())
    all_bodies = sum(approx_tokens(item.instructions) for item in loader.skills.values())
    ratio = max(1, round(body_tokens / description_tokens))

    print(f"Skills discovered: {len(loader.skills)}")
    print(f"Discovery, one skill ({EXAMPLE_SKILL} description): ~{description_tokens} tokens")
    print(f"Activation, one skill ({EXAMPLE_SKILL} body):       ~{body_tokens} tokens")
    print(f"The body is {ratio}x the description.")
    print(f"Every description together: ~{summary_tokens} tokens")
    print(f"Every full body together:   ~{all_bodies} tokens")


if __name__ == "__main__":
    main()
