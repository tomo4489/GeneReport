# GeneReport

A prototype web system for generating and managing report data using GPT parsing.

## Setup

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the application:
```bash
uvicorn app.main:app --reload
```

Set `OPENAI_API_KEY` environment variable or configure the key from the settings screen to enable GPT parsing.
The settings page (gear icon) allows editing the Azure OpenAI endpoint/key, reviewing available APIs and managing users.
Swagger UI is available at `/docs` for detailed API documentation.

### API Endpoints

- `GET /api/report-types` - list report names
- `POST /api/report/fields` - list field names of a report (body: `{ "report_name": "name" }`)
- `POST /api/report/questions` - list question prompts of a report (body: `{ "report_name": "name" }`)
- `POST /api/report/record` - create record by report name (body: `{ "report_name": "name", "payload": { ... } }`)
- `POST /api/report/parse` - parse free text using GPT and store a record (body: `{ "report_name": "name", "text": "..." }`)
