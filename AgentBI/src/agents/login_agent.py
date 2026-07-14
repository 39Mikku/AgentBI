from AgentBI.src.tools.mongo_query_tool import mongo_query
from AgentBI.src.tools.send_email_tool import send_email
from langchain.agents import create_agent
from AgentBI.src.models.llm_model import LLMModel
from AgentBI.src.logging.logging import Logger
from AgentBI.src.schemas.email_schema import EmailResp

# 初始化日志文件
logger = Logger.get_logger(__name__)

# 定义一个智能体类，用来执行验证码登录功能
class LoginAgent:
    # 初始化器/构造函数
    def __init__(self):
        # 初始化记录日志文件
        logger.info("初始化登录邮件发送的智能体")
        # 初始化，加载大模型
        self.model = LLMModel.load_model_once()
        # 初始化，定义工具类，将工具类复制给一个变量
        self.tools = [mongo_query, send_email]
        # 初始化智能体
        self.agent = self.init_agent()

    # 定义一个初始化方法，用来构建 智能体
    def init_agent(self):
        prompt = '''
        你是一个登录验证助手，负责为用户查询邮箱地址并发送验证码。
        
        【工作流程】
        1. 首先，使用 mongo_query 工具去 users 集合中根据 username 查询对应用户的邮箱。
        2. 随机生成一个 6 位数字的登录验证码。
        3. 调用 send_email 工具将生成的验证码发送给该邮箱。
        
        【严格格式要求】
        你的最终输出必须严格符合 EmailResp 的强类型结构，不要返回任何额外解释！
        '''
        self.agent = create_agent(
            model = self.model,
            tools = self.tools,
            system_prompt = prompt,
            response_format = EmailResp, # 表示大模型封装的信息（{"code": 200, "msg": "验证码发送成功！", "data": "908712"}）
            debug = True,
        )
        return self.agent

    # 定义一个方法，供API进行方法
    def answer(self, question):
        try:
            # 日志记录
            logger.info(f"开始处理用户内容: {question}")
            # 执行智能体发送验证码邮件
            resp = self.agent.invoke(
                {"messages":[{"role":"user", "content": question}]}
            )
            # 解析处理结果
            answer = resp["structured_response"].model_dump()
            print("====================")
            print(resp["structured_response"])
            print(answer)
            print("====================")
            logger.info(f"智能体最终的回复结果: {answer}")
            return answer
        except Exception as e:
            logger.error(f"处理问题时报错: {str(e)}")
            return {
                "code": 400,
                "msg": f"邮件发送失败: {str(e)}"
            }

if __name__ == "__main__":
    agent = LoginAgent()
    print(agent.answer("给鲁建平发送登录验证码"))
