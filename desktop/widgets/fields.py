"""Form field controls: path row, numeric input, text list and form row helper functions."""

from __future__ import annotations

import ast
from functools import lru_cache
import math
from pathlib import Path
import re

import numpy as np
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QValidator,
)
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr

PARAMETER_WIDTH = 220
PARAMETER_HEIGHT = 34
PARAMETER_TITLE_HEIGHT = 36
UNIT_WIDTH = 96
FORMULA_TITLE_FONT_SIZE = 11
FORMULA_UNIT_FONT_SIZE = 8


def parse_number_expression(text: str) -> float:
    """Safely parse numeric literals, scientific notation, and simple arithmetic expressions."""
    source = text.strip()
    if not source:
        raise ValueError("数值不能为空。")
    if len(source) > 64:
        raise ValueError("数值表达式过长。")
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as error:
        raise ValueError(f"无法解析数值表达式“{text}”。") from error

    node_count = 0

    def evaluate(node: ast.AST) -> int | float:
        nonlocal node_count
        node_count += 1
        if node_count > 32:
            raise ValueError("数值表达式过于复杂。")
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and \
                type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.Name) and node.id == "pi":
            return math.pi
        if isinstance(node, ast.UnaryOp) and \
                isinstance(node.op, (ast.UAdd, ast.USub)):
            value = evaluate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and \
                isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if right == 0:
                raise ValueError("数值表达式不能除以零。")
            return left / right
        raise ValueError("仅支持数值、科学计数法、括号和 +、-、*、/。")

    try:
        value = float(evaluate(tree))
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError(f"数值表达式“{text}”超出可用范围。") from error
    if not math.isfinite(value):
        raise ValueError("数值必须是有限实数。")
    return value


def _expression_state(
    text: str,
    position: int,
    minimum: float,
    maximum: float,
    *,
    integer: bool,
) -> tuple[QValidator.State, str, int]:
    """Returns validation status to Qt value boxes that allows expressions to be typed step by step."""
    candidate = text.strip().lower()
    incomplete = (
        candidate in {"", "+", "-", ".", "+.", "-.", "("}
        or candidate.endswith(("+", "-", "*", "/", "(", "e", "e+", "e-"))
        or candidate.count("(") > candidate.count(")")
    )
    try:
        value = parse_number_expression(candidate)
    except ValueError:
        state = QValidator.Intermediate if incomplete else QValidator.Invalid
        return state, text, position
    if integer and not value.is_integer():
        return QValidator.Invalid, text, position
    if minimum <= value <= maximum:
        return QValidator.Acceptable, text, position
    return QValidator.Intermediate, text, position


