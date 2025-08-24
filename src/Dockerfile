# Dockerfile
FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка Poetry
RUN pip install --upgrade pip
RUN pip install poetry==1.8.2

# Копируем зависимости
COPY pyproject.toml poetry.lock ./

# Устанавливаем зависимости проекта
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main

# Копируем проект
COPY . .