from typing import Any

from .loader import skill_loader


class SkillCatalog:
    """Manages skill categorization, bundles, and search."""

    def __init__(self):
        self.bundles = {
            "Security Engineer": [
                "security-auditor",
                "security-review",
                "security-scan",
            ],
            "Full-Stack Developer": [
                "test-driven-development",
                "debugging-strategies",
                "code-review",
            ],
            "Architect": [
                "api-design-principles",
                "hexagonal-architecture",
                "architecture-decision-records",
            ],
        }

    def get_all_skills(self) -> list[dict[str, Any]]:
        skills = []
        for name, skill in skill_loader.skills.items():
            skills.append(
                {
                    "name": name,
                    "description": skill.description,
                    "category": getattr(skill, "category", "Uncategorized"),
                    "tags": getattr(skill, "tags", []),
                    "risk": getattr(skill, "risk", "low"),
                    "type": "MD" if hasattr(skill, "_content") else "PY",
                }
            )
        return skills

    def get_skills_by_category(self, category: str) -> list[dict[str, Any]]:
        return [
            s
            for s in self.get_all_skills()
            if s["category"].lower() == category.lower()
        ]

    def search_skills(self, query: str) -> list[dict[str, Any]]:
        q = query.lower()
        return [
            s
            for s in self.get_all_skills()
            if q in s["name"].lower()
            or q in s["description"].lower()
            or any(q in t.lower() for t in s["tags"])
        ]

    def get_bundle(self, bundle_name: str) -> list[dict[str, Any]]:
        skill_names = self.bundles.get(bundle_name, [])
        return [s for s in self.get_all_skills() if s["name"] in skill_names]


catalog = SkillCatalog()
