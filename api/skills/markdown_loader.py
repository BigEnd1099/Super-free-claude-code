from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from .base import Skill


class MarkdownSkill(Skill):
    """A skill dynamically generated from a Markdown file (SKILL.md)."""

    def __init__(
        self, metadata: dict[str, Any], content: str, file_path: str = "markdown"
    ):
        self._name = metadata.get("name", "unnamed_skill")
        self._description = metadata.get("description", "No description provided.")
        self._content = content
        self._version = metadata.get("version", "1.0.0")
        self._path = file_path
        self._category = metadata.get("category", "Uncategorized")
        self._tags = metadata.get("tags", [])
        self._risk = metadata.get("risk", "low")

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def version(self) -> str:
        return self._version

    @property
    def path(self) -> str:
        return self._path

    @property
    def category(self) -> str:
        return self._category

    @property
    def tags(self) -> list:
        return self._tags

    @property
    def risk(self) -> str:
        return self._risk

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "The input text or task to be processed by this skill.",
                }
            },
            "required": ["input"],
        }

    async def execute(self, **kwargs: Any) -> str:
        """
        Executes the skill by providing the instructions to the LLM context.
        Note: In this architecture, the 'execution' of a Markdown skill is actually
        the injection of its instructions into the agent's reasoning loop.
        """
        user_input = kwargs.get("input", "")
        return f"--- SKILL: {self.name} v{self._version} ---\n\nINSTRUCTIONS:\n{self._content}\n\nUSER INPUT: {user_input}"


class MarkdownSkillLoader:
    """Parses and loads skills from Markdown files."""

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: dict[str, MarkdownSkill] = {}

    def load_all(self):
        """Scans the directory for .md files and loads them."""
        if not self.skills_dir.exists():
            return

        for file in self.skills_dir.rglob("*.md"):
            try:
                content = file.read_text(encoding="utf-8")
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]
                        body = parts[2]
                        try:
                            meta = yaml.safe_load(frontmatter)
                            skill = MarkdownSkill(
                                meta, body.strip(), file_path=str(file)
                            )
                            self.skills[skill.name] = skill
                            continue  # Successfully loaded with frontmatter
                        except Exception as ye:
                            logger.warning(
                                f"YAML error in {file.name}, falling back to simple load: {ye}"
                            )

                # Fallback: Treat as a skill with no frontmatter, name from filename
                skill = MarkdownSkill(
                    {"name": file.stem, "description": f"Skill from {file.name}"},
                    content.strip(),
                    file_path=str(file),
                )
                self.skills[skill.name] = skill
            except Exception as e:
                logger.error(f"Failed to load Markdown skill from {file.name}: {e}")

    def get_skills(self) -> list[MarkdownSkill]:
        return list(self.skills.values())
