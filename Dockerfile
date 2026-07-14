FROM python:3.11-slim

# Arabic-capable fonts for server-side rendering (survey_dashboard.py builds
# PNG/PPTX dashboards from Arabic survey text via matplotlib). Without these,
# the base image has no font that can render Arabic glyphs at all.
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-naskh-arabic \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/
COPY ["MECE Program Report Model.docx", "MECE Program Report Model.docx"]

WORKDIR /app/backend
EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
