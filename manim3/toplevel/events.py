from __future__ import annotations


from abc import (
    ABC,
    abstractmethod
)
from typing import (
    Never,
    Self
)

import attrs

from ..timelines.timeline.conditions import Condition
from .toplevel import Toplevel


class EventCapturedCondition(Condition):
    __slots__ = (
        "_event",
        "_captured_event"
    )

    def __init__(
        self: Self,
        event: Event
    ) -> None:
        super().__init__()
        self._event: Event = event
        self._captured_event: Event | None = None

    def judge(
        self: Self
    ) -> bool:
        captured_event = Toplevel._get_window().capture_event(self._event)
        if captured_event is not None:
            self._captured_event = captured_event
            return True
        return False

    def get_captured_event(
        self: Self
    ) -> Event | None:
        return self._captured_event


@attrs.frozen(kw_only=True)
class Event(ABC):
    @abstractmethod
    def _capture(
        self: Self,
        event: Event
    ) -> bool:
        pass

    @classmethod
    def _match(
        cls: type[Self],
        required_value: int | None,
        value: int | None,
        *,
        masked: bool
    ) -> bool:
        return (
            required_value is None
            or value is None
            or required_value == (value & required_value if masked else value)
        )

    def captured(
        self: Self
    ) -> EventCapturedCondition:
        return EventCapturedCondition(self)


@attrs.frozen(kw_only=True)
class KeyPressEvent(Event):
    symbol: int | None
    modifiers: int | None

    def _capture(
        self: Self,
        event: Event
    ) -> bool:
        return (
            isinstance(event, KeyPressEvent)
            and self._match(self.symbol, event.symbol, masked=False)
            and self._match(self.modifiers, event.modifiers, masked=True)
        )


@attrs.frozen(kw_only=True)
class KeyReleaseEvent(Event):
    symbol: int | None
    modifiers: int | None

    def _capture(
        self: Self,
        event: Event
    ) -> bool:
        return (
            isinstance(event, KeyReleaseEvent)
            and self._match(self.symbol, event.symbol, masked=False)
            and self._match(self.modifiers, event.modifiers, masked=True)
        )


@attrs.frozen(kw_only=True)
class MouseMotionEvent(Event):
    x: int | None
    y: int | None
    dx: int | None
    dy: int | None

    def _capture(
        self: Self,
        event: Event
    ) -> bool:
        return isinstance(event, MouseMotionEvent)


@attrs.frozen(kw_only=True)
class MouseDragEvent(Event):
    buttons: int | None
    modifiers: int | None
    x: int | None
    y: int | None
    dx: int | None
    dy: int | None

    def _capture(
        self: Self,
        event: Event
    ) -> bool:
        return (
            isinstance(event, MouseDragEvent)
            and self._match(self.buttons, event.buttons, masked=True)
            and self._match(self.modifiers, event.modifiers, masked=True)
        )


@attrs.frozen(kw_only=True)
class MousePressEvent(Event):
    buttons: int | None
    modifiers: int | None
    x: int | None
    y: int | None

    def _capture(
        self: Self,
        event: Event
    ) -> bool:
        return (
            isinstance(event, MousePressEvent)
            and self._match(self.buttons, event.buttons, masked=True)
            and self._match(self.modifiers, event.modifiers, masked=True)
        )


@attrs.frozen(kw_only=True)
class MouseReleaseEvent(Event):
    buttons: int | None
    modifiers: int | None
    x: int | None
    y: int | None

    def _capture(
        self: Self,
        event: Event
    ) -> bool:
        return (
            isinstance(event, MouseReleaseEvent)
            and self._match(self.buttons, event.buttons, masked=True)
            and self._match(self.modifiers, event.modifiers, masked=True)
        )


@attrs.frozen(kw_only=True)
class MouseScrollEvent(Event):
    x: int | None
    y: int | None
    scroll_x: float | None
    scroll_y: float | None

    def _capture(
        self: Self,
        event: Event
    ) -> bool:
        return isinstance(event, MouseScrollEvent)


class Events:
    __slots__ = ()

    def __new__(
        cls: type[Self]
    ) -> Never:
        raise TypeError

    @classmethod
    def key_press(
        cls: type[Self],
        symbol: int | None = None,
        modifiers: int | None = None
    ) -> KeyPressEvent:
        return KeyPressEvent(
            symbol=symbol,
            modifiers=modifiers
        )

    @classmethod
    def key_release(
        cls: type[Self],
        symbol: int | None = None,
        modifiers: int | None = None
    ) -> KeyReleaseEvent:
        return KeyReleaseEvent(
            symbol=symbol,
            modifiers=modifiers
        )

    @classmethod
    def mouse_motion(
        cls: type[Self],
        x: int | None = None,
        y: int | None = None,
        dx: int | None = None,
        dy: int | None = None
    ) -> MouseMotionEvent:
        return MouseMotionEvent(
            x=x,
            y=y,
            dx=dx,
            dy=dy
        )

    @classmethod
    def mouse_drag(
        cls: type[Self],
        buttons: int | None = None,
        modifiers: int | None = None,
        x: int | None = None,
        y: int | None = None,
        dx: int | None = None,
        dy: int | None = None
    ) -> MouseDragEvent:
        return MouseDragEvent(
            buttons=buttons,
            modifiers=modifiers,
            x=x,
            y=y,
            dx=dx,
            dy=dy
        )

    @classmethod
    def mouse_press(
        cls: type[Self],
        buttons: int | None = None,
        modifiers: int | None = None,
        x: int | None = None,
        y: int | None = None
    ) -> MousePressEvent:
        return MousePressEvent(
            buttons=buttons,
            modifiers=modifiers,
            x=x,
            y=y
        )

    @classmethod
    def mouse_release(
        cls: type[Self],
        buttons: int | None = None,
        modifiers: int | None = None,
        x: int | None = None,
        y: int | None = None
    ) -> MouseReleaseEvent:
        return MouseReleaseEvent(
            buttons=buttons,
            modifiers=modifiers,
            x=x,
            y=y
        )

    @classmethod
    def mouse_scroll(
        cls: type[Self],
        x: int | None = None,
        y: int | None = None,
        scroll_x: float | None = None,
        scroll_y: float | None = None
    ) -> MouseScrollEvent:
        return MouseScrollEvent(
            x=x,
            y=y,
            scroll_x=scroll_x,
            scroll_y=scroll_y
        )
