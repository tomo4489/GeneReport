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
- `POST /api/report/questions` - list question prompts or prompt text with mode (body: `{ "report_name": "name" }`)
  - struct mode: `{ "mode": "struct", "questions": [{"field":...,"question":...,"type":...}] }`
  - smart mode: `{ "mode": "smart", "prompt": "...", "fields": [...] }`
- `POST /api/report/record` - create a record in struct mode using `multipart/form-data`
  - send `report_name` plus field values; attach image/video files (up to 100MB each)
- `POST /api/report/parse` - submit free text for a smart-mode report to parse and store (body: `{ "report_name": "name", "text": "..." }`)

The web UI also provides an **AIチャット** tab to talk directly with GPT using the configured OpenAI settings.
