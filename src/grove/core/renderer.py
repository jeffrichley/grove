"""Template renderer: fill Jinja2 templates with a variable dict.

Caller resolves template_path from pack root + PlannedFile.src.
"""

from pathlib import Path

from jinja2 import StrictUndefined, Template


def render(template_path: Path, variables: dict[str, object]) -> str:
    """Render a single template file with the given variables.

    Uses Jinja2. Missing variables referenced in the template raise
    jinja2.UndefinedError (no silent fallback per project rules).
    Does not resolve {% include %} or {% extends %} (single-file only).

    Args:
        template_path: Path to the template file (e.g. .j2).
        variables: Dict of variable names to values for substitution.

    Returns:
        Rendered content as a string.

    Raises:
        FileNotFoundError: If template_path does not exist.
    """
    path = template_path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")

    source = path.read_text(encoding="utf-8")
    template = Template(source, autoescape=False, undefined=StrictUndefined)
    return template.render(**variables)
