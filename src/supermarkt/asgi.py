from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .authz import AccessControlMiddleware
from .ui import STATIC_DIR
from .version import __version__
from .web import router


app = FastAPI(title="KorbKlar", version=__version__)
# Added first so it wraps every route, including the static mount.
app.add_middleware(AccessControlMiddleware)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(router)
