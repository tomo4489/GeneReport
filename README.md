# GeneReport

A prototype web system for generating and managing report data using GPT parsing.

## Setup

Install dependencies:
```bash
pip install fastapi uvicorn sqlalchemy jinja2 pandas openpyxl python-multipart openai
```

Run the application:
```bash
uvicorn app.main:app --reload
```

Set `OPENAI_API_KEY` environment variable to enable GPT parsing.
