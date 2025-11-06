from __future__ import annotations

from fastapi import HTTPException, Request, status

API_KEY_HEADER = "x-api-key"
API_KEY_VALUE = "test-key"


def require_api_key(request: Request) -> str:
    api_key = request.headers.get(API_KEY_HEADER)
    if api_key != API_KEY_VALUE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key
