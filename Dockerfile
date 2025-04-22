# Stage for building the Java-based NoiseModelling library
FROM maven:3.9.9-eclipse-temurin-11-focal AS java-builder

WORKDIR /build

ENV CACHE_DIR=/build/cache

RUN --mount=type=cache,target=$CACHE_DIR apt-get update && apt-get install -y --no-install-recommends \
    make \
    unzip \
    && rm -rf /var/lib/apt/lists/*

COPY Makefile .env ./
# Copy the NoiseModelling source code
RUN git clone --depth 1 --branch v4.0.5 https://github.com/Universite-Gustave-Eiffel/NoiseModelling.git NoiseModelling \
    && cd NoiseModelling && git verify-commit HEAD \
# Build the NoiseModelling library
    && cd .. && make check-java && make dist


FROM python:3.12-bookworm AS base

ENV CACHE_DIR=/app/cache

WORKDIR /app

RUN --mount=type=cache,target=$CACHE_DIR apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install poetry

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/app/poetry_cache

COPY pyproject.toml poetry.lock ./
RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without=dev --no-root

COPY src ./src
RUN touch README.md \
    && poetry build \
    && /app/.venv/bin/python -m pip install dist/*.whl --no-deps

FROM python:3.12-slim-bookworm AS runtime

ARG USER_UID=1000
ARG USERNAME=pythonuser
ARG USER_GID=2000
ARG SOURCE_COMMIT

LABEL maintainer="Urban Data Analytics" name="analytics/mobilitatsmonitor_dashboard" source_commit=$SOURCE_COMMIT

# add user and group
RUN groupadd --gid $USER_GID $USERNAME && \
    useradd --create-home --no-log-init --gid $USER_GID --uid $USER_UID --shell /bin/bash $USERNAME && \
    chown -R $USERNAME:$USERNAME /home/$USERNAME /usr/local/lib /usr/local/bin

# Install Java runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jdk \
    && rm -rf /var/lib/apt/lists/*

USER $USERNAME
WORKDIR /app

# Set Java environment variables
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PATH="$JAVA_HOME/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv \
    # needed to find and register classes within the worker
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:${PYTHONPATH}" \
    # needed to find the Java classes
    JAVA_LIB_DIR="/app/dist/lib"

COPY --from=base \
    --chmod=0755 \
    --chown=$USERNAME:$USERNAME \
    ${VIRTUAL_ENV} ./.venv

# Copy the built NoiseModelling dist folder from the java-builder stage
COPY --from=java-builder \
    --chmod=0755 \
    --chown=$USERNAME:$USERNAME \
    /build/dist ./dist

COPY --chmod=0755 \
    --chown=$USERNAME:$USERNAME \
    app.py app.py

ENV PYTHONUNBUFFERED 1
