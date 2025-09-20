import secrets

from beartype.claw import beartype_this_package
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from middleware.db_session import DbSessionMiddleWare
beartype_this_package()

def add_middleware(app: FastAPI):
    app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(32))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=2592000
    )
    app.add_middleware(DbSessionMiddleWare)



