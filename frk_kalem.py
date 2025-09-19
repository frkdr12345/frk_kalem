import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QColorDialog, QSlider, QLabel
)
from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtGui import QPainter, QPen, QColor, QMouseEvent, QGuiApplication, QBrush



class DrawingOverlay(QWidget):
    def __init__(self, panel):
        super().__init__()
        self.panel = panel
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.showFullScreen()

        self.drawing = False
        self.brush_color = QColor("red")
        self.brush_size = 10
        self.eraser_mode = False
        self.points = []

        self.active = False
        self.background = None
        self.eraser_rect = None  

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.background:
            painter.drawPixmap(0, 0, self.background)

        for point, color, size, eraser in self.points:
            pen = QPen(color, size)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            if eraser:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            else:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            for i in range(1, len(point)):
                painter.drawLine(point[i - 1], point[i])

        
        if self.eraser_mode and self.eraser_rect:
            painter.setBrush(QBrush(QColor(255, 255, 255, 50)))
            painter.setPen(Qt.PenStyle.NoPen)
            x, y, w, h = self.eraser_rect
            painter.drawRect(x - w//2, y - h//2, w, h)

    def mousePressEvent(self, event: QMouseEvent):
        if not self.active:
            return
        if self.panel.geometry().contains(event.globalPosition().toPoint()):
            event.ignore()
            return

        self.panel.raise_()
        self.panel.activateWindow()

        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            color = self.brush_color
            self.points.append(([], color, self.brush_size, self.eraser_mode))
            self.points[-1][0].append(event.pos())

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.active or not self.drawing:
            return
        if self.panel.geometry().contains(event.globalPosition().toPoint()):
            event.ignore()
            return

        self.panel.raise_()
        self.panel.activateWindow()

        pos = event.pos()
        if self.eraser_mode:
            self.eraser_rect = (pos.x(), pos.y(), self.brush_size, self.brush_size)
            self.erase_in_rect()
        else:
            self.points[-1][0].append(pos)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if not self.active:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            self.eraser_rect = None
            self.update()

    def clear(self):
        self.points = []
        self.update()

    def capture_screen(self):
        self.panel.hide()
        QApplication.processEvents()
        screen = QGuiApplication.primaryScreen()
        if screen:
            self.background = screen.grabWindow(0)
            self.update()
            self.show()
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()

    def erase_in_rect(self):
        if not self.eraser_rect:
            return
        rx, ry, rw, rh = self.eraser_rect
        new_points = []
        for stroke in self.points:
            pts, color, size, eraser = stroke
            if eraser:
                new_points.append(stroke)
            else:
                pts = [p for p in pts if not (rx - rw//2 <= p.x() <= rx + rw//2 and ry - rh//2 <= p.y() <= ry + rh//2)]
                if pts:
                    new_points.append((pts, color, size, eraser))
        self.points = new_points


class ToolPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.overlay = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(100, 100, 160, 420)

        self.dragPos = None
        self.dragging = False
        self.mouse_pressed_on_panel = False

        layout = QVBoxLayout()
        layout.setSpacing(8)

        btn_start = QPushButton("Aç")
        btn_start.clicked.connect(self.start_drawing)
        btn_stop = QPushButton("Kapat")
        btn_stop.clicked.connect(self.stop_drawing)
        btn_pen = QPushButton("Kalem")
        btn_pen.clicked.connect(self.set_pen)
        btn_eraser = QPushButton("Silgi")
        btn_eraser.clicked.connect(self.set_eraser)
        btn_color = QPushButton("Renk")
        btn_color.clicked.connect(self.choose_color)
        btn_clear = QPushButton("Sil")
        btn_clear.clicked.connect(self.clear_overlay)
        lbl_slider = QLabel("Boyut:")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 50)
        self.slider.setValue(10)
        self.slider.valueChanged.connect(self.change_brush_size)
        btn_exit = QPushButton("Çıkış")
        btn_exit.clicked.connect(QApplication.instance().quit)

        widgets = [btn_start, btn_stop, btn_pen, btn_eraser, btn_color, lbl_slider, self.slider, btn_clear, btn_exit]

        for w in widgets:
            if isinstance(w, QPushButton):
                w.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255,255,255,255);
                        border: none;
                        border-radius: 10px;
                        padding: 6px;
                    }
                    QPushButton:hover {
                        background-color: rgba(255,255,255,230);
                    }
                """)
            layout.addWidget(w)

        layout.addStretch()
        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(51, 51, 51, 227);
                border-radius: 15px;
            }
        """)
        self.show()
        self.raise_()

        for child in self.findChildren(QWidget):
            child.installEventFilter(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragPos = event.globalPosition()
            self.mouse_pressed_on_panel = True
            self.dragging = False

    def mouseMoveEvent(self, event):
        if self.dragPos and self.mouse_pressed_on_panel:
            delta = event.globalPosition() - self.dragPos
            if delta.manhattanLength() > 2:
                self.dragging = True
            self.move(self.x() + int(delta.x()), self.y() + int(delta.y()))
            self.dragPos = event.globalPosition()

    def mouseReleaseEvent(self, event):
        self.dragPos = None
        self.mouse_pressed_on_panel = False
        self.dragging = False

    def eventFilter(self, obj: QObject, event: QEvent):
        if isinstance(obj, (QSlider, QLabel)):
            return super().eventFilter(obj, event)
        if self.dragging and event.type() == QEvent.Type.MouseButtonPress:
            return True
        return super().eventFilter(obj, event)

    def start_drawing(self):
        if self.overlay:
            self.overlay.capture_screen()
            self.overlay.active = True
            self.overlay.show()
            self.raise_()
            self.activateWindow()

    def stop_drawing(self):
        if self.overlay:
            self.overlay.active = False
            self.overlay.clear()
            self.overlay.background = None
            self.overlay.hide()

    def set_pen(self):
        if self.overlay:
            self.overlay.eraser_mode = False

    def set_eraser(self):
        if self.overlay:
            self.overlay.eraser_mode = True

    def choose_color(self):
        if self.overlay:
            color_dialog = QColorDialog(self)
            color_dialog.setWindowFlags(
                color_dialog.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )
            if color_dialog.exec() == QColorDialog.DialogCode.Accepted:
                color = color_dialog.selectedColor()
                if color.isValid():
                    self.overlay.brush_color = color
                    self.overlay.eraser_mode = False

    def change_brush_size(self, value):
        if self.overlay:
            self.overlay.brush_size = value

    def clear_overlay(self):
        if self.overlay:
            self.overlay.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = ToolPanel()
    overlay = DrawingOverlay(panel)
    panel.overlay = overlay
    overlay.hide()
    panel.raise_()
    panel.activateWindow()
    sys.exit(app.exec())
