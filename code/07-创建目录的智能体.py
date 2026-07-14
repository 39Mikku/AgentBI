from code.tools.create_dir_open_tool import create_dir_open_tool
from code.models.llm_model import LLMModel
from langchain.agents import create_agent

def create_dir(question):
    model = LLMModel.load_model_once()
    
    prompt = """
    一、你是一个电脑控制助手
    二、你有一个工具 create_dir_open_tool 负责创建文件夹并且打开
    """
    
    agent = create_agent(
        model = model,
        system_prompt = prompt,
        tools = [create_dir_open_tool],
        debug=True,
    )
    
    rs = agent.invoke({
        "messages":[{
            "role":"user",
            "content": question
        }]
    })
    
    result = rs["messages"][-1].content
    print(result)

if __name__ == '__main__':
    # q = "请在D盘中创建workspace\\demo文件夹"
    q = "请在D盘中创建workspace\\demo文件夹" # 帮您改为了 C 盘方便测试
    create_dir(q)
