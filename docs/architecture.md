# System Architecture — The Smooth Operator

The Smooth Operator is a production-grade, AI-powered cold outreach engine designed for high-precision, personalized email generation and autonomous campaign execution.

```mermaid
graph TB
    subgraph Client
        UI["Dashboard / CLI"]
    end

    subgraph API["FastAPI Gateway"]
        Router["API Router /api/v1"]
        MW["Middleware (Logging · CORS · Auth)"]
    end

    subgraph Agents["LangGraph Agent Orchestrator"]
        Scraper["Scraper Agent"]
        Enricher["Enrichment Agent"]
        Scorer["Lead Scorer"]
        Writer["Email Writer Agent"]
        Reviewer["Email Reviewer Agent"]
    end

    subgraph DataStores["Data Layer"]
        PG["PostgreSQL (Leads · Campaigns · Emails)"]
        Redis["Redis (Cache · Queues)"]
        Chroma["ChromaDB (Vector Embeddings)"]
    end

    subgraph LLMs["LLM Providers"]
        OpenAI["OpenAI GPT-4o"]
        Gemini["Google Gemini"]
    end

    subgraph Observability["Observability"]
        LangSmith["LangSmith Tracing"]
        Prometheus["Prometheus Metrics"]
        StructLog["Structured Logging"]
    end

    UI --> Router
    Router --> MW
    MW --> Agents
    Scraper --> PG
    Scraper --> Redis
    Enricher --> PG
    Enricher --> Chroma
    Scorer --> PG
    Scorer --> Chroma
    Writer --> PG
    Writer --> LLMs
    Reviewer --> PG
    Reviewer --> LLMs
```

## System Workflow

1. **Ingestion & Parsing**: Leads are ingested via the REST API or scraper workflows. Raw html, github, or linkedin profiles are processed and cleaned by format-specific parsers.
2. **Context Enrichment**: Enriched profile information is stored in PostgreSQL and synced to ChromaDB for semantic search capabilities.
3. **Lead Evaluation (Scoring)**: A LangGraph state machine scores leads on ICP alignment.
4. **Drafting & Generation**: Personalized emails are generated using specialized copywriting frameworks (AIDA, PAS, BAB).
5. **Quality & Guardrails**: Text outputs undergo PII detection, tone verification, and spam check compliance before queuing.
