FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/

ARG APP_HOME="/opt/dscim-cli"

# Run without root permissions.
USER 9876:9876

WORKDIR ${APP_HOME}
COPY . .

# Install with the run extra so dscim and its stack are available.
RUN uv sync --frozen --no-cache --no-dev --extra run --compile-bytecode

ENV PATH="${APP_HOME}/.venv/bin:$PATH"

# Mount configs and data as volumes, e.g.
#   docker run --rm -v ./conf:/mnt/conf:ro -v ./data:/mnt/data \
#       dscim-cli run /mnt/conf/config.yml
ENTRYPOINT ["dscim-cli"]
