"""Grove-specific exceptions.

Library and I/O errors are caught and re-raised as these so callers
can handle Grove failures without depending on concrete exception types.
"""


class GroveError(Exception):
    """Base exception for Grove CLI and core operations."""

    pass


class GroveConfigError(GroveError):
    """Invalid configuration or path (e.g. root not a directory)."""

    pass


class GroveManifestError(GroveError):
    """Manifest missing, invalid, or unsupported schema."""

    pass


class GrovePackError(GroveError):
    """Pack not found or dependency resolution failed."""

    pass
