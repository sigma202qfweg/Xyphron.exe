import sys
import random
import ctypes
import pyautogui
import pygame
from PyQt6 import QtWidgets, QtGui, QtCore
from PIL import ImageFilter, ImageQt

class PrankMalwareOverlay(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # Make the window borderless, always on top, and show in taskbar
        self.setWindowFlags(
            QtCore.Qt.WindowType.Window |           # shows in taskbar
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        # Get screen resolution
        screen = QtWidgets.QApplication.primaryScreen()
        self.screen_width = screen.size().width()
        self.screen_height = screen.size().height()
        self.setGeometry(0, 0, self.screen_width, self.screen_height)

        # Store screenshot and effects data
        self.screenshot_pixmap = None
        self.should_invert_colors = False
        self.layers = []
        self.boxes = []
        self.particles = []
        self.cursor_clones = []

        # Phases setup
        self.current_phase = 1
        self.phase_start_time = QtCore.QTime.currentTime()

        # Screenshot update timer (10 FPS)
        self.screenshot_timer = QtCore.QTimer()
        self.screenshot_timer.timeout.connect(self.update_screenshot)
        self.screenshot_timer.start(100)

        # Repaint timer (~60 FPS)
        self.repaint_timer = QtCore.QTimer()
        self.repaint_timer.timeout.connect(self.update)
        self.repaint_timer.start(16)

    # ------------------------
    # SCREENSHOT UPDATE
    # ------------------------
    def update_screenshot(self):
        screenshot_pillow = pyautogui.screenshot()

        # Apply blur only in phase 2
        if self.current_phase == 2:
            screenshot_pillow = screenshot_pillow.filter(ImageFilter.GaussianBlur(radius=5))

        # Convert to QImage
        qimage = ImageQt.ImageQt(screenshot_pillow)

        # Invert colors in some phases
        if self.current_phase in [2, 3, 4, 7]:
            if self.should_invert_colors:
                try:
                    qimage.invertPixels()
                except Exception:
                    pass
            self.should_invert_colors = not self.should_invert_colors

        # Convert to pixmap (fit to screen size)
        self.screenshot_pixmap = QtGui.QPixmap.fromImage(qimage).scaled(
            self.screen_width,
            self.screen_height
        )

    # ------------------------
    # PHASE CONTROL
    # ------------------------
    def next_phase(self):
        self.current_phase += 1
        if self.current_phase > 7:  # loop back after phase 7
            self.current_phase = 1
        self.phase_start_time = QtCore.QTime.currentTime()

    # ------------------------
    # KEY PRESS HANDLER
    # ------------------------
    def keyPressEvent(self, event):
        # Press F to close app
        if event.key() == QtCore.Qt.Key.Key_F:
            pygame.mixer.music.stop()
            QtWidgets.QApplication.quit()

    # ------------------------
    # MAIN DRAWING LOOP
    # ------------------------
    def paintEvent(self, event):
        if not self.screenshot_pixmap:
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)

        # Time elapsed in current phase
        elapsed_time = self.phase_start_time.msecsTo(QtCore.QTime.currentTime())

        # Switch phase every 10 seconds
        if elapsed_time > 10000:
            self.next_phase()

        # --------------------
        # PHASE 1: slow zoom + duplicate
        # --------------------
        if self.current_phase == 1:
            scale_factor = 1.0 - min(0.9, elapsed_time / 100000.0)
            scaled_pixmap = self.screenshot_pixmap.scaled(
                int(self.screen_width * scale_factor),
                int(self.screen_height * scale_factor),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio
            )
            painter.drawPixmap(
                (self.screen_width - scaled_pixmap.width()) // 2,
                (self.screen_height - scaled_pixmap.height()) // 2,
                scaled_pixmap
            )
            if random.random() < 0.01:
                self.layers.append(scaled_pixmap)
            for layer in self.layers:
                painter.drawPixmap(random.randint(-50, 50), random.randint(-50, 50), layer)

        # --------------------
        # PHASE 2: blurred screenshot + boxes
        # --------------------
        elif self.current_phase == 2:
            painter.drawPixmap(0, 0, self.screenshot_pixmap)
            if random.random() < 0.02:
                self.boxes.append({
                    "x": random.randint(0, max(0, self.screen_width - 100)),
                    "y": random.randint(0, max(0, self.screen_height - 100)),
                    "size": 50,
                    "grow": True
                })
            for box in self.boxes:
                color = QtGui.QColor(0, 0, 0) if random.random() < 0.5 else QtGui.QColor(255, 255, 255)
                painter.fillRect(box["x"], box["y"], box["size"], box["size"], color)
                if box["grow"]:
                    box["size"] += 5
                    if box["size"] > 200:
                        box["grow"] = False
                else:
                    box["size"] -= 5
                    if box["size"] < 20:
                        box["grow"] = True

        # --------------------
        # PHASE 3: zoom + jitter
        # --------------------
        elif self.current_phase == 3:
            scale_factor = 1.0 + 0.5 * random.random()
            scaled_pixmap = self.screenshot_pixmap.scaled(
                int(self.screen_width * scale_factor),
                int(self.screen_height * scale_factor),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio
            )
            painter.drawPixmap(random.randint(-200, 200), random.randint(-200, 200), scaled_pixmap)

        # --------------------
        # PHASE 4: particles + cursor clones
        # --------------------
        elif self.current_phase == 4:
            painter.drawPixmap(0, 0, self.screenshot_pixmap)
            if random.random() < 0.3:
                self.particles.append({
                    "x": random.randint(0, self.screen_width),
                    "y": random.randint(0, self.screen_height),
                    "color": QtGui.QColor.fromHsv(random.randint(0, 359), 255, 255),
                    "life": 30
                })
            for particle in self.particles:
                painter.setBrush(particle["color"])
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.drawEllipse(particle["x"], particle["y"], 10, 10)
                particle["life"] -= 1
            self.particles = [p for p in self.particles if p["life"] > 0]

            if random.random() < 0.05:
                self.cursor_clones.append((random.randint(0, self.screen_width),
                                           random.randint(0, self.screen_height)))
            for cx, cy in self.cursor_clones[-50:]:
                painter.drawPixmap(cx, cy, 32, 32, self.screenshot_pixmap.copy(0, 0, 32, 32))

        # --------------------
        # PHASE 5: worm/melt effect
        # --------------------
        elif self.current_phase == 5:
            for y in range(0, self.screen_height, 20):
                offset = random.randint(-20, 20)
                rect = QtCore.QRect(0, y, self.screen_width, 20)
                painter.drawPixmap(offset, y, self.screenshot_pixmap,
                                   rect.x(), rect.y(), rect.width(), rect.height())

        # --------------------
        # PHASE 6: rotate
        # --------------------
        elif self.current_phase == 6:
            painter.translate(self.screen_width // 2, self.screen_height // 2)
            angle = (elapsed_time / 50) % 360
            painter.rotate(angle)
            painter.drawPixmap(
                -int(self.screen_width / 2),
                -int(self.screen_height / 2),
                self.screenshot_pixmap
            )

        # --------------------
        # PHASE 7: split/mirror/flashing
        # --------------------
        elif self.current_phase == 7:
            num_splits = min(8, 2 ** (elapsed_time // 2500))
            tile_width = self.screen_width // num_splits
            tile_height = self.screen_height // num_splits
            for i in range(num_splits):
                for j in range(num_splits):
                    tile = self.screenshot_pixmap.copy()
                    if random.random() < 0.5:
                        tile = tile.transformed(QtGui.QTransform().scale(-1, 1))
                    if random.random() < 0.5:
                        tile = tile.transformed(QtGui.QTransform().scale(1, -1))
                    painter.drawPixmap(i * tile_width, j * tile_height,
                                       tile_width, tile_height, tile)
            if random.random() < 0.2:
                painter.fillRect(0, 0, self.screen_width, self.screen_height,
                                 QtGui.QColor(255, 255, 255, 120))


# ------------------------
# MAIN APP
# ------------------------
def main():
    app = QtWidgets.QApplication(sys.argv)

    reply = QtWidgets.QMessageBox.question(
        None,
        'Warning',
        '⚠️ THIS PROGRAM PRODUCES INTENSE VISUAL EFFECTS. IT MAY CAUSE HIGH CPU/GPU USAGE, APPLICATION CRASHES, DISPLAY/DRIVER ISSUES, OR PHYSICAL DISCOMFORT (INCLUDING SEIZURES) FOR SENSITIVE INDIVIDUALS. RUN ONLY ON A MACHINE YOU OWN OR IN A VIRTUAL MACHINE. BACK UP IMPORTANT DATA BEFORE CONTINUING. THE AUTHOR IS NOT LIABLE FOR ANY DAMAGE, DATA LOSS, OR INJURY. IF YOU DO NOT ACCEPT THESE RISKS, CLOSE THE PROGRAM NOW. CONTINUE?',
        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
    )

    if reply != QtWidgets.QMessageBox.StandardButton.Yes:
        sys.exit()

    # Play song
    pygame.mixer.init()
    pygame.mixer.music.load('song.mp3')
    pygame.mixer.music.play(-1)

    # Show fullscreen overlay
    overlay = PrankMalwareOverlay()
    hwnd = overlay.winId().__int__()
    ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0,
                                      overlay.screen_width,
                                      overlay.screen_height,
                                      0x0001 | 0x0002)
    overlay.showFullScreen()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
