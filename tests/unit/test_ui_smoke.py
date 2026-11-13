from PySide6.QtWidgets import QLabel


def test_widget_can_be_shown_offscreen(qtbot) -> None:
    widget = QLabel("hello")
    qtbot.addWidget(widget)
    widget.show()
    assert widget.isVisible()
