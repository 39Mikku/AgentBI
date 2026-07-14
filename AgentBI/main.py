from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from AgentBI.src.logging.logging import Logger
from AgentBI.src.agents.login_agent import LoginAgent
from AgentBI.src.api.api import router

# 创建日志记录
logger = Logger.get_logger(__name__)

# 定义生命周期/创建和销毁
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在 FastAPI中注册 智能体
    app.state.login_agent = LoginAgent()
    logger.info("创建邮件发送智能体的生命周期。。。")
    yield
    logger.info("销毁邮件发送智能体的生命周期。。。")

# 创建 FastAPI 应用
app = FastAPI(lifespan = lifespan)

# 注册api.py中路由
app.include_router(router)

# 增加一个友好的根路径欢迎页面
@app.get("/")
def read_root():
    return {"status": "success", "message": "AgentBI 智能体后端服务已启动！请访问 http://127.0.0.1:8000/docs 进行接口测试。"}

if __name__ == "__main__":
    # 使用 uvicorn 启动服务端应用
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
