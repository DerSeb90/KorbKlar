import mimetypes

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .authz import AccessControlMiddleware
from .ui import STATIC_DIR
from .version import __version__
from .web import router


# The shopping basket is an ES module importing a .mjs file. Where the
# platform has no mapping for it, it is served as text/plain and the browser
# refuses the module outright, taking the whole basket down.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")

app = FastAPI(title="KorbKlar", version=__version__)
# Added first so it wraps every route, including the static mount.
app.add_middleware(AccessControlMiddleware)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(router)
