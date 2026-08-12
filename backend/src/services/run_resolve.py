"""Run credential resolution — shared by create_run and continue_run.

Single source for the vault lookup chain (key_id → model match → default),
returning ``(api_key, api_base, image_model)``.
"""

from typing import Any

from core.infra.logging_config import get_logger
from repository import get_api_key_for_model, get_api_key_for_use, get_default_api_key

logger = get_logger(__name__)


async def resolve_credentials(
    user_id: str,
    model: str,
    key_id: str | None = None,
    tolerate_vault_errors: bool = False,
) -> tuple[str | None, str | None, bool]:
    """Resolve the key chain for a run.

    Chain: explicit ``key_id`` → key whose models list matches ``model`` →
    user default. Returns ``(api_key, api_base, image_model)``.

    When ``tolerate_vault_errors`` is True, vault failures degrade to
    ``(None, None, False)`` instead of raising (continue path behavior).
    """
    api_key: str | None = None
    api_base: str | None = None
    image_model = False

    def apply(entry: dict[str, Any]) -> None:
        nonlocal api_key, api_base, image_model
        api_key = entry.get("api_key") or api_key
        api_base = entry.get("base_url") or api_base
        image_model = (entry.get("model_types") or {}).get(model) == "image"

    try:
        if key_id:
            entry = await get_api_key_for_use(key_id, user_id)
            if entry:
                apply(entry)
        if not api_key and model:
            entry = await get_api_key_for_model(model, user_id)
            if entry:
                apply(entry)
        if not api_key:
            entry = await get_default_api_key(user_id)
            if entry:
                apply(entry)
    except Exception:
        if not tolerate_vault_errors:
            raise
        logger.warning("Key vault lookup failed — using env var fallback")

    return api_key, api_base, image_model
