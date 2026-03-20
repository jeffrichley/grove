"""Grove-specific exceptions.

Library and I/O errors are caught and re-raised as these so callers
can handle Grove failures without depending on concrete exception types.
"""


class GroveError(Exception):
    """Base exception for Grove CLI and core operations.

    Raise this type, or a more specific Grove subclass, for any user-visible
    failure that should surface as a concise CLI error message.
    """

    pass


class GroveConfigError(GroveError):
    """Invalid configuration or path supplied by the caller.

    Typical cases include an invalid project root, unsupported interactive
    mode, or other operator-controlled setup errors.
    """

    pass


class GroveManifestError(GroveError):
    """Manifest missing, invalid, or unsupported for the current operation.

    Use for errors involving `.grove/manifest.toml`, including absent manifests,
    invalid contents, unsupported schema versions, or unsafe sync conditions.
    """

    pass


class GrovePackError(GroveError):
    """Pack lookup, compatibility, or dependency resolution failure.

    Use when a requested pack cannot be found, loaded, or resolved with its
    required dependencies.
    """

    pass
