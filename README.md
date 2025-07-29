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

Set `OPENAI_API_KEY` environment variable to enable GPT parsing.

### API Endpoints

- `GET /api/report-types` - list report names
- `POST /api/report/{name}/record` - create record by report name