class NoWheelSpinBox(QSpinBox):
    """The integer box supports scientific notation; the expression result must still be an integer."""

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()

    def valueFromText(self, text: str) -> int:  # noqa: N802
        return int(parse_number_expression(text))

    def validate(self, text: str, position: int):  # noqa: N802
        return _expression_state(
            text, position, self.minimum(), self.maximum(), integer=True)


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    """Allows keyboard and button input, but does not use the mouse wheel to change values."""

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class ScientificDoubleSpinBox(NoWheelDoubleSpinBox):
    """The floating point box retains user expressions and provides evaluated values for interface verification."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        compact: bool = False,
    ) -> None:
        super().__init__(parent)
        self.compact = compact
        self._expression_text: str | None = None

    def textFromValue(self, value: float) -> str:  # noqa: N802
        if self._expression_text is not None:
            try:
                if parse_number_expression(self._expression_text) == value:
                    return self._expression_text
            except ValueError:
                pass
            self._expression_text = None
        if not self.compact:
            return super().textFromValue(value)
        # Keep at least 10 significant digits; g format automatically removes meaningless trailing zeros.
        precision = max(10, min(self.decimals(), 15))
        if value != 0.0 and (
            abs(value) >= 1.0e6 or abs(value) < 1.0e-4
        ):
            mantissa, exponent = f"{value:.{precision - 1}e}".split("e")
            mantissa = mantissa.rstrip("0").rstrip(".")
            return f"{mantissa}e{exponent}"
        return f"{value:.{precision}g}"

    def valueFromText(self, text: str) -> float:  # noqa: N802
        value = parse_number_expression(text)
        self._expression_text = text.strip()
        return value

    def validate(self, text: str, position: int):  # noqa: N802
        return _expression_state(
            text, position, self.minimum(), self.maximum(), integer=False)

    def setValue(self, value: float) -> None:  # noqa: N802
        self._expression_text = None
        super().setValue(value)

    def stepBy(self, steps: int) -> None:  # noqa: N802
        self._expression_text = None
        super().stepBy(steps)

    def expression_text(self) -> str:
        """Returns the current legal expression; it will not be reformatted to decimal."""
        text = self.cleanText().strip()
        value = parse_number_expression(text)
        if not self.minimum() <= value <= self.maximum():
            raise ValueError("数值表达式超出字段允许范围。")
        return text

    def number_source(self) -> float | str:
        """The four expressions are handed over to the Worker; ordinary values continue to use compatible JSON numbers."""
        text = self.expression_text()
        if re.fullmatch(
            r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?",
            text,
        ):
            return parse_number_expression(text)
        return text

    def saved_value(self) -> float | str:
        """Parameter snapshots give priority to saving the expressions actually entered by the user."""
        return self._expression_text \
            if self._expression_text is not None else self.value()

    def set_expression_text(self, text: str) -> None:
        """Restores a legal expression, keeping its original text visible."""
        source = text.strip()
        value = parse_number_expression(source)
        if not self.minimum() <= value <= self.maximum():
            raise ValueError("数值表达式超出字段允许范围。")
        self._expression_text = source
        super().setValue(value)
        self.lineEdit().setText(source)


class NoWheelComboBox(QComboBox):
    """The drop-down selection box does not respond to the scroll wheel to avoid accidentally changing options when scrolling the page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(PARAMETER_HEIGHT)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setAlignment(Qt.AlignCenter)
        self.setInsertPolicy(QComboBox.NoInsert)

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.showPopup()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        """Explicitly draw drop-down buttons to prevent platform themes from hiding native arrows."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        area = self.rect().adjusted(self.width() - 27, 1, -1, -1)
        color = self.palette().color(self.foregroundRole())
        color.setAlpha(230 if self.isEnabled() else 90)
        divider = QColor(color)
        divider.setAlpha(80 if self.isEnabled() else 35)
        painter.setPen(QPen(divider, 1.0))
        painter.drawLine(area.topLeft(), area.bottomLeft())
        painter.setPen(
            QPen(color, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        cx = area.center().x()
        cy = area.center().y() + 1
        painter.drawLine(cx - 4, cy - 2, cx, cy + 2)
        painter.drawLine(cx, cy + 2, cx + 4, cy - 2)


class PathRow(QWidget):
    """Path input line: system selector + paste/drag-and-drop text box."""

    changed = Signal()

    def __init__(
        self,
        *,
        directory: bool,
        placeholder: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.directory = directory
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setAcceptDrops(True)
        self.edit.installEventFilter(self)
        button = QPushButton("选择…")
        button.setFixedWidth(72)
        button.clicked.connect(self.choose)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit, 1)
        layout.addWidget(button)
        self.edit.editingFinished.connect(self.changed)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        from PySide6.QtCore import QEvent

        if watched is self.edit and event.type() == QEvent.Drop:
            urls = event.mimeData().urls()
            if urls:
                self.edit.setText(urls[0].toLocalFile())
                self.changed.emit()
            return True
        if watched is self.edit and event.type() == QEvent.DragEnter:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            return True
        return super().eventFilter(watched, event)

    def choose(self) -> None:
        current = self.edit.text().strip()
        if self.directory:
            value = QFileDialog.getExistingDirectory(
                self, tr("选择目录"), current)
        else:
            value, _ = QFileDialog.getOpenFileName(
                self, tr("选择文件"), current,
                tr("BHAC 网格 (grid_mks.in);;所有文件 (*)"))
        if value:
            self.edit.setText(value)
            self.changed.emit()

    def text(self) -> str:
        return self.edit.text().strip()

    def set_text(self, value: str) -> None:
        self.edit.setText(value)

    def path(self) -> Path:
        return Path(self.text()).expanduser()


def make_int(
    value: int,
    minimum: int,
    maximum: int,
    *,
    suffix: str = "",
) -> QSpinBox:
    box = NoWheelSpinBox()
    box.setRange(minimum, maximum)
    box.setValue(value)
    box.setAlignment(Qt.AlignCenter)
    box.setFixedHeight(PARAMETER_HEIGHT)
    box.lineEdit().setToolTip(
        "支持普通整数和科学计数法；表达式结果必须为整数。")
    if suffix:
        box.setSuffix(suffix)
    return box


def make_float(
    value: float,
    minimum: float,
    maximum: float,
    *,
    decimals: int = 6,
    suffix: str = "",
    scientific: bool = False,
) -> QDoubleSpinBox:
    box = ScientificDoubleSpinBox(compact=True)
    box.setDecimals(decimals)
    box.setRange(minimum, maximum)
    box.setValue(value)
    box.setAlignment(Qt.AlignCenter)
    box.setFixedHeight(PARAMETER_HEIGHT)
    box.lineEdit().setToolTip(
        "支持普通数值、6.5e9、3/4、pi 和带括号的简单四则运算；"
        "输入的表达式会保留到计算进程。")
    if suffix:
        box.setSuffix(suffix)
    if scientific:
        box.setStepType(QDoubleSpinBox.AdaptiveDecimalStepType)
    return box


def add_row(
    form: QFormLayout,
    label: str,
    widget: QWidget,
    hint: str = "",
    *,
    unit: str = "",
) -> None:
    """Add compact parameter rows and display values, units and supplementary instructions separately."""
    if isinstance(form, ParameterGrid):
        form.add_parameter(label, widget, hint=hint, unit=unit)
        return

    compact = isinstance(
        widget,
        (QAbstractSpinBox, QComboBox, TextListField),
    )
    if compact:
        widget.setFixedWidth(PARAMETER_WIDTH)

    if compact or unit or hint:
        container = QWidget()
        container.setObjectName("parameterRow")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(10)
        value_row.addWidget(widget, 0 if compact else 1)
        if compact or unit:
            unit_label = QLabel(unit or "—")
            unit_label.setFixedWidth(UNIT_WIDTH)
            unit_label.setProperty("unit", True)
            unit_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value_row.addWidget(unit_label)
        if compact or unit:
            value_row.addStretch(1)
        layout.addLayout(value_row)

    if hint:
        note = QLabel(hint)
        note.setProperty("dim", True)
        note.setWordWrap(True)
        layout.addWidget(note)

    if compact or unit or hint:
        form.addRow(label, container)
    else:
        form.addRow(label, widget)


class TextListField(QWidget):
    """Input box for a comma-separated list of values, such as a frequency list or a thread list."""

    def __init__(
        self,
        values: list[float] | list[int],
        *,
        integer: bool = False,
        hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.integer = integer
        self.edit = QLineEdit()
        self.edit.setAlignment(Qt.AlignCenter)
        self.edit.setFixedHeight(PARAMETER_HEIGHT)
        self.edit.setToolTip(
            "各项支持普通数值、6.5e9、3/4、pi 和简单四则运算。")
        if not hint:
            self.setFixedHeight(PARAMETER_HEIGHT)
        self.setObjectName("parameterField")
        self.set_values(values)
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addRow(self.edit)
        if hint:
            note = QLabel(hint)
            note.setProperty("dim", True)
            note.setWordWrap(True)
            layout.addRow(note)

    def set_values(self, values: list[float] | list[int]) -> None:
        self.edit.setText(", ".join(
            str(int(value)) if self.integer else f"{float(value):g}"
            for value in values))

    def parse(self) -> list[float] | list[int]:
        """Parse text into a list of values; format errors throw ValueError with Chinese description."""
        text = self.edit.text().strip()
        if not text:
            raise ValueError("列表不能为空：请至少填写一个数值。")
        values: list[float] | list[int] = []
        for chunk in text.replace("，", ",").split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                number = parse_number_expression(chunk)
            except ValueError as exc:
                raise ValueError(
                    f"无法解析列表项“{chunk}”：应为数值或简单分数。") from exc
            if self.integer:
                if number != int(number):
                    raise ValueError(f"列表项“{chunk}”应为整数。")
                values.append(int(number))
            else:
                values.append(number)
        if not values:
            raise ValueError("列表不能为空：请至少填写一个数值。")
        return values

    def expressions(self) -> list[str]:
        """Validates and returns the original expression for each list item."""
        self.parse()
        return [
            chunk.strip()
            for chunk in self.edit.text().replace("，", ",").split(",")
            if chunk.strip()
        ]

    def number_sources(self) -> list[float | str]:
        """Returns a number or expression suitable for writing to Worker JSON."""
        result: list[float | str] = []
        for expression in self.expressions():
            if re.fullmatch(
                r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?",
                expression,
            ):
                value = parse_number_expression(expression)
                result.append(int(value) if self.integer else value)
            else:
                result.append(expression)
        return result


_GREEK = {
    "α": r"{\alpha}",
    "β": r"{\beta}",
    "γ": r"{\gamma}",
    "Δ": r"{\Delta}",
    "ε": r"{\varepsilon}",
    "θ": r"{\theta}",
    "λ": r"{\lambda}",
    "ν": r"{\nu}",
    "ρ": r"{\rho}",
    "σ": r"{\sigma}",
    "φ": r"{\phi}",
    "Φ": r"{\Phi}",
    "Ω": r"{\Omega}",
    "Θ": r"{\Theta}",
    "η": r"{\eta}",
    "π": r"{\pi}",
    "☉": r"{\odot}",
}


def _subscript(match: re.Match[str]) -> str:
    value = re.sub(r"<[^>]+>", "", match.group(1))
    value = "".join(_GREEK.get(char, char) for char in value)
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9, ]+", value):
        value = rf"\mathrm{{{value.replace(' ', '')}}}"
    return rf"_{{{value}}}"


def _superscript(match: re.Match[str]) -> str:
    value = re.sub(r"<[^>]+>", "", match.group(1)).replace("−", "-")
    return rf"^{{{value}}}"


def _as_math(text: str) -> str | None:
    """Convert a small number of existing Qt rich text symbols into mathtext expressions."""
    stripped = text.strip()
    if stripped.startswith("$") and stripped.endswith("$"):
        return stripped
    has_markup = bool(re.search(r"</?(?:i|sub|sup)>", stripped))
    has_symbol = any(char in stripped for char in _GREEK) or "Ṁ" in stripped
    if (not has_markup and not has_symbol) or re.search(
            r"[\u4e00-\u9fff]", stripped):
        return None
    value = re.sub(r"<sub>(.*?)</sub>", _subscript, stripped)
    value = re.sub(r"<sup>(.*?)</sup>", _superscript, value)
    value = re.sub(r"</?i>", "", value)
    value = value.replace("Ṁ", r"\dot{M}").replace("−", "-")
    value = "".join(_GREEK.get(char, char) for char in value)
    value = value.replace("cos ", r"\cos ")
    return f"${value}$"


@lru_cache(maxsize=512)
def _formula_image(
    expression: str,
    color_name: str,
    font_size: int,
    dpi: int,
) -> QImage:
    """Generate cached formula plots with transparency channels using Matplotlib mathtext."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.mathtext import MathTextParser

    parsed = MathTextParser("agg").parse(
        expression,
        dpi=dpi,
        prop=FontProperties(size=font_size),
    )
    alpha = np.asarray(parsed.image, dtype=np.uint8)
    rgba = np.empty((*alpha.shape, 4), dtype=np.uint8)
    color = QColor(color_name)
    rgba[..., 0] = color.red()
    rgba[..., 1] = color.green()
    rgba[..., 2] = color.blue()
    rgba[..., 3] = alpha
    return QImage(
        rgba.data,
        rgba.shape[1],
        rgba.shape[0],
        rgba.strides[0],
        QImage.Format_RGBA8888,
    ).copy()


