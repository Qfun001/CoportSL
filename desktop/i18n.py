"""Runtime localization for the desktop interface.

The existing desktop UI uses Simplified Chinese source strings. This module
keeps those strings as stable translation keys, renders English by default,
and remembers each widget's source text so the interface can switch languages
without rebuilding widgets or losing form values.
"""

from __future__ import annotations

from typing import Any
import weakref

from .i18n_catalog import ZH_TO_EN
ZH_TO_EN.update({
    "主题": "Theme",
    "设置": "Settings",
    "正式计算": "Imaging",
    "运行记录": "Run History",
    "性能基准": "Benchmark",
    "无运行任务": "No Task Running",
    "空闲": "Idle",
    "校验中": "Validating",
    "排队": "Queued",
    "运行中": "Running",
    "正在取消": "Cancelling",
    "成功": "Succeeded",
    "失败": "Failed",
    "已取消": "Cancelled",
    "界面语言": "Language",
    "浅色 · 星光": "Light · Starlight",
    "结果：—": "Output: —",
    "结果：": "Output: ",
    "观者时刻": "Observer Time",
    "真实源参数": "Physical Source Parameters",
    "模拟吸积率": "Simulation Accretion Rate",
    "输出图件": "Output Figures",
    "区域误差": "Region Error",
    "快光": "Fast Light",
    "慢光": "Slow Light",
    "前置分析": "Pre-analysis",
    "真实源": "Physical Source",
    "成像屏": "Image Plane",
    "光线积分": "Ray Integration",
    "空间分区": "Spatial Partition",
    "电子模型": "Electron Model",
    "电子温度模型": "Electron Temperature Model",
    "观者位置": "Observer Position",
    "观者半径": "Observer Radius",
    "观者极角": "Observer Polar Angle",
    "观者方位角": "Observer Azimuth",
    "物理吸积率": "Physical Accretion Rate",
    "积分观测量": "Integrated Observables",
    "生成积分观测量及曲线": "Generate Integrated Observables and Plots",
    "任务专属科研图件": "Task-specific Scientific Figures",
    "生成任务专属科研图件": "Generate Task-specific Scientific Figures",
    "运行勾选任务": "Run Selected Tasks",
    "勾选任务": "Selected Tasks",
    "图件格式": "Figure Formats",
    "已生成图件": "Generated Figures",
    "数据：": "Data: ",
    "网格：": "Grid: ",
    "帧：": "Frames: ",
    "阶段：": "Stage: ",
    "就绪": "Ready",
    "当前页面": "Current Page",
    "正式图像的单边像素数。": "Number of pixels along one side of the production image.",
    "源距离": "Source Distance",
    "结果根目录": "Results Root",
    "打开结果根目录": "Open Results Root",
    "深色 · 事件视界": "Dark · Event Horizon",
    "已自动恢复上次使用的": "Restored the previous ",
    "数据路径和参数": "data paths and parameters",
    "数据路径": "data paths",
    "推荐计算流程": "Recommended Workflow",
    "行": "lines",
    "项": "items",
    "历史作业保留上限": "Maximum Run History Entries",
    "任务抽屉日志容量": "Task Drawer Log Capacity",
    "设置、作业与日志目录：": "Settings, jobs, and logs: ",
    "\n数据路径和各页面参数会自动恢复上次有效值；"
    "损坏时自动备份为 .broken.json 并恢复默认值。":
        "\nThe last valid data paths and page parameters are restored automatically. "
        "A damaged settings file is backed up as .broken.json before defaults are restored.",
    "\n当前使用软件同级的便携数据目录。":
        "\nThe portable data directory beside the application is currently in use.",
    "\n偏振广义相对论辐射转移桌面软件\n\n"
    "许可证：GNU Affero General Public License v3.0\n"
    "主要组件：Qt/PySide6、PyInstaller、NumPy、SciPy、"
    "Matplotlib、OpenCV、nlohmann/json\n"
    "源码：对外发布时请在同一发布页提供本版本对应源码。":
        "\nPolarized General Relativistic Radiative Transfer Desktop Application\n\n"
        "License: GNU Affero General Public License v3.0\n"
        "Core components: Qt/PySide6, PyInstaller, NumPy, SciPy, Matplotlib, "
        "OpenCV, and nlohmann/json\n"
        "Source: publish the corresponding source code on the same release page.",
    "① 数据与辐射模型准备 → ② Flux 定标 → ③ 慢光前置分析 → "
    "④ 正式快光/慢光计算 → ⑤ 结果后处理":
        "① Prepare data and radiation model → ② Calibrate flux → "
        "③ Run slow-light pre-analysis → ④ Run production fast-/slow-light imaging → "
        "⑤ Post-process results",
})

DEFAULT_LANGUAGE = "en"
LANGUAGES = {"en": "English", "zh_CN": "简体中文"}

_language = DEFAULT_LANGUAGE
_filter: Any = None
_qt_translators: list[Any] = []
_sources: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_ordered_catalog = sorted(ZH_TO_EN.items(), key=lambda item: len(item[0]), reverse=True)


def set_language(language: str) -> None:
    """Select a supported UI language."""
    global _language
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported interface language: {language}")
    _language = language
    _apply_qt_translations()


