"""Password policy tests — equivalence class + boundary value analysis."""

import pytest

from auth.password_policy import validate_password


@pytest.mark.requirement("REQ-AUTH-007")
class TestPasswordLength:
    """边界值：长度校验 (min=8, max=128)."""

    def test_too_short(self):
        """P2: 4位 → 应拒绝."""
        assert validate_password("A1!a") == "密码长度不能少于 8 位"

    def test_min_boundary_valid(self):
        """P3: 恰好8位且满足所有要求 → 应通过."""
        assert validate_password("Abcdef1!") is None

    def test_max_boundary_valid(self):
        """P4: 128位且满足要求 → 应通过."""
        pwd = "A1!" + "a" * 125
        assert len(pwd) == 128
        assert validate_password(pwd) is None

    def test_too_long(self):
        """P5: 129位 → 应拒绝."""
        pwd = "A1!" + "a" * 126
        assert len(pwd) == 129
        assert validate_password(pwd) == "密码长度不能超过 128 位"


@pytest.mark.requirement("REQ-AUTH-007")
class TestCommonPasswords:
    """等价类：常见密码黑名单."""

    def test_common_password_password123(self):
        """P6: password123 → 应拒绝."""
        assert validate_password("password123") == "此密码过于常见，请更换"

    def test_common_password_admin123(self):
        """P7: admin123 → 应拒绝."""
        assert validate_password("admin123") == "此密码过于常见，请更换"

    def test_common_password_different_case(self):
        """常见密码大小写变体 → 应拒绝（lower() 比较）."""
        assert validate_password("Admin123") == "此密码过于常见，请更换"


@pytest.mark.requirement("REQ-AUTH-007")
class TestCharacterRequirements:
    """等价类：各类字符缺失."""

    def test_missing_digit(self):
        """P8: 无数字 → 应拒绝."""
        assert validate_password("Abcdefgh!") == "密码至少包含 1 个数字"

    def test_missing_lowercase(self):
        """P9: 无小写 → 应拒绝."""
        assert validate_password("ABCDEF1!") == "密码至少包含 1 个小写字母"

    def test_missing_uppercase(self):
        """P10: 无大写 → 应拒绝."""
        assert validate_password("abcdef1!") == "密码至少包含 1 个大写字母"

    def test_missing_special(self):
        """P11: 无特殊字符 → 应拒绝."""
        assert validate_password("Abcdef12") == "密码至少包含 1 个特殊字符"


@pytest.mark.requirement("REQ-AUTH-007")
class TestEdgeCases:
    """边界 + 特殊场景."""

    def test_empty(self):
        """P13: 空字符串 → 应拒绝."""
        assert validate_password("") == "密码长度不能少于 8 位"

    def test_valid_exact_minimum(self):
        """P1: 恰好满足所有最小值 → 应通过."""
        assert validate_password("Abcdef1!") is None

    def test_unicode_valid(self):
        """P14: 含 Unicode 字符且满足要求 → 应通过."""
        assert validate_password("Abcሴ1!xy") is None  # 8 codepoints

    def test_all_spaces(self):
        """纯空格 → 缺字符类型，应拒绝."""
        msg = validate_password("        ")
        assert msg is not None  # 空格不是数字/小写/大写/特殊

    def test_only_digits_not_common(self):
        """纯数字（非黑名单）→ 应拒绝（缺小写字母）."""
        assert validate_password("12345679") == "密码至少包含 1 个小写字母"

    def test_only_digits_common(self):
        """纯数字且在黑名单中 → 应拒绝（常见密码检查优先）."""
        assert validate_password("12345678") == "此密码过于常见，请更换"
