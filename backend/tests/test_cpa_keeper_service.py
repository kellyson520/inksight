

def test_antigravity_quota_uses_auth_index_and_never_defaults_to_full_when_cycles_missing(tmp_path):
    """Antigravity 的额度应按认证文件取值；没有周期记录时不能伪报100%。"""
    import sqlite3
    from core.cpa_keeper_service import CpaKeeperService

    db = tmp_path / "keeper.db"
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE usage_overview_daily_stats (
            bucket_start TEXT, request_count INTEGER, success_count INTEGER,
            input_tokens INTEGER, output_tokens INTEGER, total_tokens INTEGER, model TEXT
        );
        CREATE TABLE usage_identities (
            id INTEGER, name TEXT, alias TEXT, provider TEXT, file_name TEXT,
            identity TEXT, total_requests INTEGER, success_count INTEGER,
            total_tokens INTEGER, last_used_at TEXT, disabled INTEGER, is_deleted INTEGER
        );
        CREATE TABLE quota_cycles (
            id INTEGER PRIMARY KEY, provider TEXT, auth_index TEXT, quota_key TEXT,
            window_seconds INTEGER, reset_at TEXT
        );
        CREATE TABLE quota_percent_segments (
            id INTEGER PRIMARY KEY, cycle_id INTEGER, remaining_percent INTEGER
        );
        INSERT INTO usage_identities VALUES
            (5, 'kellson0271@gmail.com', 'huo02', 'antigravity',
             'antigravity-kellson0271@gmail.com.json', 'antigravity-auth',
             12, 12, 1000, '2026-09-05T11:00:00+08:00', 0, 0);
        INSERT INTO quota_cycles VALUES
            (10, 'antigravity', 'antigravity-auth', 'rate_limit.primary_window', 18000,
             '2026-09-05T12:00:00.000000000Z');
        INSERT INTO quota_percent_segments VALUES (1, 10, 42);
        """
    )
    con.commit()
    con.close()

    service = CpaKeeperService(keeper_db_path=str(db), cpa_db_path=str(tmp_path / "missing-cpa.db"))
    metrics = service.get_aggregated_metrics(force_refresh=True)
    auth = metrics["auth_identities"][0]

    assert auth["provider"] == "ANTIGRAVITY"
    assert auth["identity"] == "antigravity-auth"
    assert auth["remaining_pct_num"] == 42
    assert auth["remaining_pct"] == "42%"


def test_antigravity_quota_missing_segment_is_unknown_not_full(tmp_path):
    """没有 Antigravity 百分比观测时应显示未知，不能使用100%假值。"""
    import sqlite3
    from core.cpa_keeper_service import CpaKeeperService

    db = tmp_path / "keeper-no-segment.db"
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE usage_overview_daily_stats (
            bucket_start TEXT, request_count INTEGER, success_count INTEGER,
            input_tokens INTEGER, output_tokens INTEGER, total_tokens INTEGER, model TEXT
        );
        CREATE TABLE usage_identities (
            id INTEGER, name TEXT, alias TEXT, provider TEXT, file_name TEXT,
            identity TEXT, total_requests INTEGER, success_count INTEGER,
            total_tokens INTEGER, last_used_at TEXT, disabled INTEGER, is_deleted INTEGER
        );
        CREATE TABLE quota_cycles (
            id INTEGER PRIMARY KEY, provider TEXT, auth_index TEXT, quota_key TEXT,
            window_seconds INTEGER, reset_at TEXT
        );
        CREATE TABLE quota_percent_segments (
            id INTEGER PRIMARY KEY, cycle_id INTEGER, remaining_percent INTEGER
        );
        INSERT INTO usage_identities VALUES
            (5, 'kellson0271@gmail.com', 'huo02', 'antigravity',
             'antigravity-kellson0271@gmail.com.json', 'antigravity-auth',
             12, 12, 1000, '2026-09-05T11:00:00+08:00', 0, 0);
        INSERT INTO quota_cycles VALUES
            (10, 'antigravity', 'antigravity-auth', 'rate_limit.primary_window', 18000,
             '2026-09-05T12:00:00.000000000Z');
        """
    )
    con.commit()
    con.close()

    service = CpaKeeperService(keeper_db_path=str(db), cpa_db_path=str(tmp_path / "missing-cpa.db"))
    metrics = service.get_aggregated_metrics(force_refresh=True)
    auth = metrics["auth_identities"][0]

    assert auth["remaining_pct_num"] is None
    assert auth["remaining_pct"] == "未知"


def test_remote_cpa_keeper_override_and_health():
    """验证远程配置覆盖生效与健康检查标志。"""
    from core.cpa_keeper_service import CpaKeeperService

    service = CpaKeeperService()
    ov = {
        "cpa_url": "https://remote.cpa.example.com:8443",
        "keeper_url": "http://remote.keeper.example.com:8082",
        "keeper_password": "secret_password",
    }
    health = service.check_health(config_override=ov)
    assert health["cpa_is_remote"] is True
    assert health["keeper_is_remote"] is True
    assert health["cpa_url"] == "https://remote.cpa.example.com:8443"
    assert health["keeper_url"] == "http://remote.keeper.example.com:8082"

    # 获取渲染内容，标题与标签应能反映模式视图
    content = service.get_mode_content(config_override={"view": "auths", **ov})
    assert "title" in content
    assert "header_status" in content
