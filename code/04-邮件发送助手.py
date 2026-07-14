import os
from code.models.llm_model import LLMModel
from code.tools.send_email_tool import send_email
from code.tools.mongo_query_tool import mongo_query
from langchain.agents import create_agent

def email_send_assistant(question):
    # 1.调用大模型
    model = LLMModel.load_model_once()
    
    # 获取项目根目录，动态读取人格
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    persona_path = os.path.join(base_dir, "docs", "叶瞬光.md")
    try:
        with open(persona_path, "r", encoding="utf-8") as f:
            persona_content = f.read()
    except Exception:
        persona_content = "你是一个全能的助手。"

    # 2. 系统提示词
    prompt = f"""
        1:角色设定：
{persona_content}
            附加要求：请时刻保持上述角色设定来回复我，称呼我为“小师弟”或“绳匠”。
            
        2:你拥有两个工具：
            - mongo_query: 用于查询 MongoDB 数据库。需要提取集合名称(collection)和查询条件(合法的JSON字符串)。若未指定，默认查询 users 集合。
            - send_email: 用于发送邮件。需要提取收件人邮箱、主题和邮件内容。
        3:工作流程：
            - 解析用户需求，判断是需要查询数据库、还是发送邮件，或是两者都要。
            - 若需查询数据库，请明确集合名称（默认 users），并构造合法的JSON字符串查询条件（例如查丁翔：{{"username": "丁翔"}}），然后调用 mongo_query 工具。
            - 若需发送邮件，请提取邮箱等相关参数调用 send_email 工具。
            - 综合工具返回的结果，用叶瞬光的语气向我进行最终的总结与回复。
    """
    
    # 3.创建智能体
    agent = create_agent(
        model = model,
        system_prompt = prompt,
        tools = [send_email, mongo_query],
        debug=True,
    )
    
    # 调用智能体
    rs = agent.invoke({
        "messages":[{
            "role":"user",
            "content": question
        }]
    })
    
    result = rs["messages"][-1].content
    print(result)

if __name__ == "__main__":
    question = "小光师姐，发一封信给丁翔，问他下周跟不跟我们一起去逛街"
    email_send_assistant(question)
