import threading

from test_main_window import OK, FakeService, make_window, refresh, row_keys
from ticket_factory import make_ticket


class Accepting:
    def __init__(self, calls: list) -> None:
        self.calls = calls

    def __call__(self, parent):
        calls = self.calls

        class Dialog:
            def exec(self) -> int:
                calls.append(1)
                return 1

        return Dialog()


def test_set_service_clears_old_data_and_refreshes(qtbot) -> None:
    window = make_window(qtbot, FakeService([make_ticket("CAE-1")]))
    refresh(qtbot, window)
    window.filter_bar.findings_only.setChecked(True)
    assert window.filter_bar.is_active()
    new_service = FakeService([make_ticket("CAE-9")], results=[OK])
    window.set_service(new_service, None)
    qtbot.waitUntil(lambda: row_keys(window) == ["CAE-9"], timeout=5000)
    assert not window.filter_bar.is_active()
    assert new_service.refresh_threads


def test_set_service_not_configured_shows_the_message_and_disables_refresh(qtbot) -> None:
    window = make_window(qtbot, FakeService([make_ticket("CAE-1")]))
    refresh(qtbot, window)
    window.set_service(FakeService(), "Jira is not configured.")
    assert row_keys(window) == []
    assert window.stack.currentWidget() is window.message_page
    assert window.message_label.text() == "Jira is not configured."
    assert not window.refresh_action.isEnabled()
    assert not window.filter_bar.isVisibleTo(window)


def test_swap_is_deferred_while_a_refresh_is_running(qtbot) -> None:
    gate = threading.Event()
    old = FakeService([make_ticket("CAE-1")], gate=gate)
    new = FakeService([make_ticket("CAE-9")], results=[OK])
    calls: list[int] = []
    swaps: list[int] = []

    def reconfigure():
        swaps.append(1)
        return new, None

    window = make_window(qtbot, old, reconfigure=reconfigure, dialog_factory=Accepting(calls))
    window.start_refresh()
    window.open_setup()
    assert calls == [1] and swaps == []
    gate.set()
    qtbot.waitUntil(lambda: row_keys(window) == ["CAE-9"], timeout=5000)
    assert swaps == [1]
    assert old.tickets and window._service is new


def test_cancelled_dialog_changes_nothing(qtbot) -> None:
    class Rejecting:
        def __call__(self, parent):
            class Dialog:
                def exec(self) -> int:
                    return 0

            return Dialog()

    swaps: list[int] = []
    window = make_window(
        qtbot,
        FakeService([make_ticket("CAE-1")]),
        reconfigure=lambda: swaps.append(1),
        dialog_factory=Rejecting(),
    )
    refresh(qtbot, window)
    window.open_setup()
    assert swaps == [] and row_keys(window) == ["CAE-1"]
