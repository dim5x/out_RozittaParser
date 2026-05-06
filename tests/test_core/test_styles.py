"""
tests/test_core/test_styles.py

Тесты: styles.py — реестр стилей, get_style, combine_styles, chat_icon_qss, константы.
Не требует QApplication — чисто строковые операции.
"""
import pytest

from core.ui_shared import styles


class TestStyleRegistry:
    def test_registry_has_expected_keys(self):
        expected = [
            "main_window", "card", "input", "button", "button_primary",
            "button_secondary", "log_output", "media_button", "chip_active",
            "filter_button", "progress", "date_edit",
        ]
        for key in expected:
            assert key in styles._STYLE_REGISTRY, f"Missing key: {key}"

    def test_registry_all_values_are_strings(self):
        for key, value in styles._STYLE_REGISTRY.items():
            assert isinstance(value, str), f"Key {key} is not str"
            assert len(value) > 0, f"Key {key} is empty"

    def test_registry_key_count(self):
        assert len(styles._STYLE_REGISTRY) >= 20


class TestGetStyle:
    def test_known_style_returns_string(self):
        result = styles.get_style("button")
        assert isinstance(result, str)
        assert "QPushButton" in result

    def test_unknown_style_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown style"):
            styles.get_style("nonexistent_style_xyz")

    def test_input_contains_qlineedit(self):
        result = styles.get_style("input")
        assert "QLineEdit" in result

    def test_card_contains_border_radius(self):
        result = styles.get_style("card")
        assert "border-radius" in result


class TestCombineStyles:
    def test_combine_two_styles(self):
        result = styles.combine_styles("button", "button_primary")
        assert "QPushButton" in result
        assert len(result) > len(styles.get_style("button"))

    def test_combine_single_style(self):
        result = styles.combine_styles("card")
        assert result == styles.get_style("card")

    def test_combine_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown style"):
            styles.combine_styles("button", "invalid_xyz")

    def test_combine_preserves_order(self):
        result = styles.combine_styles("button", "button_primary")
        assert "QPushButton" in result


class TestChatIconQss:
    def test_channel_type(self):
        result = styles.chat_icon_qss("channel")
        assert "QLabel" in result
        assert styles.ACCENT_ORANGE in result

    def test_group_type(self):
        result = styles.chat_icon_qss("group")
        assert styles.ACCENT_PINK in result

    def test_forum_type(self):
        result = styles.chat_icon_qss("forum")
        assert styles.ACCENT_PINK in result

    def test_private_type(self):
        result = styles.chat_icon_qss("private")
        assert styles.COLOR_SUCCESS in result

    def test_unknown_type_fallback(self):
        result = styles.chat_icon_qss("unknown_type")
        assert "QLabel" in result

    def test_output_contains_qlabel_selector(self):
        result = styles.chat_icon_qss("channel")
        assert "QLabel" in result


class TestConstants:
    def test_color_constants_are_hex(self):
        for name in ["ACCENT_ORANGE", "BG_PRIMARY", "ACCENT_PINK"]:
            val = getattr(styles, name)
            assert val.startswith("#"), f"{name} doesn't start with #"

    def test_size_constants_positive(self):
        for name in ["RADIUS_LG", "RADIUS_MD", "PADDING_MD", "PADDING_SM"]:
            val = getattr(styles, name)
            assert isinstance(val, int)
            assert val > 0, f"{name} is not positive"
