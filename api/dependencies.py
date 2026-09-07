from fastapi import Security, Depends
from fastapi.security import APIKeyHeader
import config
from api.exceptions import UnauthorizedError

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key or api_key != config.DM_API_KEY:
        raise UnauthorizedError(message="Invalid or missing API key")
    return api_key
