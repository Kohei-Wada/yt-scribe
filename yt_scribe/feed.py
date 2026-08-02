"""Stored entries as Atom, the one interface this project exposes."""

from datetime import datetime, timezone
from xml.etree import ElementTree as ET

ATOM = "http://www.w3.org/2005/Atom"


def _content(entry: dict) -> str:
    # Summary first so a reader's list view shows something worth reading
    # without per-reader configuration; transcript after so full-text search
    # reaches the whole video.
    parts = []
    if entry.get("summary"):
        parts.append(entry["summary"])
    parts.append(entry["transcript"])
    return "\n\n".join(parts)


def render(entries: list[dict], title: str, self_url: str) -> str:
    ET.register_namespace("", ATOM)
    feed = ET.Element(f"{{{ATOM}}}feed")
    ET.SubElement(feed, f"{{{ATOM}}}title").text = title
    ET.SubElement(feed, f"{{{ATOM}}}id").text = self_url
    ET.SubElement(feed, f"{{{ATOM}}}updated").text = datetime.now(timezone.utc).isoformat()
    ET.SubElement(feed, f"{{{ATOM}}}link", rel="self", href=self_url)

    for entry in entries:
        node = ET.SubElement(feed, f"{{{ATOM}}}entry")
        ET.SubElement(node, f"{{{ATOM}}}title").text = entry["title"]
        # urn: rather than the URL, so the identity survives a URL change.
        ET.SubElement(node, f"{{{ATOM}}}id").text = f"urn:youtube:{entry['id']}"
        ET.SubElement(node, f"{{{ATOM}}}link", rel="alternate", href=entry["url"])
        ET.SubElement(node, f"{{{ATOM}}}published").text = entry["published"]
        ET.SubElement(node, f"{{{ATOM}}}updated").text = entry["published"]
        author = ET.SubElement(node, f"{{{ATOM}}}author")
        ET.SubElement(author, f"{{{ATOM}}}name").text = entry["channel"]
        ET.SubElement(node, f"{{{ATOM}}}content", type="text").text = _content(entry)

    return ET.tostring(feed, encoding="unicode", xml_declaration=True)
