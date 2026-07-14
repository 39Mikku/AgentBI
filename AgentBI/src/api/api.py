from fastapi import APIRouter, Request
from AgentBI.src.schemas.login_schema import SendCodeSchema, LoginSchema
from AgentBI.src.logging.logging import Logger
import redis # 安装redis驱动，用于连接缓存数据库:  pip install redis

# 创建redis数据库连接
conn = redis.Redis(host="127.0.0.1", port=6379, db=0)

# 创建 FastAPI 访问路由
router = APIRouter()

# 创建/实例化日志处理器
logger = Logger.get_logger(__name__)

# 定义登录接口的验证码发送按钮，请求方式 POST，send_code
@router.post("/send_code")
def send_code(request: Request, args: SendCodeSchema):
    agent = request.app.state.login_agent
    # 调用 智能体中 answer 方法，执行发送邮件和查询数据
    resp = agent.answer(args.email) # 获取 SendCodeSchema 类中的变量值，前端的值
    
    # 只有当大模型成功返回，并且结果里确实包含 data 时，才去写入 Redis
    if resp.get("code") == 200 and "data" in resp:
        # 拼接键值对，将验证码缓存到redis数据库中（以用户输入的原始标识为键）
        conn.set(f"login:code:{args.email}", resp["data"], ex=300) 
        
        # 双重绑定：如果大模型返回了真实的查库邮箱地址，则顺便给邮箱也存一份
        target_email = resp.get("target_email")
        if target_email and target_email != args.email:
            conn.set(f"login:code:{target_email}", resp["data"], ex=300)
            
        logger.info(f"验证码发送成功: {args.email} / {target_email}")
    else:
        logger.error(f"验证码发送失败，未存入Redis: {resp.get('msg')}")
        
    # 安全返回，避免 KeyError
    return {"code": resp.get("code", 500), "msg": resp.get("msg", "未知错误")}

# 定义一个接口方法，用于执行登录功能（直接获取用户输入的邮箱和验证码，获取数据库里面的验证码比对）
@router.post("/login")
def login(args: LoginSchema):
    try:
        # 获取数据库中的验证码（通过key获取）
        code_bytes = conn.get(f"login:code:{args.email}")
        # 判断验证码是否存在
        if code_bytes and code_bytes.decode() == args.code:
            logger.info("验证码登录成功！")
            return {"code": 200, "msg": "正在登录！"}
        else:
            return {"code": 500, "msg": "验证码输入错误或过期！"}
    except Exception as e:
        logger.error("Redis服务器错误！")
        return {"code": 400, "msg": "服务器错误！"}
