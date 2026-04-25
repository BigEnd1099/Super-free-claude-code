import importlib.util
import inspect
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from .base import Skill
from .markdown_loader import MarkdownSkillLoader


class SkillLoader:
    """Scans and dynamically loads skills from multiple hierarchical sources."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, root_dir: str | Path | None = None):
        if not hasattr(self, "initialized"):
            self.root_dir = Path(root_dir or Path.cwd())
            self.skills: dict[str, Skill] = {}
            self.loading = False
            self.config = self._load_config()
            self.initialized = True

    def _load_config(self) -> dict[str, Any]:
        """Loads configuration from .agent/config.yaml."""
        config_path = self.root_dir / ".agent" / "config.yaml"
        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Failed to load project config: {e}")
        return {}

    def load_all(self):
        """Discovers skills from all enabled sources in the config."""
        if self.loading:
            return

        self.loading = True
        self.skills.clear()  # Reset for full reload

        try:
            # Determine sources: from config or default paths
            sources = self.config.get("skills", {}).get(
                "skills",
                ["api/skills", "api/skills/markdown", "api/skills/imported", ".agent/skills", ".claude/skills"],
            )

            for source_path_str in sources:
                source_path = self.root_dir / source_path_str
                self._scan_source(source_path, source_path_str)

            # 3. Load Global User Skills (~/.claude/skills) - Markdown Only for safety
            import os
            global_skills = Path(os.path.expanduser("~/.claude/skills"))
            if global_skills.exists():
                logger.info("Scanning global user skills (MD only)")
                try:
                    md_loader = MarkdownSkillLoader(global_skills)
                    md_loader.load_all()
                    count = 0
                    for skill in md_loader.get_skills():
                        if skill.name not in self.skills:
                            self.skills[skill.name] = skill
                            count += 1
                    logger.info(f"SKILLS: Bulk loaded {count} global skills from {global_skills}")
                except Exception as e:
                    logger.error(f"Failed to load global Markdown skills: {e}")
        finally:
            self.loading = False

    def _scan_source(self, source_path: Path, source_path_str: str):
        """Scans a specific path for Python and Markdown skills."""
        if not source_path.exists():
            return

        # 1. Load Python Skills (*.py)
        py_count = 0
        for file in source_path.rglob("*.py"):
            if file.name in [
                "__init__.py",
                "base.py",
                "loader.py",
                "markdown_loader.py",
            ]:
                continue
            if self._load_python_skill(file):
                py_count += 1

        # 2. Load Markdown Skills (*.md)
        md_count = 0
        try:
            md_loader = MarkdownSkillLoader(source_path)
            md_loader.load_all()
            for skill in md_loader.get_skills():
                if skill.name not in self.skills:
                    self.skills[skill.name] = skill
                    md_count += 1
        except Exception as e:
            logger.error(f"Failed to load Markdown skills from {source_path_str}: {e}")
            
        logger.info(f"SKILLS: Bulk loaded {py_count} PY and {md_count} MD skills from {source_path_str}")

    def _load_python_skill(self, file: Path):
        """Loads a single Python skill from a file, handling package context."""
        try:
            try:
                rel_path = file.relative_to(self.root_dir)
            except ValueError:
                # Handle global/external skills outside root_dir
                rel_path = file

            # Determine the module and package names
            # If it's in the api/skills directory, try to use the actual package name
            if "api" in rel_path.parts and "skills" in rel_path.parts:
                # e.g. api.skills.analyzer
                parts = list(rel_path.parts)
                # Remove .py suffix from last part
                parts[-1] = Path(parts[-1]).stem
                module_name = ".".join(parts)
                package_name = ".".join(parts[:-1])
            else:
                # For external skills, use a synthetic flat name
                module_name = f"skill_{file.stem}_{hash(str(rel_path)) % 10000}"
                package_name = ""

            spec = importlib.util.spec_from_file_location(module_name, file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                # Set package to support relative imports
                module.__package__ = package_name

                # If we have a package name, we should ensure the parent exists in sys.modules
                # For api.skills, it already exists, so this is generally safe.

                spec.loader.exec_module(module)

                for _, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, Skill)
                        and obj is not Skill
                    ):
                        skill_instance = obj()
                        # Override path if it's internal
                        if getattr(skill_instance, "path", "internal") == "internal":
                            skill_instance._path = str(file)

                        if skill_instance.name not in self.skills:
                            self.skills[skill_instance.name] = skill_instance
                            return True
        except Exception as e:
            logger.error(f"Failed to load Python skill from {file.name}: {e}")
        return False

    def get_tool_definitions(self) -> list[dict]:
        """Returns tool schemas for all loaded skills."""
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "input_schema": skill.input_schema,
            }
            for skill in self.skills.values()
        ]


# Initialize loader for the project root
skill_loader = SkillLoader(Path(__file__).parents[2])
skill_loader.load_all()
