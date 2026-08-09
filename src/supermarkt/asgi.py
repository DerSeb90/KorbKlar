from fastapi import FastAPI

from .version import __version__
from .web import router


app = FastAPI(title="Supermarkt-Preisvergleich", version=__version__)
app.include_router(router)
