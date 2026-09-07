import pytest
from unittest.mock import patch
from core.github_service import get_github_pulse, _generate_fallback_pulse


@pytest.mark.asyncio
async def test_github_service_fallback_structure():
    pulse = _generate_fallback_pulse("testuser")
    assert pulse["username"] == "testuser"
    assert pulse["avatar_initial"] == "T"
    assert "total_contributions" in pulse
    assert "current_streak" in pulse
    assert "contributions" in pulse
    assert len(pulse["contributions"]) == 7 * 16
    assert pulse["source_status"] == "fallback"


@pytest.mark.asyncio
async def test_github_service_fetches_or_falls_back_without_error():
    # Test network failure falls back cleanly
    with patch("core.github_service.outbound_http.get_json", side_effect=Exception("API Rate limit exceeded")):
        pulse = await get_github_pulse("octocat")
        assert pulse["username"] == "octocat"
        assert pulse["source_status"] == "fallback"
        assert len(pulse["contributions"]) >= 7 * 12
        assert "top_repos" in pulse
