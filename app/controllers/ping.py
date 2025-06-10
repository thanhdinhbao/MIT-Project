from fastapi import APIRouter, Request

router = APIRouter()


@router.get(
    "/ping",
    tags=["Health Check"],
    description="Check kết nối đến server",
    response_description="pong",
)
def ping(request: Request) -> str:
    return "pong"
