from api.harness.forensics import forensic_analyzer
from config.settings import Settings
from providers.common.router import get_router


def test_router():
    settings = Settings()
    settings.model_opus = "anthropic/claude-3-opus"
    settings.model_sonnet = "anthropic/claude-3.5-sonnet"
    settings.model_haiku = "anthropic/claude-3-haiku"

    router = get_router(settings)

    # Test background task demotion
    res = router.route("background", {})
    print(f"Background task routed to: {res}")
    assert "haiku" in res or "flash" in res

    # Test planning task routing
    res = router.route("standard", {"messages": [{"content": "Create a merge plan"}]})
    print(f"Planning task routed to: {res}")
    assert "opus" in res or "sonnet" in res


def test_forensics():
    events = [
        {"type": "tool_use", "name": "ls", "input": {}},
        {"type": "error", "message": "Rate limit reached for model claude-3-opus"},
    ]
    analysis = forensic_analyzer.analyze("test_session", events)
    print(f"Forensic analysis: {analysis}")
    assert analysis["root_cause"] == "rate_limit_exceeded"
    assert analysis["recommendation"] == "SWITCH_TO_FLASH"


if __name__ == "__main__":
    test_router()
    test_forensics()
    print("Verification complete!")
