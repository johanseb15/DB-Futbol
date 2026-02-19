from pipeline.runner import _payload_fingerprint, _validate_raw_payload


def test_validate_raw_payload_ok():
    payload = {"matches": [], "season_id": 2026}
    ok, reason = _validate_raw_payload(payload)
    assert ok is True
    assert reason == ""


def test_validate_raw_payload_invalid_shape():
    payload = {"matches": "bad"}
    ok, reason = _validate_raw_payload(payload)
    assert ok is False
    assert "matches" in reason


def test_payload_fingerprint_stable():
    a = {"matches": [{"id": 1, "x": "y"}], "season_id": 2026}
    b = {"season_id": 2026, "matches": [{"x": "y", "id": 1}]}
    assert _payload_fingerprint(a) == _payload_fingerprint(b)

