from xml.etree import ElementTree

from yt_scribe.feed import render

NS = {"atom": "http://www.w3.org/2005/Atom"}


def entry(**over):
    base = {
        "id": "abc123",
        "url": "https://www.youtube.com/watch?v=abc123",
        "title": "A title",
        "published": "2026-08-02T12:00:00+00:00",
        "channel": "Channel",
        "thumbnail": None,
        "transcript": "[00:00:00.000 --> 00:00:02.000]  hello",
        "summary": "要約です",
    }
    base.update(over)
    return base


def test_output_is_parseable_atom():
    root = ElementTree.fromstring(render([entry()], "T", "http://x/f.xml"))
    assert root.tag == "{http://www.w3.org/2005/Atom}feed"
    assert len(root.findall("atom:entry", NS)) == 1


def test_summary_comes_before_the_transcript():
    xml = render([entry()], "T", "http://x/f.xml")
    root = ElementTree.fromstring(xml)
    content = root.find("atom:entry/atom:content", NS).text
    assert content.index("要約です") < content.index("hello")


def test_entry_without_a_summary_still_renders():
    xml = render([entry(summary=None)], "T", "http://x/f.xml")
    root = ElementTree.fromstring(xml)
    content = root.find("atom:entry/atom:content", NS).text
    assert "hello" in content


def test_id_is_stable_and_link_points_at_the_video():
    root = ElementTree.fromstring(render([entry()], "T", "http://x/f.xml"))
    assert root.findtext("atom:entry/atom:id", namespaces=NS) == "urn:youtube:abc123"
    link = root.find("atom:entry/atom:link", NS)
    assert link.get("href") == "https://www.youtube.com/watch?v=abc123"


def test_markup_in_a_title_is_escaped_not_injected():
    root = ElementTree.fromstring(render([entry(title="<b>hi</b>")], "T", "http://x/f.xml"))
    assert root.findtext("atom:entry/atom:title", namespaces=NS) == "<b>hi</b>"
