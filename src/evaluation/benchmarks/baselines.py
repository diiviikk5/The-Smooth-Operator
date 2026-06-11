from typing import Dict, Any, List

class NaiveRAGBaseline:
    \"\"\"Naive RAG baseline using simple vector search and standard prompt template.\"\"\"
    
    def generate(self, query: str, context: str) -> str:
        return f"Naive RAG answer based on retrieved context: {context[:100]}..."

class NoPersonalizationBaseline:
    \"\"\"Baseline outreach email generation without personalized lead variables.\"\"\"
    
    def generate(self, company: str) -> str:
        return (
            f"Hi there,\\n\\n"
            f"I hope you're doing well. I noticed {company} has a great engineering team. "
            f"We offer software automation services that help developers work faster.\\n\\n"
            f"Are you open to a brief call next week to discuss?\\n\\n"
            f"Best,\\nSales Team"
        )
