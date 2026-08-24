FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system app && useradd --system --gid app --home-dir /nonexistent --shell /usr/sbin/nologin app
WORKDIR /app
COPY controller/remediator.py controller/policy.yaml controller/requirements.txt ./
RUN touch /app/audit.jsonl && chown -R app:app /app
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)" || exit 1
CMD ["python", "remediator.py"]
