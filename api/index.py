"""Vercel entrypoint. Wraps the existing reconciler.api FastAPI app --
does not redefine any route or logic, only adds the one route Vercel
needs that plain `uvicorn reconciler.api:app` doesn't: serving the static
frontend at "/". Every other path (/batches, /batches/{id}/run, ...) is
handled unchanged by the app imported below.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.responses import FileResponse

from reconciler.api import app

_FRONTEND_INDEX = os.path.join(
  os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "index.html")


@app.get("/")
def serve_frontend():
  return FileResponse(_FRONTEND_INDEX)
