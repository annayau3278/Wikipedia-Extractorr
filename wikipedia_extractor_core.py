import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (educational project)"}
WIKI_BASE = "https://en.wikipedia.org"
SKIP_SECTIONS = {"references", "external links", "see also", "further reading",
                 "notes", "bibliography", "citations"}
SKIP_CLASSES = {"reference", "mw-editsection", "navbox", "infobox", "metadata"}

def to_title(topic: str) -> str:
    return topic.strip().replace(" ", "_")

def safe_filename(title: str) -> str:
    keep = [c if (c.isalnum() or c in " -_") else "_" for c in title]
    return "".join(keep).strip().replace(" ", "_") or "article"

def numbered_filename(base: str, existing: list, ext: str = ".txt") -> str:
    candidate = f"{base}{ext}"
    n = 2
    while candidate in existing:
        candidate = f"{base}({n}){ext}"
        n += 1
    return candidate

def format_txt(article_title, article_url, sections) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append(article_title)
    lines.append(article_url)
    lines.append("=" * 60)
    lines.append("")
    for section in sections:
        lines.append("-" * 60)
        lines.append(section["title"])
        lines.append("-" * 60)
        if not section["blocks"]:
            lines.append("(no extractable content)")
        for block in section["blocks"]:
            if block["type"] == "paragraph":
                lines.append(block["text"])
            elif block["type"] == "subheading":
                lines.append(f"## {block['text']}")
            elif block["type"] == "list":
                marker = "1." if block.get("ordered") else "-"
                for item in block["items"]:
                    lines.append(f"{marker} {item}")
            elif block["type"] == "table":
                for row in block["rows"]:
                    lines.append(" | ".join(str(c) for c in row))
            lines.append("")
    return "\n".join(lines)

class WikipediaExtractor:
    def __init__(self, topic: str):
        self.error = None
        self.topic = topic
        self.title = None
        self.url = None
        self.soup = None
        try:
            self._fetch()
        except Exception as exc:
            self.error = f"Network error: {exc}"

    def _fetch(self):
        url = f"{WIKI_BASE}/wiki/{to_title(self.topic)}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            self.error = f"[NOT FOUND] No Wikipedia article for '{self.topic}'."
            return
        self.soup = BeautifulSoup(resp.text, "html.parser")
        h1 = self.soup.find("h1", id="firstHeading")
        if not h1:
            self.error = f"[NOT FOUND] No Wikipedia article for '{self.topic}'."
            return
        self.title = h1.get_text(strip=True)
        self.url = url

    def section_titles(self) -> list:
        if self.error or not self.soup:
            return []
        titles = []
        for h2 in self.soup.find_all("h2"):
            text = h2.get_text(strip=True)
            # Clean up the "[edit]" text that Wikipedia adds
            text = text.replace("[edit]", "").strip()
            if text and text.lower() not in SKIP_SECTIONS:
                titles.append(text)
        return titles

    def extract(self, section_title: str) -> dict:
        if self.error or not self.soup:
            return {"title": section_title, "blocks": []}
            
        blocks = []
        # Find the heading
        heading = None
        for h2 in self.soup.find_all("h2"):
            clean_text = h2.get_text(strip=True).replace("[edit]", "").strip()
            if clean_text == section_title:
                heading = h2
                break
                
        if not heading:
            return {"title": section_title, "blocks": []}

        # Iterate through siblings until the next h2
        for sibling in heading.find_next_siblings():
            if sibling.name == "h2":
                break
            
            # Skip unwanted elements
            if sibling.name in ["style", "script", "table"] and sibling.get("class") and any(cls in SKIP_CLASSES for cls in sibling.get("class")):
                continue
            if sibling.name == "table":
                # Extract table rows
                rows = []
                for tr in sibling.find_all("tr"):
                    cells = [th.get_text(strip=True) for th in tr.find_all(["th", "td"])]
                    if cells:
                        rows.append(cells)
                if rows:
                    blocks.append({"type": "table", "rows": rows})
                continue

            if sibling.name in ["p", "div"]:
                text = sibling.get_text(strip=True)
                if not text or text == "^":
                    continue
                
                # Check for lists inside the div
                lists = sibling.find_all(["ul", "ol"])
                if lists:
                    for lst in lists:
                        items = [li.get_text(strip=True) for li in lst.find_all("li", recursive=False)]
                        if items:
                            blocks.append({
                                "type": "list", 
                                "items": items, 
                                "ordered": lst.name == "ol"
                            })
                elif text:
                    blocks.append({"type": "paragraph", "text": text})
                    
            elif sibling.name in ["h3", "h4"]:
                text = sibling.get_text(strip=True).replace("[edit]", "").strip()
                if text:
                    blocks.append({"type": "subheading", "text": text})
                    
        return {"title": section_title, "blocks": blocks}