FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN pip install --upgrade pip

COPY backend/requirements-runtime.txt /tmp/requirements-runtime.txt
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu torch==2.10.0+cpu \
    && pip install -r /tmp/requirements-runtime.txt

COPY backend /app/backend

WORKDIR /app/backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
