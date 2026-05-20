#!/usr/bin/env bash
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

if [ -n "$WEBSITE_HOSTNAME" ]; then
  export DATABASE_URL="sqlite:////home/data/video_interview.db"
  mkdir -p /home/data
fi

python -m app.agent start &
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers=1 --bind=0.0.0.0:${PORT:-8000}
