from bs4 import BeautifulSoup
import re
from typing import Dict, Any, List

class HTMLParser:
    \"\"\"Parses raw HTML into cleaned structured text and metadata.\"\"\"

    def __init__(self):
        self.boilerplate_selectors = [
            "nav", "footer", "header", "sidebar", ".sidebar", 
            "#sidebar", ".footer", "#footer", ".nav", "#nav",
            ".menu", "#menu", ".cookie", ".popup", ".modal", ".ads", ".ad"
        ]

    def parse(self, html_content: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract metadata
        metadata = self._extract_metadata(soup)

        # Remove boilerplate
        for selector in self.boilerplate_selectors:
            for element in soup.select(selector):
                element.decompose()

        # Extract structured sections
        sections = []
        current_section = {"heading": "Introduction", "content": []}

        for element in soup.find_all(["h1", "h2", "h3", "p", "ul", "ol", "table"]):
            if element.name in ["h1", "h2", "h3"]:
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {"heading": element.get_text(strip=True), "content": []}
            elif element.name == "p":
                text = element.get_text(strip=True)
                if text:
                    current_section["content"].append(text)
            elif element.name in ["ul", "ol"]:
                items = [li.get_text(strip=True) for li in element.find_all("li") if li.get_text(strip=True)]
                if items:
                    current_section["content"].append("\\n".join(f"- {item}" for item in items))
            elif element.name == "table":
                rows = []
                for tr in element.find_all("tr"):
                    cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                    if cells:
                        rows.append(" | ".join(cells))
                if rows:
                    current_section["content"].append("\\n".join(rows))

        if current_section["content"]:
            sections.append(current_section)

        # Build clean plain text
        plain_text_parts = []
        for sec in sections:
            plain_text_parts.append(f"## {sec['heading']}\\n" + "\\n".join(sec["content"]))
        
        cleaned_text = "\\n\\n".join(plain_text_parts)

        return {
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "content": cleaned_text,
            "metadata": metadata,
            "sections": sections
        }

    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        metadata = {}
        
        # Title
        if soup.title:
            metadata["title"] = soup.title.get_text(strip=True)
            
        # Description
        desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if desc_tag and desc_tag.get("content"):
            metadata["description"] = desc_tag.get("content").strip()

        # Keywords
        kw_tag = soup.find("meta", attrs={"name": "keywords"})
        if kw_tag and kw_tag.get("content"):
            metadata["keywords"] = [k.strip() for k in kw_tag.get("content").split(",")]

        return metadata
