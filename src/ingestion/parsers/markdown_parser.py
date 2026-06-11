import re
from typing import Dict, Any, List

class MarkdownParser:
    \"\"\"Parses Markdown documents, extracting YAML frontmatter, headers, and sections.\"\"\"

    def parse(self, markdown_content: str) -> Dict[str, Any]:
        metadata = {}
        content = markdown_content

        # Parse YAML frontmatter if present
        frontmatter_match = re.match(r"^---\\s*\\n(.*?)\\n---\\s*\\n", markdown_content, re.DOTALL)
        if frontmatter_match:
            frontmatter_text = frontmatter_match.group(1)
            content = markdown_content[frontmatter_match.end():]
            
            # Simple YAML parser (since we don't assume yaml module is always working)
            for line in frontmatter_text.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    metadata[key.strip()] = val.strip().strip("'\"")

        # Split into sections based on headers
        sections = []
        current_section = {"heading": "Root", "content": []}
        
        for line in content.splitlines():
            header_match = re.match(r"^(#{1,6})\\s+(.*)$", line)
            if header_match:
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {
                    "heading": header_match.group(2).strip(),
                    "level": len(header_match.group(1)),
                    "content": []
                }
            else:
                current_section["content"].append(line)

        if current_section["content"]:
            sections.append(current_section)

        # Rebuild clean text without frontmatter
        cleaned_text = content.strip()

        return {
            "title": metadata.get("title", "Markdown Document"),
            "content": cleaned_text,
            "metadata": metadata,
            "sections": [
                {
                    "heading": sec["heading"],
                    "content": "\\n".join(sec["content"]).strip()
                }
                for sec in sections
            ]
        }
