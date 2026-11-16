FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 HF_HOME=/var/cache/huggingface PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY projects/scholarlysources/paper_search/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY projects/scholarlysources/paper_search ./paper_search
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --retries=10 --start-period=180s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"
CMD ["python", "-m", "uvicorn", "src.api:app", "--app-dir", "/app/paper_search", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
