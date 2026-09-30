"""
author: anrf
date:9/22/2026
desc:
"""
import httpx

from anrf0911_ai.common.config import get_settings


class EcommerceClient:
    def __init__(self, access_token: str):
        self.access_token = access_token

    async def get_json(self, path: str, params: dict | None = None):
        settings = get_settings()
        url = f"{settings.ecommerce_service_url.rstrip('/')}/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        async with httpx.AsyncClient(timeout=8, trust_env=False) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()


if __name__ == "__main__":
    from anrf0911_ai.app.services.auth import AuthService, CurrentUser
    from anrf0911_ai.common.utils import run_async

    token = AuthService().encode_access_token(
        CurrentUser(user_id="u1", role="customer")
    )
    print(run_async(EcommerceClient(token).get_json("/products")))
