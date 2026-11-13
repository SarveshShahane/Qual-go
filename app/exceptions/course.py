from fastapi import status
from app.exceptions.base_exception import BaseAppException


class ModuleNotFoundException(BaseAppException):
    def __init__(self, message: str = "Module not found", detail: any = None):
        super().__init__(message=message, status=status.HTTP_404_NOT_FOUND, detail=detail)


class ChapterNotFoundException(BaseAppException):
    def __init__(self, message: str = "Chapter not found", detail: any = None):
        super().__init__(message=message, status=status.HTTP_404_NOT_FOUND, detail=detail)


class TopicNotFoundException(BaseAppException):
    def __init__(self, message: str = "Topic not found", detail: any = None):
        super().__init__(message=message, status=status.HTTP_404_NOT_FOUND, detail=detail)


class InvalidResourceException(BaseAppException):
    def __init__(self, message: str = "Invalid resource specification", detail: any = None):
        super().__init__(message=message, status=status.HTTP_400_BAD_REQUEST, detail=detail)


class DuplicateResourceException(BaseAppException):
    def __init__(self, message: str = "Resource already exists", detail: any = None):
        super().__init__(message=message, status=status.HTTP_409_CONFLICT, detail=detail)


class InvalidContentPathException(BaseAppException):
    def __init__(self, message: str = "Invalid content path", detail: any = None):
        super().__init__(message=message, status=status.HTTP_400_BAD_REQUEST, detail=detail)
