class DomainError(Exception):
    """Base class: the API layer maps these to HTTP status codes."""


class InvalidImage(DomainError):
    pass


class ImageTooLarge(DomainError):
    pass
