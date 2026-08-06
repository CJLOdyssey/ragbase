"""Password strength validation for registration and password changes."""

from dataclasses import dataclass

COMMON_PASSWORDS = {
    "password", "password123", "admin123", "admin888",
    "12345678", "qwerty123", "letmein", "welcome",
    "monkey", "dragon", "passw0rd", "abc123",
    "123456789", "iloveyou", "trustno1", "sunshine",
    "master", "access", "shadow", "michael",
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