def _apply_qt_translations() -> None:
    """Load Qt's standard-dialog translations when a Qt app is available."""
    global _qt_translators
    try:
        from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTranslator
    except ImportError:
        return
    application = QCoreApplication.instance()
    if application is None:
        return
    for translator in _qt_translators:
        application.removeTranslator(translator)
    _qt_translators = []
    if _language != "zh_CN":
        return
    directory = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    for catalog in ("qtbase_zh_CN", "qt_zh_CN"):
        translator = QTranslator(application)
        if translator.load(catalog, directory):
            application.installTranslator(translator)
            _qt_translators.append(translator)


def current_language() -> str:
    """Return the active UI language key."""
    return _language


def tr(source: str) -> str:
    """Translate a source string while preserving embedded dynamic values."""
    if _language == "zh_CN" or not source:
        return source
    exact = ZH_TO_EN.get(source)
    if exact is not None:
        return exact
    translated = source
    for chinese, english in _ordered_catalog:
        if chinese in translated:
            translated = translated.replace(chinese, english)
    return translated


def _render(owner: object, key: str, current: str) -> str:
    state = _sources.setdefault(owner, {})
    previous = state.get(key)
    if previous is None or current != previous[1]:
        source = current
    else:
        source = previous[0]
    rendered = tr(source)
    state[key] = (source, rendered)
    return rendered


def _set_text(owner: object, key: str, getter, setter) -> None:
    current = getter()
    rendered = _render(owner, key, current)
    if rendered != current:
        setter(rendered)


def translate_object(obj: object) -> None:
    """Translate supported text properties on one Qt object."""
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import (
        QAbstractButton,
        QComboBox,
        QGroupBox,
        QLabel,
        QLineEdit,
        QMenu,
        QProgressBar,
        QTabWidget,
        QTableWidget,
        QToolBox,
        QTreeWidget,
        QWidget,
    )

    if isinstance(obj, (QLabel, QAbstractButton, QAction)):
        _set_text(obj, "text", obj.text, obj.setText)
    if isinstance(obj, QGroupBox):
        _set_text(obj, "title", obj.title, obj.setTitle)
    if isinstance(obj, QMenu):
        _set_text(obj, "menu-title", obj.title, obj.setTitle)
    if isinstance(obj, QLineEdit):
        _set_text(
            obj, "placeholder", obj.placeholderText, obj.setPlaceholderText)
    if isinstance(obj, QProgressBar):
        _set_text(obj, "format", obj.format, obj.setFormat)
    if isinstance(obj, QWidget):
        _set_text(obj, "tooltip", obj.toolTip, obj.setToolTip)
        _set_text(obj, "status-tip", obj.statusTip, obj.setStatusTip)
        if obj.windowTitle():
            _set_text(obj, "window-title", obj.windowTitle, obj.setWindowTitle)
    if isinstance(obj, QComboBox):
        for index in range(obj.count()):
            current = obj.itemText(index)
            rendered = _render(obj, f"combo:{index}", current)
            if rendered != current:
                obj.setItemText(index, rendered)
    if isinstance(obj, QTabWidget):
        for index in range(obj.count()):
            current = obj.tabText(index)
            rendered = _render(obj, f"tab:{index}", current)
            if rendered != current:
                obj.setTabText(index, rendered)
    if isinstance(obj, QToolBox):
        for index in range(obj.count()):
            current = obj.itemText(index)
            rendered = _render(obj, f"toolbox:{index}", current)
            if rendered != current:
                obj.setItemText(index, rendered)
    if isinstance(obj, QTableWidget):
        for column in range(obj.columnCount()):
            item = obj.horizontalHeaderItem(column)
            if item is not None:
                current = item.text()
                rendered = _render(obj, f"header:{column}", current)
                if rendered != current:
                    item.setText(rendered)
        for row in range(obj.rowCount()):
            for column in range(obj.columnCount()):
                item = obj.item(row, column)
                if item is not None:
                    current = item.text()
                    rendered = _render(obj, f"cell:{row}:{column}", current)
                    if rendered != current:
                        item.setText(rendered)
    if isinstance(obj, QTreeWidget):
        header = obj.headerItem()
        for column in range(obj.columnCount()):
            current = header.text(column)
            rendered = _render(obj, f"tree-header:{column}", current)
            if rendered != current:
                header.setText(column, rendered)


def retranslate_widget_tree(root: object) -> None:
    """Immediately refresh all supported text beneath a Qt object."""
    from PySide6.QtCore import QObject

    translate_object(root)
    if isinstance(root, QObject):
        for child in root.findChildren(QObject):
            translate_object(child)


def install_live_translation(application: object) -> None:
    """Translate newly shown and subsequently repainted Qt widgets."""
    global _filter
    if _filter is not None:
        return
    from PySide6.QtCore import QEvent, QObject

    class TranslationFilter(QObject):
        def __init__(self) -> None:
            super().__init__()
            self._active: set[int] = set()

        def eventFilter(self, watched, event) -> bool:  # noqa: N802
            if event.type() not in {QEvent.Show, QEvent.Paint}:
                return False
            identity = id(watched)
            if identity in self._active:
                return False
            self._active.add(identity)
            try:
                translate_object(watched)
            finally:
                self._active.discard(identity)
            return False

    _filter = TranslationFilter()
    application.installEventFilter(_filter)