class FormulaLabel(QLabel):
    """Ordinary Chinese uses Qt text, and mathematical expressions use mathtext for typesetting."""

    def __init__(
        self,
        text: str,
        *,
        font_size: int,
        fixed_color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.source = text
        self.expression = _as_math(text)
        self.formula_font_size = font_size
        self.fixed_color = fixed_color
        if self.expression is None:
            self.setText(text)
            self.setTextFormat(Qt.RichText)
        else:
            self._refresh_formula()

    def _refresh_formula(self) -> None:
        if self.expression is None:
            return
        color = self.fixed_color or self.palette().color(
            self.foregroundRole()).name(QColor.HexRgb)
        dpr = max(1.0, self.devicePixelRatioF())
        try:
            image = _formula_image(
                self.expression,
                color,
                self.formula_font_size,
                max(96, round(120 * dpr)),
            )
        except ValueError:
            self.expression = None
            self.setText(self.source)
            self.setTextFormat(Qt.RichText)
            return
        pixmap = QPixmap.fromImage(image)
        pixmap.setDevicePixelRatio(dpr)
        self.setPixmap(pixmap)

    def changeEvent(self, event) -> None:  # noqa: N802
        super().changeEvent(event)
        if event.type() in {
            QEvent.ApplicationPaletteChange,
            QEvent.PaletteChange,
            QEvent.FontChange,
        }:
            self._refresh_formula()


class ParameterCard(QFrame):
    """A materialized card for a parameter: symbol title, centered input, units, and description."""

    def __init__(
        self,
        title: str,
        widget: QWidget,
        *,
        hint: str = "",
        unit: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("parameterCard")

        title_label = FormulaLabel(
            title,
            font_size=FORMULA_TITLE_FONT_SIZE,
            fixed_color="#f7f9fc",
        )
        title_label.setProperty("parameterTitle", True)
        title_label.setToolTip(hint)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setMinimumWidth(96)
        title_label.setFixedHeight(PARAMETER_TITLE_HEIGHT)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(title_label)
        header.addStretch(1)

        compact = isinstance(
            widget, (QAbstractSpinBox, QComboBox, TextListField))
        if compact:
            widget.setFixedWidth(PARAMETER_WIDTH)

        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(10)
        if compact:
            value_row.addWidget(widget)
        else:
            value_row.addWidget(widget, 1)
        if compact or unit:
            unit_label = FormulaLabel(
                unit or "—", font_size=FORMULA_UNIT_FONT_SIZE)
            unit_label.setFixedWidth(UNIT_WIDTH)
            unit_label.setFixedHeight(PARAMETER_HEIGHT)
            unit_label.setProperty("unitChip", True)
            unit_label.setAlignment(Qt.AlignCenter)
            value_row.addWidget(unit_label)
        if compact:
            value_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 11)
        layout.setSpacing(8)
        layout.addLayout(header)
        layout.addLayout(value_row)
        # Cards without descriptions also retain the same description area to ensure that pairs of input boxes are vertically aligned.
        note = QLabel(hint or " ")
        note.setTextFormat(Qt.RichText)
        note.setProperty("parameterHint", True)
        note.setWordWrap(True)
        note.setMinimumHeight(18)
        layout.addWidget(note)


class ParameterGrid(QGridLayout):
    """Automatically arrange parameter cards by two columns, with path and multi-line fields automatically spanning the entire row."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        columns: int = 2,
    ) -> None:
        super().__init__(parent)
        self.columns = max(1, columns)
        self._row = 0
        self._column = 0
        self.setContentsMargins(0, 0, 0, 0)
        self.setHorizontalSpacing(12)
        self.setVerticalSpacing(12)
        self.setAlignment(Qt.AlignTop)
        for column in range(self.columns):
            self.setColumnStretch(column, 1)

    def _flush(self) -> None:
        if self._column:
            self._row += 1
            self._column = 0

    def add_parameter(
        self,
        title: str,
        widget: QWidget,
        *,
        hint: str = "",
        unit: str = "",
    ) -> ParameterCard:
        wide = isinstance(
            widget, (PathRow, QPlainTextEdit, QTextEdit, QLabel))
        card = ParameterCard(title, widget, hint=hint, unit=unit)
        if wide:
            self._flush()
            self.addWidget(card, self._row, 0, 1, self.columns)
            self._row += 1
        else:
            self.addWidget(card, self._row, self._column)
            self._column += 1
            if self._column >= self.columns:
                self._row += 1
                self._column = 0
        return card

    def add_full_row(self, widget: QWidget) -> None:
        self._flush()
        self.addWidget(widget, self._row, 0, 1, self.columns)
        self._row += 1

    def addRow(self, *items) -> None:  # noqa: N802
        """Compatible with the original QFormLayout's additional instructions, checkboxes and action buttons."""
        if len(items) == 1 and isinstance(items[0], QWidget):
            self.add_full_row(items[0])
            return
        if len(items) == 2 and isinstance(items[1], QWidget):
            title, widget = items
            if str(title):
                self.add_parameter(str(title), widget)
            else:
                self.add_full_row(widget)
            return
        raise TypeError("ParameterGrid.addRow only accepts QWidget rows.")


def set_widget_error(widget: QWidget, message: str | None) -> None:
    """Mark or clear errors on the field (red border + tooltip)."""
    if message:
        widget.setStyleSheet("border: 1px solid #d9534f;")
        widget.setToolTip(message)
    else:
        widget.setStyleSheet("")
        widget.setToolTip("")
