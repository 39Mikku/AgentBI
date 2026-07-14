# 将封装的模型导入进来
from code.models.llm_model import LLMModel
# 导入自己的工具类，用来发送邮件
from code.tools.send_email_tool import send_email
# 导入 Agent 构建智能体
from langchain.agents import create_agent    # pip install langchain

# 自定义智能体方法
def send_email_agent(question): # question: 就是用户的指令
    # 第一步: 创建大模型对象
    model = LLMModel.load_model_once()
    
    import os
    # 获取项目根目录路径，兼容不同位置的执行环境
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    persona_path = os.path.join(base_dir, "docs", "叶瞬光.md")
    
    # 动态读取人格配置文件
    with open(persona_path, "r", encoding="utf-8") as f:
        persona_content = f.read()
    
    # 第二步: 提示词工程 (动态读取人格 + 工作流)
    prompt = f'''
        1:角色设定：
{persona_content}

            附加要求：请时刻保持上述角色设定来回复我，称呼我为“小师弟”或“绳匠”。
            
        2:你有一个工具 send_email，用于发送邮件；你需要根据我的信息，提取收件人邮箱、主题和内容，最后发送邮件。
        3:工作流程：
            - 解析用户需求
                1) 提取收件人邮箱、组织邮件内容、邮箱主题（注意：在组织邮件内容时，请务必用上述设定的口吻和语气来代写这封邮件的内容！）。
                2) 检查邮箱是否存在，如果不存在，请用设定中叶瞬光的语气回复“未找到邮箱”；如果邮箱存在，就调用工具发送邮件。
                3) 返回结果：如果邮件发送成功，请用叶瞬光温柔的语气提示“邮件发送成功”，并且向我展示邮件的内容，对吧？
                4) 如果邮件发送失败，也请用叶瞬光的语气提示“邮件发送失败”，并且告诉我错误原因，好不好？
    '''

    # 第三步: 创建智能体
    agent = create_agent(
        model = model,          # 调用大模型，使用大模型进行思考
        system_prompt= prompt,  # 系统提示词
        tools = [send_email],   # 智能体工具
        debug=True,             # 打印日志，在控制台打印日志
    )

    # 第四步: 调用智能体
    response = agent.invoke({
        "messages": [{
            "role":"user",  # 标识用户信息
            "content": question
        }]
    })
    
    print("==========*2")
    print(response)
    print("==========*2")
    if "messages" in response:
        print(response["messages"])

if __name__ == "__main__":
    question = "向elysiareal@qq.com发送一封邮件，这是我的同学，向他介绍一下我，以及你自己"
    send_email_agent(question)
