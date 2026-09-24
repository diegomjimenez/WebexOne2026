# Lab 7 - Skills in AI Assistant

In this section, you will build a **Skill Loader** in Python. 

While MCP provides tools (the *what*), Skills provide the standard operating procedures or runbooks (the *how*). By teaching your Python bot to read Markdown runbooks, you can encode organizational knowledge without hardcoding complex logic into your Python scripts.

## Step 7.1: The Skill Loader

We will create a Python class that reads a directory of Markdown files. Each file represents a skill, containing YAML frontmatter for metadata (name, description) and a Markdown body for instructions.

Create a new folder `07_skills_bot` and inside it, create `skill_loader.py`:

??? Tip "Python Code"
    ```python
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
    ```

## Step 7.2: Creating a Skill

Create a folder named `skills` inside `07_skills_bot`. Then, create a new folder `troubleshoot-status` inside `skills`, and add a `SKILL.md` file:

??? Tip "Markdown Code"
    ```markdown
    ---
    name: troubleshoot-status
    description: >-
      Use when a user reports a problem with Webex services being down,
      slow, or unavailable. Always check the platform status before
      escalating or troubleshooting local configurations.
    ---

    # Troubleshoot Status

    ## How it works

    1. **Check platform status** — call `unresolved_incidents` to see if there is a known Webex outage.
    2. **Review incidents** — If there are incidents, summarize them for the user and tell them to wait for Cisco to resolve it.
    3. **Check local users** — If there are no incidents, call `list_people` to ensure the user's account is active and properly configured.

    ## Guardrails

    - Never ask the user to change their password or reinstall Webex if there is an active platform incident.
    - Always provide the incident title and updates if one exists.
    ```

## Step 7.3: Integrating Skills into the Bot

Now, we will integrate the `SkillLoader` into our bot. We will:
1. Load all skills on startup.
2. Inject the skill descriptions into the LLM's system prompt.
3. Provide a local tool `read_skill_runbook` so the LLM can read the full instructions when needed.

Create `01_bot_skills.py` in `07_skills_bot`:

??? Tip "Python Code"
    ```python
    import asyncio
    import logging
    import os
    import sys
    from datetime import datetime, timezone
    from pathlib import Path

    from dotenv import load_dotenv

    # Ensure we can import from 06_mcp_bot and 05_bot
    LAB_ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(LAB_ROOT / "06_mcp_bot"))
    sys.path.insert(0, str(LAB_ROOT / "05_bot"))

    from llm import as_openai_tools, run_turn
    from mcp_hub import McpHub
    from mcp_client import McpClient
    from websocket_client import WebSocketClient
    from skill_loader import SkillLoader

    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("mcp-skills-bot")

    load_dotenv()

    BOT_TOKEN = os.getenv("BOT_TOKEN")
    MESSAGING_TOKEN = os.getenv("WEBEX_MESSAGING_MCP_TOKEN")
    MEETING_TOKEN = os.getenv("WEBEX_MEETING_MCP_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")

    if not BOT_TOKEN or not OPENAI_API_KEY:
        raise SystemExit("Set BOT_TOKEN and OPENAI_API_KEY in your .env file")

    # Load Skills
    skills_dir = Path(__file__).resolve().parent / "skills"
    skill_loader = SkillLoader(skills_dir)
    log.info(f"Loaded {len(skill_loader.skills)} skill(s).")

    # Define the local tool for reading skills
    READ_SKILL_TOOL = {
        "type": "function",
        "function": {
            "name": "read_skill_runbook",
            "description": "Read the full instructions for a specific skill/runbook.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "The name of the skill to read (e.g., 'troubleshoot-status').",
                    }
                },
                "required": ["skill_name"],
            },
        },
    }

    def read_skill_runbook(arguments):
        skill_name = arguments.get("skill_name")
        skill = skill_loader.get_skill(skill_name)
        if skill:
            log.info(f"LLM reading skill: {skill_name}")
            return skill.instructions
        return f"Skill '{skill_name}' not found."

    # Setup MCP Hub
    CUSTOM_SERVER = LAB_ROOT / "04_custom_mcp" / "06_calling_hub.py"
    custom = McpClient(
        command=sys.executable,
        args=[str(CUSTOM_SERVER)],
        cwd=str(LAB_ROOT),
    )

    hub = McpHub([
        ("https://mcp.webexapis.com/mcp/webex-messaging", MESSAGING_TOKEN),
        ("https://mcp.webexapis.com/mcp/webex-meeting", MEETING_TOKEN),
        custom,
    ])

    async def answer(question, sender, room_id):
        tools = as_openai_tools(await hub.list_tools()) + [READ_SKILL_TOOL]
        
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Inject the skills summary into the system prompt
        skills_summary = skill_loader.get_all_skills_summary()
        
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a Webex assistant helping {sender}. Today is {today} (UTC). "
                    "Answer only from tool results, never from memory. "
                    "You have access to several operational runbooks (Skills). "
                    "If a user's request matches a skill, call read_skill_runbook to get the instructions, "
                    "and strictly follow those instructions.\n\n"
                    f"{skills_summary}"
                ),
            },
            {"role": "user", "content": question},
        ]
        
        reply = await run_turn(hub, messages, tools, extra={"read_skill_runbook": read_skill_runbook})
        return reply

    def handle_message(message):
        text = (message.get("text") or "").strip()
        if not text:
            return

        sender = message["personEmail"]
        log.info(f"Received from {sender}: {text}")
        asyncio.create_task(reply_with_assistant(message, sender, text))

    async def reply_with_assistant(message, sender, question):
        try:
            reply = await answer(question, sender, message["roomId"])
        except Exception as e:
            log.exception("Assistant turn failed")
            bot.send_message(message["roomId"], "Sorry, I encountered an error.")
            return
            
        bot.send_message(message["roomId"], reply)
        log.info(f"Sent to {sender}: {reply}")

    if __name__ == "__main__":
        bot = WebSocketClient(access_token=BOT_TOKEN, on_message=handle_message)
        log.info(f"Listening as {bot.me['emails'][0]} via WebSocket... (Ctrl+C to stop)")
        try:
            bot.run()
        except KeyboardInterrupt:
            log.info("Stopped.")
    ```

## Step 7.4: Test the Bot

Run the bot from your terminal:

```bash
python 07_skills_bot/01_bot_skills.py
```

In Webex, ask your bot:
> *"A user is complaining that Webex is slow. Can you troubleshoot?"*

You should see in your terminal that the LLM first calls `read_skill_runbook` for `troubleshoot-status`, reads the instructions, and then calls `unresolved_incidents` to check the platform status, exactly as the runbook instructed!

![Skill Execution](assets/placeholder_skill_execution.png){ width="650" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
