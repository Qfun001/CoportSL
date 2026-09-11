"""Desktop interface themes: light and dark color palettes, style sheets and semantic status colors.

The visual language is inspired by images of black holes:
- Dark theme "Event Horizon": nearly black deep space bottom, blue-violet panel, amber "photon ring" accent color
  With teal as the secondary accent color, the navigation and task cards have a soft glow.
- Light theme "Starlight": clean cloud white background, the same set of amber/cyan blue accent colors to ensure contrast.

It is only responsible for visuals and does not contain any business logic; the page uses ``palette(name)`` to select colors,
Apply a global style sheet via ``apply_theme(app, name)``."""

from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtGui import QColor, QPalette

# Semantic status keys: idle/validating/queued/running/cancelling/
# success / failed / cancelled
STATUS_KEYS = (
    "idle", "validating", "queued", "running", "cancelling",
    "success", "failed", "cancelled",
)

STATUS_LABELS = {
    "idle": "空闲",
    "validating": "校验中",
    "queued": "排队",
    "running": "运行中",
    "cancelling": "正在取消",
    "success": "成功",
    "failed": "失败",
    "cancelled": "已取消",
}

_PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "window": "#0b0e16",
        "base": "#10141f",
        "alt": "#161c2b",
        "card": "#141a29",
        "border": "#26304a",
        "border_soft": "#1c2438",
        "text": "#e9edf6",
        "text_dim": "#8d96ac",
        "accent": "#f5a524",
        "accent_deep": "#d97e06",
        "accent_soft": "rgba(245, 165, 36, 38)",
        "accent2": "#53b7f0",
        "accent_text": "#1a1206",
        "nav_hover": "rgba(245, 165, 36, 14)",
        "nav_selected": "rgba(245, 165, 36, 26)",
        "idle": "#6d7689",
        "validating": "#c9a227",
        "queued": "#a97fd4",
        "running": "#53b7f0",
        "cancelling": "#c98736",
        "success": "#3fae6a",
        "failed": "#e05a55",
        "cancelled": "#c98736",
        "warn_bg": "#3a2f12",
        "warn_text": "#eec96a",
        "error_bg": "#3d1d20",
        "error_text": "#f0a09c",
        "info_bg": "#152a3d",
        "info_text": "#8fc8f2",
    },
    "light": {
        "window": "#f2f4f9",
        "base": "#ffffff",
        "alt": "#e9edf5",
        "card": "#ffffff",
        "border": "#c9d2e3",
        "border_soft": "#dde3ef",
        "text": "#1f2735",
        "text_dim": "#5f6b80",
        "accent": "#c96a00",
        "accent_deep": "#a85600",
        "accent_soft": "rgba(201, 106, 0, 26)",
        "accent2": "#0284c7",
        "accent_text": "#ffffff",
        "nav_hover": "rgba(201, 106, 0, 14)",
        "nav_selected": "rgba(201, 106, 0, 24)",
        "idle": "#6b7280",
        "validating": "#8a6d00",
        "queued": "#7a4b91",
        "running": "#0284c7",
        "cancelling": "#95580f",
        "success": "#1e7a38",
        "failed": "#b3372f",
        "cancelled": "#95580f",
        "warn_bg": "#f8ecc9",
        "warn_text": "#7a5d00",
        "error_bg": "#f9dedc",
        "error_text": "#9c2b23",
        "info_bg": "#dcebf8",
        "info_text": "#0b5a8a",
    },
}

THEME_NAMES = {"dark": "深色 · 事件视界", "light": "浅色 · 星光"}
DEFAULT_THEME = "dark"


def palette(name: str) -> dict[str, str]:
    """Returns the color table of the specified theme; unknown themes fall back to the default."""
    return _PALETTES.get(name, _PALETTES[DEFAULT_THEME])


def status_color(theme: str, status: str) -> str:
    return palette(theme).get(status, palette(theme)["idle"])


