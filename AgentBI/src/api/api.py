from typing import Any

from fastapi import APIRouter, Request

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.logging.logging import Logger
from AgentBI.src.schemas.login_schema import LoginSchema, SendCodeSchema
from AgentBI.src.services.login_service import LoginService

router = APIRouter()
logger = Logger.get_logger(__name__)


def login_response(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": 200,
        "msg": "正在登录",
        "data": {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "avatar_data_url": user.get("avatar_data_url"),
        },
    }


@router.post("/send_code")
def send_code(request: Request, args: SendCodeSchema):
    try:
        result = LoginService(get_chat_repository(request)).send_code(args.email)
        logger.info("登录验证码已发送: %s", result["target_email"])
        return {"code": 200, "msg": "验证码已发送", **result}
    except (ValueError, RuntimeError) as error:
        logger.error("发送登录验证码失败: %s", error)
        return {"code": 400, "msg": str(error)}


@router.post("/login")
def login(request: Request, args: LoginSchema):
    user = LoginService(get_chat_repository(request)).login(args.email, args.code)
    if not user:
        return {"code": 500, "msg": "验证码错误或已过期"}
    logger.info("用户登录成功: %s", user["user_id"])
    return login_response(user)
