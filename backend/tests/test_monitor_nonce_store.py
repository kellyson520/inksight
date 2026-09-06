import pytest

from core.monitor_nonce_store import MonitorNonceStore


@pytest.mark.asyncio
async def test_nonce_store_rejects_replay_after_reload(tmp_path):
    path = tmp_path / "monitor.sqlite"
    first = MonitorNonceStore(path)
    await first.initialize()
    expires_at = __import__("time").time() + 2_000
    assert await first.consume("nonce-1", expires_at=expires_at) is True

    second = MonitorNonceStore(path)
    await second.initialize()
    assert await second.consume("nonce-1", expires_at=expires_at) is False


@pytest.mark.asyncio
async def test_nonce_store_prunes_expired_entries(tmp_path):
    path = tmp_path / "monitor.sqlite"
    store = MonitorNonceStore(path, now=lambda: 100.0)
    await store.initialize()
    assert await store.consume("old", expires_at=99.0) is True
    assert await store.consume("new", expires_at=200.0) is True
    assert await store.consume("old", expires_at=200.0) is True
