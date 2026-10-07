# Tenant Hazard Triage API + demo page. The model itself runs in Ollama on the host (or another container):
#   docker build -t tenant-hazard-triage .
#   docker run -p 8000:8000 -e OLLAMA_HOST=http://host.docker.internal:11434 tenant-hazard-triage
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
COPY web/ web/
COPY data/bank_holidays_england_wales.json data/
ENV TRIAGE_BACKEND=ollama TRIAGE_MODEL=tenant-hazard-triage OLLAMA_HOST=http://host.docker.internal:11434
EXPOSE 8000
USER nobody
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "api:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
