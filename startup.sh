#!/usr/bin/env bash
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
python -m app.agent start &
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind=0.0.0.0:${PORT:-8000}
