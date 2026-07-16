import uuid

from fastapi import FastAPI, Request


from app.api.routers.query_router import query_router
from app.core.context import set_req_id
from app.core.lifespan import lifespan


app = FastAPI(lifespan=lifespan)
app.include_router(query_router)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    set_req_id(str(uuid.uuid4()))
    response = await call_next(request)

    return response
