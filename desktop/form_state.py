"""Stable snapshots, restoration and change monitoring of cross-page form parameters."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QPlainTextEdit,
    QSpinBox,
)

from .widgets.fields import ScientificDoubleSpinBox, TextListField

STATE_VERSION = 1

Field = QCheckBox | QComboBox | QDoubleSpinBox | QSpinBox | \
    QPlainTextEdit | TextListField


def _walk_value(
    key: str,
    value: Any,
    seen: set[int],
) -> Iterator[tuple[str, Field]]:
    if isinstance(value, (
        QCheckBox,
        QComboBox,
        QDoubleSpinBox,
        QSpinBox,
        QPlainTextEdit,
        TextListField,
    )):
        identity = id(value)
        if identity not in seen:
            seen.add(identity)
            yield key, value
        return
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from _walk_value(
                f"{key}.{child_key}", child, seen)


def iter_fields(
    roots: Iterable[tuple[str, object]],
) -> Iterator[tuple[str, Field]]:
    """Enumerate persistable fields by stable Python property names and eliminate shared control aliases."""
    seen: set[int] = set()
    for prefix, root in roots:
        for name, value in vars(root).items():
            yield from _walk_value(f"{prefix}.{name}", value, seen)


def capture_state(
    roots: Iterable[tuple[str, object]],
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect form values; invalid list text inherits the most recent valid snapshot."""
    values = dict(previous or {})
    for key, field in iter_fields(roots):
        if isinstance(field, TextListField):
            try:
                field.parse()
            except ValueError:
                continue
            values[key] = field.edit.text()
        elif isinstance(field, QPlainTextEdit):
            values[key] = field.toPlainText()
        elif isinstance(field, QComboBox):
            values[key] = {
                "data": field.currentData(),
                "text": field.currentText(),
            }
        elif isinstance(field, QCheckBox):
            values[key] = field.isChecked()
        elif isinstance(field, QSpinBox):
            values[key] = field.value()
        elif isinstance(field, ScientificDoubleSpinBox):
            values[key] = field.saved_value()
        elif isinstance(field, QDoubleSpinBox):
            values[key] = field.value()
    return values


def _restore_field(field: Field, value: Any) -> bool:
    if isinstance(field, TextListField):
        if not isinstance(value, str) or len(value) > 100_000:
            return False
        original = field.edit.text()
        field.edit.setText(value)
        try:
            field.parse()
        except ValueError:
            field.edit.setText(original)
            return False
        return True
    if isinstance(field, QPlainTextEdit):
        if not isinstance(value, str) or len(value) > 100_000:
            return False
        field.setPlainText(value)
        return True
    if isinstance(field, QComboBox):
        if not isinstance(value, dict):
            return False
        index = field.findData(value.get("data"))
        if index < 0 and isinstance(value.get("text"), str):
            index = field.findText(value["text"])
        if index < 0:
            return False
        field.setCurrentIndex(index)
        return True
    if isinstance(field, QCheckBox):
        if not isinstance(value, bool):
            return False
        field.setChecked(value)
        return True
    if isinstance(field, QSpinBox):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        numeric = float(value)
        if not numeric.is_integer() or not field.minimum() <= numeric <= \
                field.maximum():
            return False
        field.setValue(int(numeric))
        return True
    if isinstance(field, ScientificDoubleSpinBox):
        if isinstance(value, str):
            try:
                field.set_expression_text(value)
            except ValueError:
                return False
            return True
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        numeric = float(value)
        if not field.minimum() <= numeric <= field.maximum():
            return False
        field.setValue(numeric)
        return True
    if isinstance(field, QDoubleSpinBox):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        numeric = float(value)
        if not field.minimum() <= numeric <= field.maximum():
            return False
        field.setValue(numeric)
        return True
    return False


def restore_state(
    roots: Iterable[tuple[str, object]],
    values: dict[str, Any],
) -> set[str]:
    """Only fields that still exist in the current version and have valid types and ranges are restored."""
    restored: set[str] = set()
    for key, field in iter_fields(roots):
        if key in values and _restore_field(field, values[key]):
            restored.add(key)
    return restored


def connect_changes(
    roots: Iterable[tuple[str, object]],
    callback: Callable[[], None],
) -> None:
    """Connect all persistent fields to the same anti-shake save callback."""
    for _key, field in iter_fields(roots):
        if isinstance(field, TextListField):
            field.edit.textChanged.connect(callback)
        elif isinstance(field, QPlainTextEdit):
            field.textChanged.connect(callback)
        elif isinstance(field, QComboBox):
            field.currentIndexChanged.connect(callback)
        elif isinstance(field, QCheckBox):
            field.toggled.connect(callback)
        elif isinstance(field, ScientificDoubleSpinBox):
            field.lineEdit().textChanged.connect(callback)
        elif isinstance(field, (QSpinBox, QDoubleSpinBox)):
            field.valueChanged.connect(callback)
