from scripts.adapters.base import AdapterError, make_client


def test_adapter_error_is_exception():
    err = AdapterError("nope")
    assert isinstance(err, Exception)
    assert str(err) == "nope"


def test_make_client_has_timeout_and_user_agent():
    with make_client() as c:
        assert c.timeout.connect is not None
        assert "portrait-photo-site" in c.headers["user-agent"].lower()
