from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from app.api.access_dependency import get_access_scope
from app.api.dependencies import get_query_service
from app.api.schemas.query_schema import QuerySchema
from app.security.access_scope import AccessScope
from app.services.query_service import QueryService

query_router = APIRouter(tags=["慧经营智能问数"])


@query_router.post("/api/query")
async def query(
    query: QuerySchema,
    access_scope: AccessScope = Depends(get_access_scope),
    query_service: QueryService = Depends(get_query_service),
):
    return StreamingResponse(
        query_service.query(
            query.query,
            access_scope=access_scope,
            max_rows=query.max_rows,
        ),
        media_type="text/event-stream",
    )
