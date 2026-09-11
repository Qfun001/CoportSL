"""QPainter vector icon factory.

All icons are drawn with rounded lines on a 24×24 logical grid, and are colored according to the current theme at runtime
Generate QPixmap/QIcon: naturally supports high-resolution screen scaling, and does not need to import resource files
PyInstaller data directory."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QPixmap,
    QRadialGradient,
)

NAV_ICON_NAMES = (
    "database", "flux_wave", "black_hole", "bar_chart",
    "grid", "gauge", "history", "gear",
)

TASK_ICON_NAMES = ("analysis", "fast", "slow", "target")


def _pen(color: QColor, width: float = 1.7) -> QPen:
    pen = QPen(color)
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _draw_database(p: QPainter) -> None:
    p.drawEllipse(QRectF(4.0, 3.0, 16.0, 6.0))
    p.drawLine(QPointF(4.0, 6.0), QPointF(4.0, 18.0))
    p.drawLine(QPointF(20.0, 6.0), QPointF(20.0, 18.0))
    path = QPainterPath()
    path.moveTo(4.0, 18.0)
    path.arcTo(QRectF(4.0, 12.0, 16.0, 12.0), 180.0, 180.0)
    p.drawPath(path)
    path2 = QPainterPath()
    path2.moveTo(4.0, 12.0)
    path2.arcTo(QRectF(4.0, 6.0, 16.0, 12.0), 180.0, 180.0)
    p.drawPath(path2)


def _draw_flux_wave(p: QPainter) -> None:
    path = QPainterPath(QPointF(2.0, 12.0))
    path.cubicTo(QPointF(5.0, 4.0), QPointF(8.0, 4.0), QPointF(10.5, 12.0))
    path.cubicTo(QPointF(13.0, 20.0), QPointF(16.0, 20.0), QPointF(18.5, 12.0))
    path.cubicTo(QPointF(19.5, 9.0), QPointF(20.5, 8.5), QPointF(22.0, 8.5))
    p.drawPath(path)


def _draw_black_hole(p: QPainter, color: QColor) -> None:
    # Tilted accretion ring + solid shadow, a tribute to black hole photos
    p.save()
    p.translate(12.0, 12.0)
    p.rotate(72.0)
    p.drawEllipse(QRectF(-9.5, -3.6, 19.0, 7.2))
    p.restore()
    p.setBrush(color)
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(12.0, 12.0), 3.6, 3.6)


def _draw_bar_chart(p: QPainter) -> None:
    p.drawLine(QPointF(3.5, 4.0), QPointF(3.5, 20.5))
    p.drawLine(QPointF(3.5, 20.5), QPointF(21.0, 20.5))
    for x, top in ((7.5, 13.0), (12.5, 8.0), (17.5, 11.0)):
        p.drawLine(QPointF(x, 20.5), QPointF(x, top))


def _draw_grid(p: QPainter) -> None:
    path = QPainterPath()
    path.addRoundedRect(QRectF(3.5, 3.5, 17.0, 17.0), 2.0, 2.0)
    p.drawPath(path)
    for pos in (9.2, 14.8):
        p.drawLine(QPointF(pos, 3.5), QPointF(pos, 20.5))
        p.drawLine(QPointF(3.5, pos), QPointF(20.5, pos))


def _draw_gauge(p: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(3.5, 16.5)
    path.arcTo(QRectF(3.5, 5.0, 17.0, 17.0), 180.0, 180.0)
    p.drawPath(path)
    p.drawLine(QPointF(12.0, 13.5), QPointF(16.8, 8.2))
    p.drawLine(QPointF(5.0, 20.5), QPointF(19.0, 20.5))


def _draw_history(p: QPainter) -> None:
    p.drawEllipse(QRectF(4.0, 4.0, 16.0, 16.0))
    path = QPainterPath(QPointF(12.0, 7.5))
    path.lineTo(QPointF(12.0, 12.0))
    path.lineTo(QPointF(15.8, 14.2))
    p.drawPath(path)


def _draw_gear(p: QPainter) -> None:
    p.drawEllipse(QRectF(9.2, 9.2, 5.6, 5.6))
    for index in range(8):
        angle = math.radians(index * 45.0)
        inner = QPointF(12.0 + 6.4 * math.cos(angle),
                        12.0 + 6.4 * math.sin(angle))
        outer = QPointF(12.0 + 8.8 * math.cos(angle),
                        12.0 + 8.8 * math.sin(angle))
        p.drawLine(inner, outer)


def _draw_analysis(p: QPainter) -> None:
    p.drawEllipse(QRectF(3.5, 3.5, 11.5, 11.5))
    p.drawLine(QPointF(13.2, 13.2), QPointF(20.5, 20.5))
    delay = QPainterPath(QPointF(5.5, 11.8))
    delay.cubicTo(
        QPointF(7.0, 7.0), QPointF(9.0, 13.5), QPointF(13.0, 7.0))
    p.drawPath(delay)


def _draw_fast(p: QPainter) -> None:
    path = QPainterPath(QPointF(13.5, 2.5))
    path.lineTo(QPointF(6.5, 13.0))
    path.lineTo(QPointF(11.5, 13.0))
    path.lineTo(QPointF(10.0, 21.5))
    path.lineTo(QPointF(17.5, 10.5))
    path.lineTo(QPointF(12.5, 10.5))
    path.closeSubpath()
    p.drawPath(path)


def _draw_slow(p: QPainter) -> None:
    p.drawEllipse(QRectF(3.0, 8.0, 18.0, 8.0))
    p.drawEllipse(QRectF(7.0, 10.0, 10.0, 4.0))


def _draw_target(p: QPainter) -> None:
    p.drawEllipse(QRectF(4.5, 4.5, 15.0, 15.0))
    p.drawEllipse(QRectF(9.0, 9.0, 6.0, 6.0))
    p.drawLine(QPointF(12.0, 2.0), QPointF(12.0, 5.5))
    p.drawLine(QPointF(12.0, 18.5), QPointF(12.0, 22.0))
    p.drawLine(QPointF(2.0, 12.0), QPointF(5.5, 12.0))
    p.drawLine(QPointF(18.5, 12.0), QPointF(22.0, 12.0))


def _draw_play(p: QPainter) -> None:
    path = QPainterPath(QPointF(7.5, 4.5))
    path.lineTo(QPointF(19.0, 12.0))
    path.lineTo(QPointF(7.5, 19.5))
    path.closeSubpath()
    p.drawPath(path)


def _draw_resume(p: QPainter) -> None:
    arc = QPainterPath(QPointF(5.0, 15.5))
    arc.arcTo(QRectF(4.0, 4.0, 16.0, 16.0), 205.0, 245.0)
    p.drawPath(arc)
    arrow = QPainterPath(QPointF(3.8, 10.0))
    arrow.lineTo(QPointF(4.8, 16.0))
    arrow.lineTo(QPointF(10.2, 13.2))
    p.drawPath(arrow)
    play = QPainterPath(QPointF(10.2, 8.3))
    play.lineTo(QPointF(16.2, 12.0))
    play.lineTo(QPointF(10.2, 15.7))
    play.closeSubpath()
    p.drawPath(play)


def _draw_folder(p: QPainter) -> None:
    path = QPainterPath(QPointF(3.0, 7.0))
    path.lineTo(QPointF(9.0, 7.0))
    path.lineTo(QPointF(11.0, 9.5))
    path.lineTo(QPointF(21.0, 9.5))
    path.lineTo(QPointF(19.5, 19.0))
    path.lineTo(QPointF(4.5, 19.0))
    path.closeSubpath()
    p.drawPath(path)


def _draw_check(p: QPainter) -> None:
    p.drawLine(QPointF(4.0, 12.5), QPointF(9.5, 18.0))
    p.drawLine(QPointF(9.5, 18.0), QPointF(20.5, 6.5))


_DRAWERS = {
    "database": _draw_database,
    "flux_wave": _draw_flux_wave,
    "bar_chart": _draw_bar_chart,
    "grid": _draw_grid,
    "gauge": _draw_gauge,
    "history": _draw_history,
    "gear": _draw_gear,
    "analysis": _draw_analysis,
    "fast": _draw_fast,
    "slow": _draw_slow,
    "target": _draw_target,
    "play": _draw_play,
    "resume": _draw_resume,
    "folder": _draw_folder,
    "check": _draw_check,
}


def paint_icon(name: str, color: str | QColor, size: int = 24,
               dpr: float = 1.0) -> QPixmap:
    """Draw the named icon as a QPixmap (enlarged by dpr and devicePixelRatio set)."""
    qcolor = QColor(color) if isinstance(color, str) else color
    pixmap = QPixmap(int(size * dpr), int(size * dpr))
    pixmap.fill(Qt.transparent)
    pixmap.setDevicePixelRatio(dpr)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.scale(size / 24.0, size / 24.0)
    painter.setPen(_pen(qcolor))
    painter.setBrush(Qt.NoBrush)
    if name == "black_hole":
        _draw_black_hole(painter, qcolor)
    else:
        try:
            _DRAWERS[name](painter)
        except KeyError as exc:
            painter.end()
            raise ValueError(f"未知图标：{name}") from exc
    painter.end()
    return pixmap


def icon(name: str, color: str | QColor, size: int = 24,
         dpr: float = 1.0) -> QIcon:
    return QIcon(paint_icon(name, color, size, dpr))


def brand_pixmap(size: int = 64, dpr: float = 1.0) -> QPixmap:
    """Brand logo: accretion disk vortex + photon ring + bright spot black hole rendering."""
    from PySide6.QtGui import QConicalGradient

    pixmap = QPixmap(int(size * dpr), int(size * dpr))
    pixmap.fill(Qt.transparent)
    pixmap.setDevicePixelRatio(dpr)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    center = size / 2.0

    # 1) Outer glow
    glow = QRadialGradient(center, center, center)
    glow.setColorAt(0.0, QColor(245, 165, 36, 0))
    glow.setColorAt(0.55, QColor(245, 165, 36, 26))
    glow.setColorAt(0.80, QColor(245, 165, 36, 90))
    glow.setColorAt(1.0, QColor(245, 165, 36, 0))
    painter.setBrush(glow)
    painter.setPen(Qt.NoPen)
    painter.drawRect(0, 0, size, size)

    # 2) Accretion disk: inclined annulus, tapered gradient to form vortex light and dark
    disk_outer = QRectF(center - size * 0.44, center - size * 0.17,
                        size * 0.88, size * 0.34)
    disk_inner = QRectF(center - size * 0.26, center - size * 0.10,
                        size * 0.52, size * 0.20)
    painter.save()
    painter.translate(center, center)
    painter.rotate(72.0)
    painter.translate(-center, -center)
    ring = QPainterPath()
    ring.addEllipse(disk_outer)
    hole = QPainterPath()
    hole.addEllipse(disk_inner)
    ring = ring.subtracted(hole)
    swirl = QConicalGradient(center, center, 130.0)
    swirl.setColorAt(0.00, QColor(255, 226, 160))
    swirl.setColorAt(0.25, QColor(245, 165, 36))
    swirl.setColorAt(0.55, QColor(150, 72, 0))
    swirl.setColorAt(0.78, QColor(217, 126, 6))
    swirl.setColorAt(1.00, QColor(255, 226, 160))
    painter.setBrush(swirl)
    painter.drawPath(ring)
    painter.restore()

    # 3) Black hole shadow: pure black core, with slightly absorbed background color at the edges
    shadow = QRadialGradient(center, center, size * 0.30)
    shadow.setColorAt(0.0, QColor(0, 0, 0))
    shadow.setColorAt(0.85, QColor(2, 3, 6))
    shadow.setColorAt(1.0, QColor(8, 10, 16))
    painter.setBrush(shadow)
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(QPointF(center, center), size * 0.285, size * 0.285)

    # 3b) The front edge of the accretion disk: The round-headed thick arc passes under the shadow, forming a deep
    painter.save()
    painter.translate(center, center)
    painter.rotate(72.0)
    painter.translate(-center, -center)
    mid = QRectF(center - size * 0.35, center - size * 0.135,
                 size * 0.70, size * 0.27)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(_pen(QColor(217, 126, 6, 220), size * 0.105))
    painter.drawArc(mid, -85 * 16, 140 * 16)
    painter.setPen(_pen(QColor(255, 214, 130, 235), size * 0.05))
    painter.drawArc(mid, -80 * 16, 130 * 16)
    painter.restore()

    # 4) Photon ring: a thin bright ring that fits the shadow
    painter.setBrush(Qt.NoBrush)
    painter.setPen(_pen(QColor(255, 227, 166), max(1.0, size / 72.0)))
    painter.drawEllipse(QPointF(center, center), size * 0.295, size * 0.295)
    painter.end()
    return pixmap
