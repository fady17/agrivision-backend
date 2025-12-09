class AgriVisionException(Exception):
    """Base exception for application"""
    pass

class AIServiceError(AgriVisionException):
    """Gemini is down or timing out"""
    pass

class StorageError(AgriVisionException):
    """MinIO upload failed"""
    pass

class ImageValidationError(AgriVisionException):
    """File is corrupted or format is wrong"""
    pass