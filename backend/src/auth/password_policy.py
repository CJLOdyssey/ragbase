"""Password strength validation for registration and password changes."""

from dataclasses import dataclass

__all__ = [
    "COMMON_PASSWORDS",
    "PasswordPolicy",
    "policy",
    "validate_password",
]

COMMON_PASSWORDS = {
    # SecLists top-100 (2023) + 中文常见弱密码 — 与 HIBP 前 10 万重合度高
    "password", "123456", "123456789", "12345678", "12345", "1234567",
    "qwerty", "abc123", "password1", "qwerty123", "111111", "123123",
    "admin", "letmein", "welcome", "monkey", "dragon", "baseball",
    "football", "shadow", "master", "michael", "mustang", "superman",
    "batman", "freedom", "whatever", "trustno1", "passw0rd", "iloveyou",
    "sunshine", "princess", "football1", "charlie", "hunter", "ginger",
    "buster", "soccer", "harley", "george", "andrew", "joshua", "thomas",
    "anthony", "daniel", "matthew", "jordan", "tigger", "pepper", "loveme",
    "jennifer", "secret", "access", "pass", "starwars", "qazwsx",
    "zaq12wsx", "1qaz2wsx", "qwertyuiop", "asdfghjkl", "zxcvbnm",
    "11111111", "222222", "333333", "555555", "666666", "888888", "999999",
    "123321", "654321", "112233", "121212", "abcabc", "a1b2c3",
    "password123", "password1234", "password12", "p@ssw0rd", "passw0rd123",
    "admin123", "admin888", "admin666", "administrator", "root",
    "toor", "guest", "test", "test123", "demo", "demo123",
    "changeme", "default", "none", "unknown", "newuser", "login",
    # 中文常见弱密码
    "woaini", "woaini520", "aini1314", "5201314", "1314520", "woainima",
    "a123456", "a123456789", "qq123456", "taobao", "alipay", "weixin",
    "wang123", "zhang123", "li123456", "chen123", "liu123", "yang123",
    "woshishui", "nihao123", "zheshimima", "wojia123", "xiexie123",
}


@dataclass
class PasswordPolicy:
    """Password strength requirements for registration and password changes."""

    min_length: int = 8
    max_length: int = 128
    min_digits: int = 1
    min_lowercase: int = 1
    min_uppercase: int = 1
    min_special: int = 1
    special_chars: str = r"!@#$%^&*()_+\-=\[\]{}|;':\",./<>?~"


policy = PasswordPolicy()


def validate_password(password: str) -> str | None:
    """Validate password against the configured policy.

    Returns an error message string if validation fails, or None if valid.
    """
    if len(password) < policy.min_length:
        return f"密码长度不能少于 {policy.min_length} 位"
    if len(password) > policy.max_length:
        return f"密码长度不能超过 {policy.max_length} 位"
    if password.lower() in COMMON_PASSWORDS:
        return "此密码过于常见，请更换"
    if sum(c.isdigit() for c in password) < policy.min_digits:
        return f"密码至少包含 {policy.min_digits} 个数字"
    if sum(c.islower() for c in password) < policy.min_lowercase:
        return f"密码至少包含 {policy.min_lowercase} 个小写字母"
    if sum(c.isupper() for c in password) < policy.min_uppercase:
        return f"密码至少包含 {policy.min_uppercase} 个大写字母"
    if sum(c in policy.special_chars for c in password) < policy.min_special:
        return f"密码至少包含 {policy.min_special} 个特殊字符"
    return None
