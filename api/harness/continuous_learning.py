import json
import os
from typing import Dict, List, Any, Optional
from loguru import logger

class InstinctManager:
    """Manages 'Instincts' - learned patterns from successful behaviors."""

    def __init__(self, storage_path: str = "data/instincts.json"):
        self.storage_path = storage_path
        self.instincts: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    self.instincts = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load instincts: {e}")

    def _save(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        try:
            with open(self.storage_path, "w") as f:
                json.dump(self.instincts, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save instincts: {e}")

    def learn(self, pattern_key: str, behavior: Any):
        """Records a successful behavior pattern."""
        logger.info(f"INSTINCT: Learning pattern '{pattern_key}'")
        self.instincts[pattern_key] = {
            "behavior": behavior,
            "success_count": self.instincts.get(pattern_key, {}).get("success_count", 0) + 1,
            "last_updated": os.path.getmtime(self.storage_path) if os.path.exists(self.storage_path) else 0
        }
        self._save()

    def recall(self, pattern_key: str) -> Optional[Any]:
        """Recalls a learned behavior pattern."""
        instinct = self.instincts.get(pattern_key)
        if instinct:
            logger.info(f"INSTINCT: Recalling pattern '{pattern_key}'")
            return instinct["behavior"]
        return None

instinct_manager = InstinctManager()
