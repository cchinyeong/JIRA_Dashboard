from PySide6.QtCore import Qt
from ticket_factory import make_ticket

from jira_dashboard.models import Finding, FindingCode, TicketKind, User
from jira_dashboard.services.ticket_query import group, make_snapshot
from jira_dashboard.ui.hierarchy_model import ORPHANS_TITLE, HierarchyModel
from jira_dashboard.ui.ticket_model import TICKET_ROLE


def epic(key: str, **kw):
    return make_ticket(key, kind=TicketKind.REQUEST, issue_type="Epic", **kw)


def task(key: str, parent: str | None = None, **kw):
    return make_ticket(key, kind=TicketKind.TASK, parent_key=parent, **kw)


def build(listed, context=()) -> HierarchyModel:
    snapshot = make_snapshot(listed, context)
    model = HierarchyModel()
    model.set_view(group(listed, snapshot))
    return model


def top_texts(model: HierarchyModel) -> list[str]:
    return [model.item(r, 0).text() for r in range(model.rowCount())]


def child_keys(item) -> list[str]:
    return [item.child(r, 0).data(TICKET_ROLE).jira_key for r in range(item.rowCount())]


def test_task_sits_under_its_epic_in_key_order() -> None:
    model = build(
        [epic("CAE-1"), task("CAE-12", "CAE-1"), task("CAE-3", "CAE-1"), task("CAE-7", "CAE-1")]
    )
    assert top_texts(model) == ["CAE-1  Summary"]
    assert child_keys(model.item(0, 0)) == ["CAE-3", "CAE-7", "CAE-12"]


def test_columns_and_headers() -> None:
    model = build([epic("CAE-1", assignee=User(username="a", display_name="Ann"))])
    headers = [model.headerData(c, Qt.Orientation.Horizontal) for c in range(model.columnCount())]
    assert headers == [
        "Key / Summary",
        "Type",
        "Status",
        "Assignee",
        "Sprint",
        "Target end",
        "Findings",
    ]
    assert model.item(0, 1).text() == "Epic"
    assert model.item(0, 3).text() == "Ann"


def test_non_matching_parent_is_dimmed() -> None:
    parent = epic("CAE-1")
    child = task("CAE-2", "CAE-1")
    snapshot = make_snapshot([parent, child])
    model = HierarchyModel()
    model.set_view(group([child], snapshot))
    parent_item = model.item(0, 0)
    assert parent_item.font().italic()
    assert parent_item.background().style() == Qt.BrushStyle.NoBrush
    assert not parent_item.child(0, 0).font().italic()


def test_orphan_tasks_have_their_own_node_with_count() -> None:
    model = build([task("CAE-5"), task("CAE-6"), epic("CAE-1")])
    texts = top_texts(model)
    assert f"{ORPHANS_TITLE} (2)" in texts
    group_item = model.item(texts.index(f"{ORPHANS_TITLE} (2)"), 0)
    assert child_keys(group_item) == ["CAE-5", "CAE-6"]
    assert group_item.data(TICKET_ROLE) is None
    assert not group_item.flags() & Qt.ItemFlag.ItemIsSelectable


def test_no_orphan_node_when_every_task_has_a_parent() -> None:
    model = build([epic("CAE-1"), task("CAE-2", "CAE-1")])
    assert not any(text.startswith(ORPHANS_TITLE) for text in top_texts(model))


def test_findings_are_counted_tinted_and_explained() -> None:
    finding = Finding(FindingCode.TASK_WITHOUT_PARENT, "No parent.", suggestion="Link it.")
    model = build([task("CAE-5", findings=(finding,))])
    group_item = model.item(0, 0)
    row_item = group_item.child(0, 0)
    assert group_item.child(0, 6).text() == "1"
    assert row_item.background().style() != Qt.BrushStyle.NoBrush
    assert "No parent." in row_item.toolTip() and "Link it." in row_item.toolTip()


def test_unknown_values_are_styled() -> None:
    model = build([epic("CAE-1", assignee=None)])
    assert model.item(0, 3).text() == "Unknown"
    assert model.item(0, 3).font().italic()


def test_index_for_key_finds_nested_and_orphan_rows() -> None:
    model = build([epic("CAE-1"), task("CAE-2", "CAE-1"), task("CAE-9")])
    assert model.index_for_key("CAE-2").data(TICKET_ROLE).jira_key == "CAE-2"
    assert model.index_for_key("CAE-9").data(TICKET_ROLE).jira_key == "CAE-9"
    assert model.index_for_key("CAE-404") is None
