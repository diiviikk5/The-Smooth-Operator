import logging
from typing import Dict, Any, List
import io

logger = logging.getLogger(__name__)

class PDFParser:
    \"\"\"Parses PDF documents into plain text and page-wise metadata.\"\"\"

    def parse(self, pdf_bytes: bytes) -> Dict[str, Any]:
        text_content = []
        pages_metadata = []

        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_content.append(text)
                    pages_metadata.append({
                        "page_number": page_num + 1,
                        "char_count": len(text)
                    })
            
            # Simple document metadata
            doc_info = {}
            if reader.metadata:
                doc_info = {
                    "author": reader.metadata.get("/Author", ""),
                    "creator": reader.metadata.get("/Creator", ""),
                    "producer": reader.metadata.get("/Producer", ""),
                    "subject": reader.metadata.get("/Subject", ""),
                    "title": reader.metadata.get("/Title", ""),
                }

            full_text = "\\n\\n--- Page Break ---\\n\\n".join(text_content)
            
            return {
                "title": doc_info.get("title", "PDF Document"),
                "content": full_text,
                "metadata": doc_info,
                "pages": pages_metadata
            }

        except ImportError:
            logger.warning("PyPDF2 not installed. Returning empty parser output.")
            return {
                "title": "PDF Document (Parsing Failed)",
                "content": "",
                "metadata": {},
                "pages": []
            }
        except Exception as e:
            logger.error(f"Error parsing PDF: {str(e)}")
            raise
