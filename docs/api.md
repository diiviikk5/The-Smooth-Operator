# API Documentation — The Smooth Operator

The Smooth Operator API is built with FastAPI. Interactive OpenAPI docs are available at `/docs` when the API is running.

## Authentication
By default, the API binds to port `8000` locally. Include authorization headers in production deployments.

## Endpoints

### Health Check
* **GET `/api/v1/health`**: Simple health heartbeat check.
* **GET `/api/v1/health/ready`**: Verifies connectivity to PostgreSQL, Redis, and ChromaDB.

### Leads
* **POST `/api/v1/leads`**: Add a new lead.
* **GET `/api/v1/leads`**: List all leads (paginated).
* **GET `/api/v1/leads/{id}`**: Get specific lead details.
* **PATCH `/api/v1/leads/{id}`**: Update lead properties.
* **DELETE `/api/v1/leads/{id}`**: Remove a lead from the system.
* **POST `/api/v1/leads/{id}/scrape`**: Trigger background scraper for lead profile.
* **POST `/api/v1/leads/{id}/enrich`**: Trigger lead profiling enrichment.
* **POST `/api/v1/leads/{id}/score`**: Evaluate ICP alignment score.

### Campaigns
* **POST `/api/v1/campaigns`**: Create a new outreach campaign.
* **GET `/api/v1/campaigns`**: List all active campaigns.
* **POST `/api/v1/campaigns/{id}/launch`**: Set campaign status to active.
* **GET `/api/v1/campaigns/{id}/analytics`**: Get campaign-level delivery metrics.

### Emails
* **POST `/api/v1/emails/generate`**: Draft personalized email using selected framework.
* **POST `/api/v1/emails/{id}/send`**: Dispatch email to recipient.
* **GET `/api/v1/emails/{id}/trace`**: Get LangGraph trace steps for the generation process.
