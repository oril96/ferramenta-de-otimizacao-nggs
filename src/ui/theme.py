"""
Dark modern stylesheet for Optimus Toolbox (PyQt6 QSS).
"""

DARK_MODERN_QSS = r"""
/* Base colors */
* {
    color: #E6E6E6;
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 10.5pt;
}

QWidget {
    background-color: #121212;
}

QGroupBox {
    border: 1px solid #2A2A2A;
    border-radius: 6px;
    margin-top: 12px;
    padding: 8px 8px 8px 8px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: #BBBBBB;
}

QPushButton {
    background-color: #1F1F1F;
    border: 1px solid #2E2E2E;
    border-radius: 6px;
    padding: 8px 12px;
}

QPushButton:hover {
    background-color: #2A2A2A;
}

QPushButton:pressed {
    background-color: #343434;
}

QStatusBar {
    background: #141414;
    border-top: 1px solid #2A2A2A;
}

QScrollBar:vertical {
    background: #161616;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical { background: #2E2E2E; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""

