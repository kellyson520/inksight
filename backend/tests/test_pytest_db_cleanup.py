import asyncio


def test_sync_database_cleanup_runs_close_all_to_completion(monkeypatch):
    from tests import conftest

    state = {"closed": False}

    async def close_all():
        await asyncio.sleep(0)
        state["closed"] = True

    monkeypatch.setattr("core.db.close_all", close_all)
    conftest._close_databases_sync()
    assert state["closed"] is True
