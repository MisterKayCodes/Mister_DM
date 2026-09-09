import asyncio
import httpx
from clients.exceptions import APIUnavailableError, APIResponseError

class BaseClient:
    """
    Base HTTP Client wrapping httpx.AsyncClient.
    Provides standard retry logic, timeout handling, and exception mapping.
    """
    def __init__(self, base_url: str, api_key: str, service_name: str = "External API", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.service_name = service_name
        self.timeout = timeout

    def _get_headers(self) -> dict:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, json: dict = None, params: dict = None, max_retries: int = 3) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        attempt = 0

        while attempt < max_retries:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        json=json,
                        params=params,
                        headers=self._get_headers()
                    )
                    
                    if response.status_code >= 400:
                        raise APIResponseError(
                            service_name=self.service_name,
                            status_code=response.status_code,
                            detail=response.text
                        )
                    
                    return response.json() if response.content else {}

            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt >= max_retries:
                    raise APIUnavailableError(
                        service_name=self.service_name,
                        message=f"Failed after {max_retries} attempts: {str(e)}"
                    )
                await asyncio.sleep(1.0 * attempt)
            except APIResponseError:
                raise
            except Exception as e:
                raise APIUnavailableError(
                    service_name=self.service_name,
                    message=f"Unexpected connection error: {str(e)}"
                )
