# syntax=docker/dockerfile:1
#
# Platform default AgentCore Runtime container.
#
# AgentCore requires arm64 images. The build is driven from CI with
# `docker buildx build --platform linux/arm64`; locally you can also run
# `docker buildx build --platform linux/arm64 -t mcp-harness .`.
FROM --platform=linux/arm64 public.ecr.aws/docker/library/python:3.13-slim

WORKDIR /app

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .

# AgentCore Runtime invokes the container on port 8080.
EXPOSE 8080

CMD ["python", "app.py"]
