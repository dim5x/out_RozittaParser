"""
tests/test_core/test_config.py

Тесты: AppConfig, load_config, save_config — сериализация, валидация, свойства.
"""
import json
import os
import pytest
from config import AppConfig, load_config, save_config, DAYS_LIMIT_ALL_TIME
from core.exceptions import ConfigError


# ──────────────────────────────────────────────────────────────────────────────
# load_config
# ──────────────────────────────────────────────────────────────────────────────

class TestLoadConfig:
    def test_missing_file_returns_defaults(self, tmp_path):
        cfg = load_config(str(tmp_path / "nonexistent.json"))
        assert cfg.api_id == ""
        assert cfg.api_hash == ""
        assert cfg.phone == ""
        assert cfg.days == 30
        assert cfg.split_mode == "none"

    def test_invalid_json_returns_defaults(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{invalid json", encoding="utf-8")
        cfg = load_config(str(path))
        assert cfg.api_id == ""

    def test_full_config(self, tmp_path):
        path = tmp_path / "full.json"
        data = {
            "api_id": "12345",
            "api_hash": "abc123",
            "phone": "+79991234567",
            "days": 90,
            "media_filter": ["Фото"],
            "comments": True,
            "split_mode": "day",
            "stt_model": "medium",
            "stt_language": "en",
            "proxy_enabled": True,
            "proxy_type": "socks5",
            "proxy_host": "127.0.0.1",
            "proxy_port": 9050,
            "proxy_secret": "",
        }
        path.write_text(json.dumps(data), encoding="utf-8")
        cfg = load_config(str(path))
        assert cfg.api_id == "12345"
        assert cfg.api_hash == "abc123"
        assert cfg.days == 90
        assert cfg.comments is True
        assert cfg.split_mode == "day"
        assert cfg.proxy_enabled is True
        assert cfg.stt_model == "medium"

    def test_partial_config_fills_defaults(self, tmp_path):
        path = tmp_path / "partial.json"
        path.write_text('{"api_id": "999"}', encoding="utf-8")
        cfg = load_config(str(path))
        assert cfg.api_id == "999"
        assert cfg.api_hash == ""
        assert cfg.split_mode == "none"

    def test_round_trip(self, tmp_path):
        path = str(tmp_path / "rt.json")
        original = AppConfig(api_id="42", api_hash="x", phone="+1")
        save_config(original, path)
        loaded = load_config(path)
        assert loaded.api_id == "42"
        assert loaded.api_hash == "x"
        assert loaded.phone == "+1"


# ──────────────────────────────────────────────────────────────────────────────
# AppConfig.validate()
# ──────────────────────────────────────────────────────────────────────────────

class TestAppConfigValidate:
    def test_empty_api_id_raises(self):
        cfg = AppConfig(api_id="", api_hash="abc")
        with pytest.raises(ConfigError, match="API ID"):
            cfg.validate()

    def test_whitespace_api_id_raises(self):
        cfg = AppConfig(api_id="   ", api_hash="abc")
        with pytest.raises(ConfigError, match="API ID"):
            cfg.validate()

    def test_non_numeric_api_id_raises(self):
        cfg = AppConfig(api_id="abc", api_hash="xyz")
        with pytest.raises(ConfigError, match="числом"):
            cfg.validate()

    def test_empty_api_hash_raises(self):
        cfg = AppConfig(api_id="123", api_hash="")
        with pytest.raises(ConfigError, match="API Hash"):
            cfg.validate()

    def test_whitespace_api_hash_raises(self):
        cfg = AppConfig(api_id="123", api_hash="   ")
        with pytest.raises(ConfigError, match="API Hash"):
            cfg.validate()

    def test_invalid_split_mode_raises(self):
        cfg = AppConfig(api_id="1", api_hash="x", split_mode="bad")
        with pytest.raises(ConfigError, match="split_mode"):
            cfg.validate()

    def test_valid_config_passes(self):
        cfg = AppConfig(api_id="12345", api_hash="abcdef1234567890")
        cfg.validate()  # no exception


# ──────────────────────────────────────────────────────────────────────────────
# AppConfig properties
# ──────────────────────────────────────────────────────────────────────────────

class TestAppConfigProperties:
    def test_api_id_int_valid(self):
        assert AppConfig(api_id="42").api_id_int == 42

    def test_api_id_int_empty(self):
        assert AppConfig(api_id="").api_id_int is None

    def test_api_id_int_non_numeric(self):
        assert AppConfig(api_id="abc").api_id_int is None

    def test_api_id_int_float_string(self):
        assert AppConfig(api_id="3.14").api_id_int is None

    def test_is_all_time_true(self):
        assert AppConfig(days=DAYS_LIMIT_ALL_TIME).is_all_time is True
        assert AppConfig(days=500).is_all_time is True

    def test_is_all_time_false(self):
        assert AppConfig(days=30).is_all_time is False
        assert AppConfig(days=364).is_all_time is False

    def test_db_path(self):
        cfg = AppConfig(output_dir="/tmp/out")
        assert cfg.db_path == os.path.join("/tmp/out", "telegram_archive.db")

    def test_session_path_absolute(self):
        cfg = AppConfig(session_name="test_session")
        assert os.path.isabs(cfg.session_path)


# ──────────────────────────────────────────────────────────────────────────────
# save_config
# ──────────────────────────────────────────────────────────────────────────────

class TestSaveConfig:
    def test_creates_file(self, tmp_path):
        path = str(tmp_path / "new.json")
        save_config(AppConfig(api_id="1", api_hash="x"), path)
        assert os.path.exists(path)

    def test_excludes_runtime_fields(self, tmp_path):
        path = str(tmp_path / "rt.json")
        cfg = AppConfig(api_id="1", api_hash="x", output_dir="/secret", session_name="priv")
        save_config(cfg, path)
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        assert "output_dir" not in data
        assert "session_name" not in data

    def test_json_is_valid_utf8(self, tmp_path):
        path = str(tmp_path / "utf8.json")
        cfg = AppConfig(api_id="1", api_hash="x", phone="+7999")
        save_config(cfg, path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_readonly_path_raises(self, tmp_path):
        path = str(tmp_path / "readonly" / "config.json")
        with pytest.raises(ConfigError):
            save_config(AppConfig(), path)

    def test_round_trip_preserves_proxy(self, tmp_path):
        path = str(tmp_path / "proxy.json")
        cfg = AppConfig(
            api_id="1", api_hash="x",
            proxy_enabled=True, proxy_type="mtproto",
            proxy_host="1.2.3.4", proxy_port=443, proxy_secret="ee1234",
        )
        save_config(cfg, path)
        loaded = load_config(path)
        assert loaded.proxy_enabled is True
        assert loaded.proxy_type == "mtproto"
        assert loaded.proxy_host == "1.2.3.4"
        assert loaded.proxy_port == 443
        assert loaded.proxy_secret == "ee1234"


# ──────────────────────────────────────────────────────────────────────────────
# S8: Config edge cases
# ──────────────────────────────────────────────────────────────────────────────

class TestAppConfigValidateAdditional:
    @pytest.mark.parametrize("mode", ["none", "day", "month", "post"])
    def test_valid_split_modes_all(self, mode):
        cfg = AppConfig(api_id="1", api_hash="abc123", split_mode=mode)
        cfg.validate()

    @pytest.mark.parametrize("mode", ["weekly", "year", "NONE", "Day", ""])
    def test_invalid_split_modes(self, mode):
        cfg = AppConfig(api_id="1", api_hash="abc123", split_mode=mode)
        with pytest.raises(ConfigError, match="split_mode"):
            cfg.validate()

    def test_negative_api_id_int_still_parses(self):
        cfg = AppConfig(api_id="-1")
        assert cfg.api_id_int == -1

    def test_zero_api_id_int(self):
        cfg = AppConfig(api_id="0")
        assert cfg.api_id_int == 0


class TestLoadConfigAdditional:
    def test_empty_file_returns_defaults(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_bytes(b"")
        cfg = load_config(str(path))
        assert cfg.api_id == ""

    def test_json_with_extra_keys(self, tmp_path):
        path = tmp_path / "extra.json"
        data = {"api_id": "123", "api_hash": "abc", "unknown_key": "value"}
        path.write_text(json.dumps(data), encoding="utf-8")
        cfg = load_config(str(path))
        assert cfg.api_id == "123"

    def test_load_returns_appconfig_instance(self, tmp_path):
        path = tmp_path / "cfg.json"
        path.write_text('{"api_id": "1"}', encoding="utf-8")
        cfg = load_config(str(path))
        assert isinstance(cfg, AppConfig)

    def test_load_non_dict_json(self, tmp_path):
        path = tmp_path / "array.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        cfg = load_config(str(path))
        assert cfg.api_id == ""

    def test_proxy_fields_loaded(self, tmp_path):
        path = tmp_path / "proxy.json"
        data = {
            "api_id": "1", "api_hash": "x",
            "proxy_enabled": True, "proxy_type": "socks5",
            "proxy_host": "10.0.0.1", "proxy_port": 1080,
        }
        path.write_text(json.dumps(data), encoding="utf-8")
        cfg = load_config(str(path))
        assert cfg.proxy_host == "10.0.0.1"
        assert cfg.proxy_port == 1080


class TestAppConfigPropertiesAdditional:
    def test_db_path_with_nested_output_dir(self):
        cfg = AppConfig(output_dir="a/b/c")
        assert "a" in cfg.db_path
        assert "b" in cfg.db_path
        assert "telegram_archive.db" in cfg.db_path

    def test_is_all_time_boundary_364(self):
        assert AppConfig(days=364).is_all_time is False

    def test_is_all_time_boundary_365(self):
        assert AppConfig(days=365).is_all_time is True

    def test_is_all_time_boundary_366(self):
        assert AppConfig(days=366).is_all_time is True
