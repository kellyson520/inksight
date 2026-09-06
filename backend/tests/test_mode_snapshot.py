from core.mode_snapshot import ModeSnapshot


def test_mode_snapshot_freezes_nested_config_and_definition():
    config = {"mode_language": "zh", "mode_settings": {"x": 1}}
    definition = {"mode_id": "DAILY", "layout": {"body": []}}
    snapshot = ModeSnapshot.capture("DAILY", config, definition)
    config["mode_settings"]["x"] = 9
    definition["layout"]["body"].append({"type": "text"})

    assert snapshot.persona == "DAILY"
    assert snapshot.config["mode_settings"]["x"] == 1
    assert snapshot.definition["layout"]["body"] == []


def test_mode_snapshot_capture_normalizes_none_inputs():
    snapshot = ModeSnapshot.capture("daily", None, None)
    assert snapshot.persona == "DAILY"
    assert snapshot.config == {}
    assert snapshot.definition == {}
