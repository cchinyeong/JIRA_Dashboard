from datetime import UTC, date, datetime

from ticket_factory import make_ticket

from jira_dashboard.models import Finding, FindingCode, Sprint, TicketStatus, User
from jira_dashboard.ui.details_panel import HINT, NO_FINDINGS, DetailsPanel


def make_panel(qtbot) -> DetailsPanel:
    panel = DetailsPanel()
    qtbot.addWidget(panel)
    panel.show()
    return panel


def test_empty_state_shows_hint_and_no_values(qtbot) -> None:
    panel = make_panel(qtbot)
    assert panel.hint.text() == HINT
    assert panel.hint.isVisibleTo(panel)
    assert not panel.scroll.isVisibleTo(panel)
    assert not panel.open_button.isEnabled()


def test_full_ticket_values(qtbot) -> None:
    ticket = make_ticket(
        "CAE-5",
        summary="Study",
        reporter=User(username="bob", display_name="Bob"),
        requester="Carol",
        request_drivers=("Fatigue", "Drop"),
        target_start_date=date(2026, 10, 1),
        created_date=datetime(2026, 9, 1, tzinfo=UTC),
        estimated_effort=5.0,
        description="Do the study",
    )
    panel = make_panel(qtbot)
    panel.show_ticket(ticket, None, "https://x/CAE-5")
    assert not panel.hint.isVisibleTo(panel)
    assert panel.title.text() == "CAE-5  Study"
    assert panel.value("Status") == "In Progress"
    assert panel.value("Assignee") == "Ann"
    assert panel.value("Reporter") == "Bob"
    assert panel.value("Requester") == "Carol"
    assert panel.value("Request drivers") == "Fatigue, Drop"
    assert panel.value("Target start") == "01 Oct 2026"
    assert panel.value("Target end") == "05 Nov 2026"
    assert panel.value("Created") == "01 Sep 2026"
    assert panel.value("Estimated (days)") == "5"
    assert panel.value("Remaining (days)") == "2.5"
    assert panel.description.toPlainText() == "Do the study"
    assert not panel.is_unknown("Assignee")


def test_unknown_values(qtbot) -> None:
    ticket = make_ticket(requester=None, sprint=None, target_end_date=None, remaining_effort=None)
    panel = make_panel(qtbot)
    panel.show_ticket(ticket, None, None)
    for name in ("Requester", "Sprint", "Target end", "Remaining (days)"):
        assert panel.value(name) == "Unknown"
        assert panel.is_unknown(name)
    assert panel.description.toPlainText() == "Unknown"


def test_non_standard_status(qtbot) -> None:
    ticket = make_ticket(status=TicketStatus.UNKNOWN, raw_status="Implemented")
    panel = make_panel(qtbot)
    panel.show_ticket(ticket, None, None)
    assert panel.value("Status") == "Unknown (Implemented)"
    assert panel.is_unknown("Status")


def test_dyson_projects_shown_or_unknown(qtbot) -> None:
    panel = make_panel(qtbot)
    panel.show_ticket(make_ticket(dyson_projects=("898B", "915")), None, None)
    assert panel.value("Dyson projects") == "898B, 915"
    assert not panel.is_unknown("Dyson projects")
    panel.show_ticket(make_ticket(), None, None)
    assert panel.value("Dyson projects") == "Unknown"
    assert panel.is_unknown("Dyson projects")


def test_sprint_with_dates(qtbot) -> None:
    sprint = Sprint(1, "Sprint 7", "ACTIVE", date(2026, 11, 2), date(2026, 11, 13))
    panel = make_panel(qtbot)
    panel.show_ticket(make_ticket(sprint=sprint), None, None)
    assert panel.value("Sprint") == "Sprint 7 (ACTIVE, 02 Nov 2026 – 13 Nov 2026)"


def test_blocked_ticket(qtbot) -> None:
    panel = make_panel(qtbot)
    panel.show_ticket(make_ticket(status=TicketStatus.REFINEMENT), None, None)
    assert panel.value("Blocked") == "Yes"
    panel.show_ticket(
        make_ticket(status=TicketStatus.REFINEMENT, blocked_reason="Waiting for model"), None, None
    )
    assert panel.value("Blocked") == "Yes: Waiting for model"
    panel.show_ticket(make_ticket(), None, None)
    assert panel.value("Blocked") == "No"


def test_parent_loaded_not_loaded_and_none(qtbot) -> None:
    panel = make_panel(qtbot)
    child = make_ticket("CAE-2", parent_key="CAE-1")
    parent = make_ticket("CAE-1", summary="Epic summary", issue_type="Epic")
    panel.show_ticket(child, parent, None)
    assert panel.value("Parent") == "CAE-1 · Epic · Epic summary"
    panel.show_ticket(child, None, None)
    assert panel.value("Parent") == "CAE-1"
    panel.show_ticket(make_ticket(), None, None)
    assert panel.value("Parent") == "None"


def test_findings_listed_in_full(qtbot) -> None:
    findings = (
        Finding(
            FindingCode.REQUEST_WRONG_EPIC_LINK,
            "Linked with the wrong relation.",
            field="issuelinks",
            related_key="CAE-9",
            suggestion="Use 'is caused by'.",
        ),
        Finding(FindingCode.INVALID_VALUE, "Bad value."),
    )
    panel = make_panel(qtbot)
    panel.show_ticket(make_ticket(findings=findings), None, None)
    texts = panel.finding_texts()
    assert len(texts) == 2
    assert "Linked with the wrong relation." in texts[0]
    assert "Field: issuelinks" in texts[0]
    assert "Related: CAE-9" in texts[0]
    assert "Suggestion: Use 'is caused by'." in texts[0]
    assert texts[1] == "Bad value."


def test_no_findings_message_and_refresh_of_findings(qtbot) -> None:
    finding = Finding(FindingCode.INVALID_VALUE, "Bad value.")
    panel = make_panel(qtbot)
    panel.show_ticket(make_ticket(findings=(finding,)), None, None)
    panel.show_ticket(make_ticket(), None, None)
    assert panel.finding_texts() == [NO_FINDINGS]


def test_description_is_formatted_and_markup_is_escaped(qtbot) -> None:
    description = (
        "{panel:title=Background|titleBGColor=#ffffcc}\nA *bold* point\n{panel}\n"
        "<b>x</b> <script>y</script>"
    )
    ticket = make_ticket(summary="<i>s</i>", description=description, requester="<u>r</u>")
    panel = make_panel(qtbot)
    panel.show_ticket(ticket, None, None)
    text = panel.description.toPlainText()
    assert "Background" in text and "A bold point" in text
    assert "{panel" not in text and "titleBGColor" not in text and "*bold*" not in text
    assert "<b>x</b> <script>y</script>" in text
    assert panel.value("Requester") == "<u>r</u>"
    assert panel.title.text() == "CAE-1  <i>s</i>"
    assert panel.title.textFormat().name == "PlainText"
    assert not panel.description.openLinks()


def test_open_button_follows_link_and_emits_signal(qtbot) -> None:
    panel = make_panel(qtbot)
    panel.show_ticket(make_ticket(), None, None)
    assert not panel.open_button.isEnabled()
    panel.show_ticket(make_ticket(), None, "https://jira.example.test/browse/CAE-1")
    assert panel.open_button.isEnabled()
    with qtbot.waitSignal(panel.open_requested, timeout=1000):
        panel.open_button.click()
