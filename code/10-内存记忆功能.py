import os
from code.models.llm_model import LLMModel
from code.tools.send_email_tool import send_email
from code.tools.mongo_query_tool import mongo_query
from langchain.agents import create_agent

# 记忆功能：langgraph 较新版本中通常叫 MemorySaver，图片中为 InMemorySaver，这里做个兼容别名
try:
    from langgraph.checkpoint.memory import MemorySaver as InMemorySaver
except ImportError:
    from langgraph.checkpoint.memory import InMemorySaver

# 1. 实例化模型
model = LLMModel.load_model_once()

# 2. 动态加载人设
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
persona_path = os.path.join(base_dir, "docs", "叶瞬光.md")
try:
    with open(persona_path, "r", encoding="utf-8") as f:
        persona_content = f.read()
except Exception:
    persona_content = "你是一个全能的助手。"

prompt = f"""
    【角色设定】
{persona_content}
    附加要求：请时刻保持上述角色设定来回复我。
    
    你是一个拥有对话记忆能力的智能体，你随时记得上下文信息。
    当需要查询用户信息或邮箱时，请去 users 集合中根据 username 字段进行查询。
"""

# 3. 创建 Agent，最核心的变化是加入了 checkpointer
agent = create_agent(
    model = model,
    system_prompt = prompt,
    tools = [mongo_query, send_email],
    checkpointer = InMemorySaver(),  # 为大模型添加内存记忆功能
    debug = True,
)

def test(question):
    # 核心：必须传入 config 指定 thread_id，大模型才能根据 ID 匹配历史上下文
    rs = agent.invoke(
        {"messages":[{"role":"user", "content": question}]},
        config={"configurable": {"thread_id": "10"}}
    )
    return rs["messages"][-1].content

if __name__ == "__main__":
    # 测试一系列问题，验证上下文记忆
    questions = [
        "我叫骑士，好久不见了小师姐——",
        "我是谁？你还记得我的名字吗？",
        "帮我发一封问候信给丁翔，问他下周要不要一起去逛街",
        "刚才发送了什么来着？"
    ]
    for i, d in enumerate(questions): # i 表示序列， d 表示元素值
        print(f"第{i+1}个问题: {d}")
        print(test(d))
        print("=======================================")
