class AppClientError(Exception):
    """Base exception for external service HTTP clients."""
    pass

class APIUnavailableError(AppClientError):
    """Raised when an external API service is unreachable or timing out."""
    def __init__(self, service_name: str, message: str = "Service unavailable"):
        self.service_name = service_name
        self.message = message
        super().__init__(f"[{service_name}] {message}")

class APIResponseError(AppClientError):
    """Raised when an external API returns a non-2xx status code."""
    def __init__(self, service_name: str, status_code: int, detail: str):
        self.service_name = service_name
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"[{service_name}] Returned {status_code}: {detail}")
