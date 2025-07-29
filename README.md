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
- `GET /api/report/{name}/fields` - list field names of the specified report
- `POST /api/report/{name}/record` - create record by report name
- `POST /api/report/{name}/parse` - parse free text using GPT and store a record
