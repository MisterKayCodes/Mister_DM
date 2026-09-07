from fastapi import HTTPException, status

class APIResponseError(HTTPException):
    def __init__(self, status_code: int, message: str):
        super().__init__(
            status_code=status_code,
            detail={"status": "error", "message": message, "code": status_code}
        )

class UnauthorizedError(APIResponseError):
    def __init__(self, message: str = "Invalid or missing API key"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message
        )

class NotFoundError(APIResponseError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=message
        )

class BadRequestError(APIResponseError):
    def __init__(self, message: str = "Bad request"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message
        )
