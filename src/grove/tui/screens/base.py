"""Base screen for grove init TUI."""

from collections.abc import Callable
from typing import Any

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import RadioSet


class GroveBaseScreen(Screen[None]):
    """Base for all grove init screens.

    Subclasses override compose_content() to yield the main screen content.
    For screens with a RadioSet, override _radio_actions() and use
    on_radio_set_changed (inherited) to dispatch.
    """

    def compose(self) -> ComposeResult:
        """Compose content from compose_content().

        Yields:
            Widgets from compose_content().
        """
        yield from self.compose_content()

    def compose_content(self) -> ComposeResult:
        """Override in subclasses to yield the main screen content. Default: nothing.

        Yields:
            Widgets; override in subclasses.
        """
        yield from ()  # override in subclasses

    def _radio_actions(self) -> dict[str, Callable[[], Any]]:
        """Map radio button id to no-arg callable. Override in subclasses.

        Returns:
            Dict mapping button id to callable; default empty.
        """
        return {}

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Dispatch to the action for the pressed radio button.

        Uses _radio_actions() to map button id to callable. Subclasses
        override _radio_actions(); do not override this unless you need
        different behavior.

        Args:
            event: RadioSet.Changed with the pressed button.
        """
        radios = event.control
        pressed = radios.pressed_button if radios else None
        if pressed is None:
            return
        actions = self._radio_actions()
        if pressed.id in actions:
            actions[pressed.id]()
