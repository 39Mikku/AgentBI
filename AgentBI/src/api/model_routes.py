from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.model_route_schema import ModelRole, ModelRouteResponse, ModelRouteUpdate

router = APIRouter(prefix="/model-routes", tags=["model-routes"])


@router.get("", response_model=list[ModelRouteResponse])
def list_model_routes(request: Request, user_id: str = Query(min_length=1)):
    return get_chat_repository(request).list_model_routes(user_id)


@router.put("/{role}", response_model=ModelRouteResponse)
def save_model_route(role: ModelRole, request: Request, payload: ModelRouteUpdate, user_id: str = Query(min_length=1)):
    repository = get_chat_repository(request)
    if not repository.get_provider(payload.provider_id):
        raise HTTPException(status_code=404, detail="模型提供商不存在")
    return repository.save_model_route(user_id, role, payload.model_dump())


@router.delete("/{role}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model_route(role: ModelRole, request: Request, user_id: str = Query(min_length=1)):
    get_chat_repository(request).delete_model_route(user_id, role)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

