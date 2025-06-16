from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QWidget,
    QVBoxLayout, QHBoxLayout, QSizePolicy,
    QPushButton, QGridLayout
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize, QUrl, QTimer
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
import json
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Load gui.json
        with open('gui.json', 'r') as f:
            gui_config = json.load(f)['gui']
            frames_config = gui_config['frames']
            self.default_width = gui_config.get('default-width', 1000)
            self.default_height = gui_config.get('default-height', 700)

            # Top frame config
            top_config = frames_config['top']
            self.default_top_percent = top_config.get('height-percent', 40)
            self.min_top_percent = top_config.get('height-percent-min', 30)
            self.max_top_percent = top_config.get('height-percent-max', 70)

            self.top_bg_color = top_config.get('background-color', '#191E22')
            self.top_left_config = top_config.get('left', {})
            self.top_right_config = top_config.get('right', {})

            self.top_splitter_config = top_config.get('splitter', {})

            # Top right width control
            self.default_top_right_percent = self.top_right_config.get('width-percent', 50)
            self.min_top_right_percent = self.top_right_config.get('width-percent-min', 30)
            self.max_top_right_percent = self.top_right_config.get('width-percent-max', 70)

            # Bottom frame config
            bottom_config = frames_config['bottom']
            self.bottom_padding = bottom_config.get('padding', 10)
            self.bottom_bg_color = bottom_config.get('background-color', '#232C32')

            # Main vertical splitter config
            self.main_splitter_config = frames_config.get('splitter', {})

        self.setWindowTitle("Playout GUI")
        self.setMinimumSize(800, 600)

        # Central widget and layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Vertical splitter (top/bottom)
        self.main_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(self.main_splitter)
        self.apply_splitter_style(self.main_splitter, self.main_splitter_config)

        # Top frame with horizontal splitter inside
        self.top_frame = QWidget()
        top_layout = QHBoxLayout(self.top_frame)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self.top_splitter = QSplitter(Qt.Horizontal)
        top_layout.addWidget(self.top_splitter)
        self.apply_splitter_style(self.top_splitter, self.top_splitter_config)

        # Left widget in top
        self.top_left = QWidget()
        self.top_left.setStyleSheet(f"background-color: {self.top_left_config.get('background-color', '#191E22')};")

        # Right widget in top — contains nested top & bottom frames (no splitter)
        self.top_right = QWidget()
        self.top_right.setStyleSheet(f"background-color: {self.top_right_config.get('background-color', '#191E22')};")

        self.top_splitter.addWidget(self.top_left)
        self.top_splitter.addWidget(self.top_right)

        # --- Nested layout for top_right ---
        right_layout = QVBoxLayout(self.top_right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Nested top widget (expandable)
        self.top_right_top = QWidget()
        nested_top_bg = self.top_right_config.get('frames', {}).get('top', {}).get('background-color', '#111417')
        self.top_right_top.setStyleSheet(f"background-color: {nested_top_bg};")
        self.top_right_top.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Setup video player inside nested top widget
        self.setup_video_player()

        # Load and start video
        video_path = "E:/projects/python/playout/video/sample.wmv"
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
        #self.media_player.play()

        # Nested bottom widget (fixed height)
        self.top_right_bottom = QWidget()
        bottom_frame_cfg = self.top_right_config.get('frames', {}).get('bottom', {})
        nested_bottom_bg = bottom_frame_cfg.get('background-color', '#222831')
        self.top_right_bottom.setStyleSheet(f"background-color: {nested_bottom_bg};")

        # Save controls and height config for button grid
        self.bottom_frame_cfg = bottom_frame_cfg
        self.bottom_controls_config = bottom_frame_cfg.get('controls', {})

        right_layout.addWidget(self.top_right_top)
        right_layout.addWidget(self.top_right_bottom)

        # Create button grid inside bottom of top right
        self.create_button_grid()

        # Bottom frame
        self.bottom_frame = QWidget()
        self.bottom_frame.setStyleSheet(f"background-color: {self.bottom_bg_color};")

        self.main_splitter.addWidget(self.top_frame)
        self.main_splitter.addWidget(self.bottom_frame)

        self.load_position()

        # Connect splitter signals
        self.main_splitter.splitterMoved.connect(self.on_main_splitter_moved)
        self.top_splitter.splitterMoved.connect(self.on_top_splitter_moved)

        # Timer for delayed resize after sash drag ends
        self.resize_delay_timer = QTimer(self)
        self.resize_delay_timer.setSingleShot(True)
        self.resize_delay_timer.timeout.connect(self._on_delayed_resize_video)

    def apply_splitter_style(self, splitter, config):
        bg = config.get('background-color', '#191E22')
        thickness = config.get('height', 0)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {bg};
                {'height' if splitter.orientation() == Qt.Vertical else 'width'}: {thickness}px;
            }}
        """)

    def load_position(self):
        config = {}
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                config = json.load(f)

        x = (self.screen().geometry().width() - self.default_width) // 2
        y = (self.screen().geometry().height() - self.default_height) // 2
        width = self.default_width
        height = self.default_height
        top_percent = self.default_top_percent
        left_percent = 50

        if 'main' in config:
            main_cfg = config['main']
            x = main_cfg.get('x', x)
            y = main_cfg.get('y', y)
            width = main_cfg.get('width', width)
            height = main_cfg.get('height', height)
            top_percent = main_cfg.get('top_height_percent', top_percent)
            left_percent = main_cfg.get('top_left_percent', left_percent)

        self.setGeometry(x, y, width, height)

        top_height = int(height * top_percent / 100)
        bottom_height = height - top_height
        self.main_splitter.setSizes([top_height, bottom_height])

        left_width = int(width * left_percent / 100)
        right_width = width - left_width
        self.top_splitter.setSizes([left_width, right_width])

        self.update_main_splitter_limits()
        self.update_top_splitter_limits()

    def save_position(self):
        geom = self.geometry()
        sizes_main = self.main_splitter.sizes()
        sizes_top = self.top_splitter.sizes()
        total_height = sum(sizes_main)
        total_width = sum(sizes_top)

        top_height = sizes_main[0]
        top_percent = (top_height / total_height) * 100 if total_height > 0 else self.default_top_percent
        top_percent = max(self.min_top_percent, min(self.max_top_percent, top_percent))

        left_width = sizes_top[0]
        left_percent = (left_width / total_width) * 100 if total_width > 0 else 50

        config = {}
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                config = json.load(f)

        config['main'] = {
            'x': geom.x(),
            'y': geom.y(),
            'width': geom.width(),
            'height': geom.height(),
            'top_height_percent': top_percent,
            'top_left_percent': left_percent
        }

        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)

    def update_main_splitter_limits(self):
        total_height = self.height()
        min_top = int(total_height * self.min_top_percent / 100)
        max_top = int(total_height * self.max_top_percent / 100)

        self.top_frame.setMinimumHeight(min_top)
        self.top_frame.setMaximumHeight(max_top)

        min_bottom = total_height - max_top
        max_bottom = total_height - min_top
        self.bottom_frame.setMinimumHeight(min_bottom)
        self.bottom_frame.setMaximumHeight(max_bottom)

    def update_top_splitter_limits(self):
        total_width = self.width()

        min_right_pct_width = int(total_width * self.min_top_right_percent / 100)
        max_right_pct_width = int(total_width * self.max_top_right_percent / 100)

        controls = self.bottom_controls_config
        button_size = controls.get('button-size', 50)
        cell_spacing = controls.get('cell-spacing', 10)
        padding = self.bottom_frame_cfg.get('padding', self.bottom_padding)

        # Count actual buttons
        button_count = len([
            b for b in ['play', 'stop', 'vol_up', 'vol_down', 'vol_up_fade', 'vol_down_fade']
            if b in self.buttons
        ])

        total_buttons_width = (button_size * button_count) + (cell_spacing * (button_count - 1)) + (2 * padding)

        min_right = max(min_right_pct_width, total_buttons_width)
        max_right = max_right_pct_width

        min_left = total_width - max_right
        max_left = total_width - min_right

        self.top_left.setMinimumWidth(min_left)
        self.top_left.setMaximumWidth(max_left)
        self.top_right.setMinimumWidth(min_right)
        self.top_right.setMaximumWidth(max_right)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_main_splitter_limits()
        self.update_top_splitter_limits()

    def on_main_splitter_moved(self, pos, index):
        self.video_widget.hide()
        self.update_main_splitter_limits()
        self.save_position()
        self.resize_delay_timer.start(300)  # debounce resize after drag

    def on_top_splitter_moved(self, pos, index):
        self.video_widget.hide()
        self.update_top_splitter_limits()
        self.save_position()
        self.resize_delay_timer.start(300)  # debounce resize after drag

    def create_button_grid(self):
        controls = self.bottom_controls_config

        buttons_info = {
            'play': 'play',
            'stop': 'stop',
            'vol_up': 'vol_up',
            'vol_down': 'vol_down',
            'vol_up_fade': 'vol_up_fade',
            'vol_down_fade': 'vol_down_fade'
        }

        button_count = len(buttons_info)
        padding = controls.get('padding', 0)
        bottom_padding = self.bottom_frame_cfg.get('padding', 0)
        controls_padding = self.bottom_controls_config.get('padding', 0)

        cell_spacing = controls.get('cell-spacing', 5)
        button_size = controls.get('button-size', 50)
        default_icon_size = controls.get('icon-size', 32)

        total_buttons_width = (button_size * button_count) + (cell_spacing * (button_count - 1)) + (2 * padding)

        total_height = button_size + 2 * bottom_padding
        self.top_right_bottom.setFixedHeight(total_height)

        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(cell_spacing)
        grid_layout.setVerticalSpacing(cell_spacing)

        self.buttons = {}

        border_style = controls.get('border-style', 'solid')
        border_width = controls.get('border-width', 3)
        border_color = controls.get('border-color', '#e1e1e1')
        border_radius = controls.get('border-radius', 5)

        button_style = f"""
            QPushButton {{
                border-style: {border_style};
                border-width: {border_width}px;
                border-color: {border_color};
                border-radius: {border_radius}px;
            }}
            QPushButton:hover {{
                background-color: #444;
            }}
        """

        col = 0
        for btn_key, config_key in buttons_info.items():
            btn = QPushButton()
            btn.setFixedSize(button_size, button_size)
            btn.setStyleSheet(button_style)

            icon_path = controls.get(config_key, {}).get('icon', '')
            if icon_path and os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                icon_size = controls.get(config_key, {}).get('icon-size', default_icon_size)
                btn.setIconSize(QSize(icon_size, icon_size))

            grid_layout.addWidget(btn, 0, col)
            self.buttons[btn_key] = btn
            col += 1

        grid_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        grid_container.setFixedSize(
            button_size * len(buttons_info) + cell_spacing * (len(buttons_info) - 1),
            button_size
        )

        old_layout = self.top_right_bottom.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
            old_layout.deleteLater()

        center_layout = QHBoxLayout()
        center_layout.setContentsMargins(controls_padding, controls_padding, controls_padding, controls_padding)
        center_layout.setSpacing(0)
        center_layout.addStretch()
        center_layout.addWidget(grid_container)
        center_layout.addStretch()
        center_layout.setAlignment(grid_container, Qt.AlignVCenter)

        self.top_right_bottom.setLayout(center_layout)
        self.top_right_bottom.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Adjust top_right width if button grid is wider
        total_width = self.width()

        min_right_width = int(total_width * self.min_top_right_percent / 100)
        max_right_width = int(total_width * self.max_top_right_percent / 100)
        default_right_width = int(total_width * self.top_right_config.get('width-percent', 50) / 100)

        desired_width = max(default_right_width, total_buttons_width + 2 * controls_padding)
        desired_width = max(min_right_width, min(desired_width, max_right_width))

        self.top_right.setMinimumWidth(desired_width)
        self.top_right.setMaximumWidth(desired_width)

    def setup_video_player(self):
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)

        self.video_widget = QVideoWidget(self.top_right_top)
        self.video_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.media_player.setVideoOutput(self.video_widget)

        layout = QVBoxLayout(self.top_right_top)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.video_widget, alignment=Qt.AlignCenter)

        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._on_delayed_resize_video)

        def resize_event(event):
            self.resize_timer.start(100)
            event.accept()

        self.top_right_top.resizeEvent = resize_event

        # Initial sizing
        self._on_delayed_resize_video()

    def _on_delayed_resize_video(self):
        w = self.top_right_top.width()
        h = self.top_right_top.height()

        # Maintain 16:9 aspect ratio inside container
        target_w = w
        target_h = int(w * 9 / 16)

        if target_h > h:
            target_h = h
            target_w = int(h * 16 / 9)

        self.video_widget.resize(target_w, target_h)
        self.video_widget.move((w - target_w) // 2, (h - target_h) // 2)
        self.video_widget.show()

    def closeEvent(self, event):
        self.save_position()
        super().closeEvent(event)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
