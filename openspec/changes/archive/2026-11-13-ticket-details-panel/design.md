# Design

## Context

`MainWindow` has a `QTableView` over `TicketTableModel` and a sort proxy; selecting a row already drives the "Open in Jira" action. `Ticket` carries every field the panel needs. The parent is available through `service.snapshot.get(key)`, which returns tickets from both the table and the context (parents loaded for hierarchy), so no service change is needed. The window runs on dark and light themes; the earlier tint problem showed that hard-coded light colours break in dark mode.

## Goals / Non-Goals

**Goals:**
- Show everything known about one ticket, readable in both themes.
- Keep the panel a dumb view: it receives a ticket and a few lookups, and holds no Jira or service logic.

**Non-Goals:**
- Editing, wiki-markup rendering, comments, history, filters, grouping, setup dialog.

## Decisions

- **Widget: `DetailsPanel(QWidget)`** in `ui/details_panel.py` with `show_ticket(ticket | None, parent_ticket | None, link | None)`. The window computes the parent (`service.snapshot.get(ticket.parent_key)`) and link (`service.ticket_link`) and passes them in, so the panel needs no service and tests need no fake service.
- **Layout:** `QSplitter` (table left, panel right, initial sizes about 3:1, panel collapsible). The panel is a `QScrollArea` containing a form: a header label (key and summary, bold), then sections as `QGroupBox` with `QFormLayout` rows (People, Planning, Hierarchy), then Findings, then Description. Alternative: a `QTextBrowser` with generated HTML; rejected because it invites injecting Jira text as markup and styles badly in dark mode.
- **Text and description:** every value goes through `QLabel.setText` with `Qt.TextFormat.PlainText`. The description goes through `ui/jira_markup.to_html`, which HTML-escapes the whole text first and then converts the Jira markup it recognises (panel titles, headings, bold, italic, monospace, bullet and numbered lists, tables, code and noformat blocks, links as "text (address)", mentions, images as `[image: name]`, colour and quote markers removed) into a small subset of tags it produces itself, shown in a read-only `QTextBrowser` with link opening disabled. Alternative: show the raw text; rejected because markup codes made descriptions hard to read. Alternative: a full third-party wiki renderer; rejected as a heavy dependency that would emit arbitrary HTML.
- **Formatting reuse:** the panel reuses the table's formatting helpers (date, days, status text, unknown text) moved to a small `ui/formatting.py`, so table and panel cannot drift. The table model imports them from there.
- **Unknown style:** values use the palette's disabled-text colour in italics instead of a fixed grey, so it adapts to both themes. Findings are shown in a `QGroupBox` using the palette's normal colours with a bold message line, a "Field / Related / Suggestion" line each; no fixed background colour.
- **Selection:** the window connects the table's selection change to the panel. Before a refresh it remembers the selected key; after `set_tickets` it reselects that key through the proxy if present, otherwise clears. Reselecting triggers the same update, so the panel shows new values.
- **Open in Jira button:** emits `open_requested`; the window handles it with the existing `open_selected`, so the rule stays in one place. Enabled only when a link was passed in.
- **Testing:** pytest-qt with the existing offscreen setup. Panel tests build tickets with `ticket_factory.make_ticket`. A markup test sets a description of `<b>x</b>` and asserts the text is literal.

## Risks / Trade-offs

- [Moving formatting helpers touches the table model] → covered by the existing model tests, which must stay green.
- [Very long descriptions] → shown in a scrollable read-only text box with a minimum height; no truncation.
- [Our own converter covers common Jira markup only] → unknown constructs are left as their text; escaping happens first, so an unrecognised or malformed construct can never produce unsafe output.
- [Reselect after refresh could fire the selection signal twice] → harmless (idempotent update); tested for the resulting state only.
