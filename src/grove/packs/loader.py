"""Load pack manifests from disk.

Discovery order in a pack directory: pack.toml, then pack.yaml, then pack.yml
(prefer TOML when present). Builtins use pack.toml. Schema matches
PackManifest in grove.core.models; contributes may include templates,
setup_questions, and rules with path triggers (e.g. contributes.rules[].paths).
Template paths in contributes are relative to the pack root.
"""

import tomllib
from pathlib import Path

from grove.core.models import PackManifest


def _find_manifest_path(pack_root: Path) -> Path | None:
    """Return path to pack manifest file, or None if not found.

    Discovery order: pack.toml, pack.yaml, pack.yml (TOML only implemented).

    Args:
        pack_root: Directory containing the pack (e.g. grove/packs/builtins/base).

    Returns:
        Path to pack.toml/pack.yaml/pack.yml if present, else None.
    """
    for name in ("pack.toml", "pack.yaml", "pack.yml"):
        p = pack_root / name
        if p.is_file():
            return p
    return None


def load_pack_manifest(pack_root: Path) -> PackManifest:
    """Load and validate a pack manifest from a directory.

    Args:
        pack_root: Directory containing pack.toml (or pack.yaml/pack.yml).

    Returns:
        Validated PackManifest. Template paths in contributes are relative
        to pack_root.

    Raises:
        FileNotFoundError: No pack.toml / pack.yaml / pack.yml in pack_root.
        ValueError: Manifest invalid or missing required fields.
    """
    pack_root = pack_root.resolve()
    manifest_path = _find_manifest_path(pack_root)
    if manifest_path is None:
        raise FileNotFoundError(
            f"No pack manifest (pack.toml or pack.yaml) in {pack_root}"
        )

    if manifest_path.suffix in (".yaml", ".yml"):
        raise ValueError("YAML pack manifests not yet supported; use pack.toml")

    with manifest_path.open("rb") as f:
        data = tomllib.load(f)

    return _parse_pack_toml(data, pack_root)


def _get_str(data: dict[str, object], key: str, default: str = "") -> str:
    """Get a string value from a dict, with default.

    Args:
        data: Source dict.
        key: Key to look up.
        default: Value if key missing or None.

    Returns:
        str value or default.
    """
    v = data.get(key, default)
    return str(v) if v is not None else default


def _get_list(data: dict[str, object], key: str) -> list[str]:
    """Get a list of strings from a dict.

    Args:
        data: Source dict.
        key: Key to look up.

    Returns:
        List of strings; empty if key missing or not a list.
    """
    v = data.get(key)
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def _get_contributes(data: dict[str, object]) -> dict[str, object]:
    """Get and normalize contributes dict from pack data.

    Args:
        data: Pack TOML data dict.

    Returns:
        Normalized contributes dict; empty if missing.
    """
    v = data.get("contributes")
    if v is None:
        return {}
    if isinstance(v, dict):
        return _normalize_contributes(v)
    return {}


def _parse_pack_toml(data: object, pack_root: Path) -> PackManifest:
    """Parse TOML data into PackManifest. Validates required fields.

    Args:
        data: Parsed TOML (dict from tomllib.load).
        pack_root: Absolute pack root directory for template resolution.

    Returns:
        Validated PackManifest.

    Raises:
        ValueError: If data is not a dict or required fields missing/invalid.
    """
    if not isinstance(data, dict):
        raise ValueError("Pack manifest must be a TOML table")
    d = data
    for key in ("id", "name", "version"):
        if key not in d:
            raise ValueError(f"Pack manifest missing required field: {key}")
    return PackManifest(
        id=_get_str(d, "id").strip() or _raise("id"),
        name=_get_str(d, "name").strip() or _raise("name"),
        version=_get_str(d, "version").strip() or _raise("version"),
        depends_on=_get_list(d, "depends_on"),
        compatible_with=_get_list(d, "compatible_with"),
        activates_when=_get_list(d, "activates_when"),
        contributes=_get_contributes(d),
        root_dir=pack_root,
    )


def _raise(field: str) -> str:
    """Raise ValueError for missing/invalid pack manifest field.

    Args:
        field: Field name to include in the error message.

    Raises:
        ValueError: Always; used for required non-empty fields.
    """
    raise ValueError(f"Pack manifest field '{field}' must be non-empty")


def _normalize_contributes(raw: dict) -> dict[str, object]:
    """Ensure contributes is JSON-serializable and has expected shape.

    Args:
        raw: Raw contributes dict from TOML.

    Returns:
        Normalized dict (lists/dicts recursively normalized).
    """
    out: dict[str, object] = {}
    for k, v in raw.items():
        if v is None:
            continue
        if isinstance(v, list):
            out[k] = [_normalize_contributes_item(x) for x in v]
        elif isinstance(v, dict):
            out[k] = _normalize_contributes(v)
        else:
            out[k] = v
    return out


def _normalize_contributes_item(x: object) -> object:
    """Normalize one item (dict or passthrough).

    Args:
        x: Item from contributes (dict or scalar).

    Returns:
        Normalized dict or x unchanged.
    """
    if isinstance(x, dict):
        return _normalize_contributes(x)
    return x
