FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

ENV SEARXNG_URL=http://host.docker.internal:8888
ENV UVICORN_NO_HOST_CHECK=1

EXPOSE 8000

ENTRYPOINT ["python", "src/searxng_mcp_server.py"]
