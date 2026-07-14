import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# 加载当前目录下的 .env 环境变量
current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(current_dir, ".env"))

print("====== 01-调用大模型 基础测试 ======")
print("API Base:", os.getenv("BASE_URL"))
print("Model Name:", os.getenv("MODEL_NAME"))

# 初始化 ChatOpenAI 客户端
llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME"),
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL")
)

# 构建消息列表
messages = [
    SystemMessage(content="你是一个简单的测试助手。"),
    HumanMessage(content="你好！如果你能收到这条消息，请回复'连接成功'！")
]

# 发送请求并打印结果
try:
    print("正在调用大模型，请稍候...")
    response = llm.invoke(messages)
    print("\n大模型回复内容：")
    print(response.content)
except Exception as e:
    print(f"\n大模型调用失败，错误详情: {e}")
