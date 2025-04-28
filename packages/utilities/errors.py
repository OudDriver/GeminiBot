class DockerExecutionError(Exception):
    """Base exception for Docker execution issues."""


class DockerConnectionError(DockerExecutionError):
    """Error connecting to or initializing Docker."""


class DockerImageNotFoundError(DockerExecutionError):
    """Required Docker image not found."""


class DockerContainerError(DockerExecutionError):
    """Error during container runtime or setup."""

class HandleAttachmentError(Exception):
    """Error during handling attachments."""

    def __init__(self, file_name: str) -> None:
        """Initialize for the properties."""
        self.file_name = file_name