def _qss(c: dict[str, str]) -> str:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    check_icon = (root / "desktop" / "resources" /
                  "checkbox-check.svg").as_posix()
    return f"""
QWidget {{
    background: {c['window']};
    color: {c['text']};
    font-size: 13px;
}}
QMainWindow::separator {{ background: {c['border_soft']}; }}

/* ---------- Input controls ---------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit,
QListWidget, QTableWidget, QTreeWidget {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {c['card']}, stop:0.45 {c['base']}, stop:1 {c['alt']});
    border: 1px solid {c['border_soft']};
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: {c['accent']};
    selection-color: {c['accent_text']};
}}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
    border: 1px solid {c['border']};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {c['accent']};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
QComboBox:disabled, QPlainTextEdit:disabled, QTextEdit:disabled {{
    background: {c['alt']};
    color: {c['text_dim']};
}}
QLabel[unit="true"] {{
    color: {c['text_dim']};
    background: transparent;
    padding-left: 2px;
}}
QWidget#parameterRow, QWidget#parameterField {{
    background: transparent;
}}
QComboBox::drop-down {{
    width: 27px;
    border: none;
    border-left: 1px solid {c['border_soft']};
    background: {c['alt']};
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
}}
QComboBox::down-arrow {{ image: none; width: 0; height: 0; }}
QComboBox QAbstractItemView {{
    background: {c['base']};
    border: 1px solid {c['border']};
    outline: none;
}}
QComboBox QAbstractItemView::item {{ padding: 4px 8px; }}
QComboBox QAbstractItemView::item:selected {{
    background: {c['accent_soft']};
    color: {c['text']};
}}

/* ---------- Two-column parameter cards ---------- */
QFrame#parameterCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {c['card']}, stop:1 {c['alt']});
    border: 1px solid {c['border_soft']};
    border-radius: 9px;
}}
QFrame#parameterCard:hover {{
    border-color: {c['border']};
}}
QLabel[parameterTitle="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #171b24, stop:0.55 #0d1017, stop:1 #07090e);
    border: 1px solid {c['accent_deep']};
    border-radius: 6px;
    color: #f7f9fc;
    font-family: "Cambria Math", "STIX Two Math", "Segoe UI Symbol";
    font-size: 16px;
    font-weight: 600;
    padding: 0 10px;
}}
QLabel[unitChip="true"] {{
    background: {c['base']};
    border: 1px solid {c['border_soft']};
    border-radius: 6px;
    color: {c['text_dim']};
    font-family: "Cambria Math", "STIX Two Math", "Segoe UI Symbol";
    padding: 5px 7px;
}}
QLabel[parameterHint="true"] {{
    background: transparent;
    color: {c['text_dim']};
    font-family: "Cambria Math", "Microsoft YaHei UI", "Segoe UI Symbol";
    font-size: 11px;
    padding: 0 2px;
}}
QFrame#parameterCard QSpinBox,
QFrame#parameterCard QDoubleSpinBox,
QFrame#parameterCard QComboBox,
QFrame#parameterCard QLineEdit {{
    min-height: 24px;
}}

/* ---------- Buttons ---------- */
QPushButton {{
    background: {c['alt']};
    border: 1px solid {c['border_soft']};
    border-radius: 6px;
    padding: 6px 14px;
}}
QPushButton:hover {{
    border-color: {c['accent']};
    background: {c['card']};
}}
QPushButton:pressed {{ background: {c['border_soft']}; }}
QPushButton:disabled {{
    color: {c['text_dim']};
    background: {c['alt']};
    border-color: {c['border_soft']};
}}
QPushButton[primary="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {c['accent']}, stop:1 {c['accent_deep']});
    color: {c['accent_text']};
    border: none;
    font-weight: 600;
    padding: 7px 18px;
}}
QPushButton[primary="true"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {c['accent_deep']}, stop:1 {c['accent']});
}}
QPushButton[primary="true"]:disabled {{
    background: {c['border_soft']};
    color: {c['text_dim']};
}}
QPushButton[danger="true"] {{
    background: {c['error_bg']};
    color: {c['error_text']};
    border: 1px solid {c['failed']};
}}

/* ---------- Left navigation ---------- */
QPushButton[nav="true"] {{
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 8px;
    color: {c['text_dim']};
    text-align: left;
    padding: 9px 12px 9px 10px;
}}
QPushButton[nav="true"]:hover {{
    background: {c['nav_hover']};
    color: {c['text']};
}}
QPushButton[nav="true"]:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {c['nav_selected']}, stop:1 transparent);
    border-left: 3px solid {c['accent']};
    color: {c['accent']};
    font-weight: 600;
}}
QPushButton[nav="true"]:checked:hover {{ color: {c['accent']}; }}

/* ---------- Task cards ---------- */
QPushButton[card="true"] {{
    background: {c['card']};
    border: 1px solid {c['border_soft']};
    border-radius: 10px;
    padding: 12px 16px;
    color: {c['text_dim']};
    text-align: left;
    font-weight: 600;
}}
QPushButton[card="true"]:hover {{
    border-color: {c['accent']};
    color: {c['text']};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {c['card']}, stop:1 {c['alt']});
}}
QPushButton[card="true"]:checked {{
    border: 1px solid {c['accent']};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {c['nav_selected']}, stop:1 {c['card']});
    color: {c['accent']};
}}

/* ---------- Groups and cards ---------- */
QGroupBox {{
    background: {c['card']};
    border: 1px solid {c['border_soft']};
    border-radius: 10px;
    margin-top: 14px;
    padding: 10px 10px 8px 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    top: 2px;
    padding: 0 6px;
    color: {c['text_dim']};
}}
QFrame#summaryBar {{
    background: {c['card']};
    border: 1px solid {c['border_soft']};
    border-radius: 10px;
}}
QFrame#quickActionBar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {c['card']}, stop:0.7 {c['base']}, stop:1 {c['alt']});
    border: 1px solid {c['border_soft']};
    border-radius: 10px;
}}
QLabel#quickContext {{
    background: {c['accent_soft']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    color: {c['accent']};
    font-weight: 600;
    padding: 5px 10px;
}}
QFrame#quickActionBar QPushButton[quickAction="true"] {{
    min-width: 92px;
}}
QFrame#glowDivider {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 transparent, stop:0.25 {c['accent']},
        stop:0.65 {c['accent2']}, stop:1 transparent);
}}
QLabel#brandTitle {{
    font-size: 17px;
    font-weight: 700;
    color: {c['text']};
}}
QLabel#brandSub {{
    color: {c['text_dim']};
    font-size: 11px;
}}

/* ---------- Progress and tables ---------- */
QProgressBar {{
    background: {c['alt']};
    border: 1px solid {c['border_soft']};
    border-radius: 6px;
    text-align: center;
    height: 14px;
    color: {c['text']};
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {c['accent2']}, stop:1 {c['accent']});
    border-radius: 5px;
}}
QHeaderView::section {{
    background: {c['alt']};
    border: none;
    border-bottom: 1px solid {c['border_soft']};
    padding: 5px 8px;
}}
QTableWidget::item:selected {{
    background: {c['accent_soft']};
    color: {c['text']};
}}

/* ---------- Scroll bars ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background: {c['border']};
    min-height: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{ background: {c['accent']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{
    background: {c['border']};
    min-width: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{ background: {c['accent']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ---------- Other widgets ---------- */
QTabWidget::pane {{ border: 1px solid {c['border_soft']}; }}
QTabBar::tab {{
    background: {c['alt']};
    border: 1px solid {c['border_soft']};
    padding: 6px 14px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{ background: {c['card']}; color: {c['accent']}; }}
QToolTip {{
    background: {c['card']};
    color: {c['text']};
    border: 1px solid {c['border']};
    padding: 4px 6px;
}}
QCheckBox, QRadioButton {{ spacing: 7px; }}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    background: {c['base']};
    border: 2px solid {c['border']};
    border-radius: 3px;
}}
QCheckBox::indicator:hover {{ border-color: {c['accent']}; }}
QCheckBox::indicator:checked {{
    background: {c['accent']};
    border-color: {c['accent_deep']};
    image: url("{check_icon}");
}}
QCheckBox::indicator:checked:hover {{ background: {c['accent_deep']}; }}
QCheckBox::indicator:disabled {{
    background: {c['alt']};
    border-color: {c['border_soft']};
}}
QCheckBox:disabled, QRadioButton:disabled {{ color: {c['text_dim']}; }}
QLabel[matchStatus="true"] {{
    background: {c['base']};
    border: 1px solid {c['border_soft']};
    border-radius: 6px;
    color: {c['text']};
    padding: 6px 8px;
}}
QLabel[dim="true"] {{
    color: {c['text_dim']};
    background: transparent;
    font-family: "Cambria Math", "Microsoft YaHei UI", "Segoe UI Symbol";
}}
QToolButton[sectionToggle="true"] {{
    border: none;
    font-weight: 600;
    color: {c['text_dim']};
    padding: 4px 2px;
}}
QToolButton[sectionToggle="true"]:hover {{ color: {c['accent']}; }}
"""


