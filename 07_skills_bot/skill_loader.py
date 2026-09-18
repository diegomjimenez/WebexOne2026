import yaml
from pathlib import Path

class Skill:
    def __init__(self, name: str, description: str, instructions: str):
        self.name = name
        self.description = description
        self.instructions = instructions

class SkillLoader:
    def __init__(self, skills_dir: str):
        self.skills_dir = Path(skills_dir)
        self.skills = {}
        self._load_skills()

    def _load_skills(self):
        if not self.skills_dir.exists():
            print(f"Warning: Skills directory {self.skills_dir} not found.")
            return
            
        for skill_path in self.skills_dir.rglob("SKILL.md"):
            content = skill_path.read_text(encoding="utf-8")
            
            # Split frontmatter and body
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_str = parts[1]
                body = parts[2].strip()
                
                try:
                    metadata = yaml.safe_load(frontmatter_str)
                    name = metadata.get("name", skill_path.parent.name)
                    description = metadata.get("description", "").replace("\n", " ").strip()
                    
                    self.skills[name] = Skill(name, description, body)
                except yaml.YAMLError as e:
                    print(f"Error parsing YAML in {skill_path}: {e}")

    def get_skill(self, name: str) -> Skill:
        return self.skills.get(name)
        
    def get_all_skills_summary(self) -> str:
        if not self.skills:
            return "No skills loaded."
            
        summary = "Available Skills (Runbooks):\n"
        for name, skill in self.skills.items():
            summary += f"- {name}: {skill.description}\n"
        return summary
