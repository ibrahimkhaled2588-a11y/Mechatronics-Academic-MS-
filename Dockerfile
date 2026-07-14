FROM python:3.11-slim

# Arabic-capable fonts for server-side rendering (survey_dashboard.py builds
# PNG/PPTX dashboards from Arabic survey text via matplotlib). Without these,
# the base image has no font that can render Arabic glyphs at all.
# fonts-noto is the broad meta-package (covers Arabic + everything else) --
# more reliably present across base-image repo mirrors than the narrower
# fonts-noto-naskh-arabic package name, which failed to resolve on Fly's builder.
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# matplotlib builds a font cache on first use; point it at a directory
# that's always writable regardless of the container's user, rather than
# relying on a home directory that may not exist/be writable.
ENV MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/
COPY ["MECE Program Report Model.docx", "MECE Program Report Model.docx"]

WORKDIR /app/backend
EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
