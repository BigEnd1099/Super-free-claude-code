import pytest
from api.routes import perturb_prompt

def test_perturb_prompt_comprehensive():
    # Test sensitive words
    original = "I need to hack the system and bypass the root password."
    perturbed = perturb_prompt(original)
    
    # Check that sensitive words are modified
    assert "hack" not in perturbed
    assert "system" not in perturbed
    assert "bypass" not in perturbed
    assert "root" not in perturbed
    assert "password" not in perturbed
    
    # Check that non-sensitive words are preserved (modulo splitting/joining)
    assert "need" in perturbed.lower()
    
def test_perturb_prompt_with_punctuation():
    original = "The system! is down. Hack?"
    perturbed = perturb_prompt(original)
    
    assert "system" not in perturbed
    assert "hack" not in perturbed
    # Punctuation should be preserved in the perturbed output
    assert "!" in perturbed
    assert "?" in perturbed

def test_perturb_prompt_case_insensitivity():
    original = "SYSTEM ROOT HACK"
    perturbed = perturb_prompt(original)
    
    assert "SYSTEM" not in perturbed
    assert "ROOT" not in perturbed
    assert "HACK" not in perturbed
