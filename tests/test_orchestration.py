import asyncio

import pytest

from api.orchestration.memory import SharedMemory
from api.orchestration.tasks import AsyncTaskManager
from api.skills.loader import SkillLoader


@pytest.mark.asyncio
async def test_shared_memory():
    memory = SharedMemory()
    await memory.set_task("test_key", "test_value")
    val = await memory.get_task("test_key")
    assert val == "test_value"

    keys = await memory.get_all_keys()
    assert "test_key" in keys


@pytest.mark.asyncio
async def test_async_task_manager_parallel():
    manager = AsyncTaskManager(max_concurrent=2)

    async def slow_task(duration):
        await asyncio.sleep(duration)
        return "done"

    tasks = [lambda: slow_task(0.1) for _ in range(4)]
    start_time = asyncio.get_event_loop().time()
    results = await manager.dispatch_parallel(tasks)
    end_time = asyncio.get_event_loop().time()

    assert len(results) == 4
    assert all(r == "done" for r in results)
    # With max_concurrent=2, 4 tasks of 0.1s should take ~0.2s
    assert end_time - start_time >= 0.2


def test_skill_loader(tmp_path):
    # Create a dummy skill file in a scanned directory
    skills_dir = tmp_path / "api" / "skills"
    skills_dir.mkdir(parents=True)

    skill_file = skills_dir / "test_skill.py"
    skill_file.write_text("""
from api.skills.base import Skill
class MyTestSkill(Skill):
    @property
    def name(self): return "test_skill"
    @property
    def description(self): return "test desc"
    async def execute(self, **kwargs): return "ok"
""")

    loader = SkillLoader(tmp_path)
    loader.load_all()
    assert "test_skill" in loader.skills
    assert loader.skills["test_skill"].description == "test desc"