def apply_theme(application, name: str) -> None:
    """Applies the specified theme to the QApplication (stylesheet + base palette)."""
    from PySide6.QtGui import QFont

    colors = palette(name)
    application.setStyle("fusion")
    # Explicitly specify Chinese font families to ensure clear and consistent rendering at each zoom level
    application.setFont(QFont("Microsoft YaHei UI", 9))
    qt_palette = QPalette()
    qt_palette.setColor(QPalette.Window, QColor(colors["window"]))
    qt_palette.setColor(QPalette.WindowText, QColor(colors["text"]))
    qt_palette.setColor(QPalette.Base, QColor(colors["base"]))
    qt_palette.setColor(QPalette.AlternateBase, QColor(colors["alt"]))
    qt_palette.setColor(QPalette.Text, QColor(colors["text"]))
    qt_palette.setColor(QPalette.Button, QColor(colors["alt"]))
    qt_palette.setColor(QPalette.ButtonText, QColor(colors["text"]))
    qt_palette.setColor(QPalette.Highlight, QColor(colors["accent"]))
    qt_palette.setColor(QPalette.HighlightedText, QColor(colors["accent_text"]))
    qt_palette.setColor(
        QPalette.Disabled, QPalette.Text, QColor(colors["text_dim"]))
    qt_palette.setColor(
        QPalette.Disabled, QPalette.ButtonText, QColor(colors["text_dim"]))
    application.setPalette(qt_palette)
    application.setStyleSheet(_qss(colors))
