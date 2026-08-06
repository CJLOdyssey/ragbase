"""Auth sub-package — split from monolithic auth.py into domain modules.

Endpoints organized by concern:
  - login.py:   /login, /refresh, /logout
  - register.py: /send-register-code, /register, /verify, /resend-verification
  - password.py: /forgot-password, /reset-password, /change-password
  - profile.py:  /config, /me, /merge
"""

from fastapi import APIRouter

from . import login, password, profile, register

router = APIRouter(prefix="/api/auth", tags=["auth"])
router.include_router(login.router)
router.include_router(register.router)
router.include_router(password.router)
router.include_router(profile.router)
