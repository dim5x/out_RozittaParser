"""
tests/test_features/test_auth_static.py

Тесты: AuthService.parse_proxy_link, AuthService.detect_tdata_path.
"""
from features.auth.api import AuthService


class TestParseProxyLink:
    def test_valid_mtproto(self):
        result = AuthService.parse_proxy_link(
            "https://t.me/proxy?server=1.2.3.4&port=443&secret=ee1234"
        )
        assert result is not None
        assert result["type"] == "mtproto"
        assert result["host"] == "1.2.3.4"
        assert result["port"] == 443
        assert result["secret"] == "ee1234"

    def test_valid_mtproto_with_https(self):
        result = AuthService.parse_proxy_link(
            "https://t.me/proxy?server=proxy.example.com&port=8080&secret=abcd1234"
        )
        assert result is not None
        assert result["host"] == "proxy.example.com"
        assert result["port"] == 8080

    def test_no_proxy_in_path(self):
        result = AuthService.parse_proxy_link("https://t.me/other?server=1.2.3.4")
        assert result is None

    def test_empty_string(self):
        assert AuthService.parse_proxy_link("") is None

    def test_invalid_url(self):
        assert AuthService.parse_proxy_link("not a url at all") is None

    def test_missing_secret(self):
        result = AuthService.parse_proxy_link(
            "https://t.me/proxy?server=1.2.3.4&port=443"
        )
        assert result is None

    def test_missing_server(self):
        result = AuthService.parse_proxy_link(
            "https://t.me/proxy?port=443&secret=ee1234"
        )
        assert result is None

    def test_missing_port_uses_default(self):
        result = AuthService.parse_proxy_link(
            "https://t.me/proxy?server=1.2.3.4&secret=ee1234"
        )
        assert result is not None
        assert result["port"] == 443

    def test_none_input(self):
        assert AuthService.parse_proxy_link(None) is None


class TestDetectTdataPath:
    def test_returns_string_or_none(self):
        result = AuthService.detect_tdata_path()
        assert result is None or isinstance(result, str)

    def test_nonexistent_returns_none(self, tmp_path, monkeypatch):
        import platform
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        monkeypatch.setenv("APPDATA", str(tmp_path / "nonexistent"))
        result = AuthService.detect_tdata_path()
        assert result is None
