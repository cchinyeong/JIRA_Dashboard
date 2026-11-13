from jira_dashboard.ui.jira_markup import to_html

PANEL = "{panel:title=Background|titleBGColor=#ffffcc}\nThe dock tray is thick.\n{panel}"


def test_panel_becomes_a_heading_without_the_codes() -> None:
    result = to_html(PANEL)
    assert "<b>Background</b>" in result
    assert "The dock tray is thick." in result
    assert "{panel" not in result and "titleBGColor" not in result


def test_inline_panel_on_one_line() -> None:
    result = to_html("{panel:title=PIC (Requester - Full Name)|titleBGColor=#ffffcc} . {panel}")
    assert "<b>PIC (Requester - Full Name)</b>" in result
    assert "{panel" not in result


def test_headings_bold_italic_and_monospace() -> None:
    result = to_html("h2. Goals\nA *bold* and _italic_ and {{code}} word")
    assert "<h4>Goals</h4>" in result
    assert "<b>bold</b>" in result and "<i>italic</i>" in result
    assert "<code>code</code>" in result


def test_underscores_inside_words_are_left_alone() -> None:
    assert "<i>" not in to_html("use snake_case_name here and 2*3*4")


def test_lists_keep_order_and_depth() -> None:
    result = to_html("# first\n# second\n* point\n** nested")
    assert "1. first" in result and "2. second" in result
    assert "• point" in result
    assert "margin-left:18px" in result and "nested" in result


def test_numbering_restarts_after_a_gap() -> None:
    result = to_html("# a\n# b\n\ntext\n# c")
    assert "1. c" in result


def test_images_links_mentions_and_colour() -> None:
    result = to_html(
        "!image-1.png|thumbnail! see [the page|https://wiki.example/x] "
        "ask [~jsmith] {color:red}now{color}"
    )
    assert "[image: image-1.png]" in result
    assert "the page (https://wiki.example/x)" in result
    assert "@jsmith" in result
    assert "now" in result and "{color" not in result
    assert "<img" not in result and "<a " not in result


def test_table() -> None:
    result = to_html("||Name||Value||\n|alpha|1|\n|beta|2|")
    assert "<th>Name</th>" in result
    assert "<td>alpha</td>" in result and "<td>2</td>" in result


def test_code_block_is_preformatted_and_not_converted() -> None:
    result = to_html("{code:python}\nx = *y*\n{code}")
    assert "<pre>x = *y*</pre>" in result


def test_html_in_the_text_is_escaped() -> None:
    result = to_html('<script>alert(1)</script> <img src="x"> & done\n{code}<b>x</b>{code}')
    assert "<script>" not in result and "<img" not in result
    assert "&lt;script&gt;" in result and "&amp; done" in result
    assert "<pre>&lt;b&gt;x&lt;/b&gt;</pre>" in result


def test_horizontal_rule_and_blank_lines_collapse() -> None:
    result = to_html("one\n\n\n\ntwo\n----\nthree")
    assert result.count("<br>") == 1
    assert "<hr>" in result
