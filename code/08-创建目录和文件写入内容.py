from code.models.llm_model import LLMModel
from code.tools.create_dir_open_tool import create_dir_open_tool
from code.tools.create_file_open_tool import create_file_open_tool
from langchain.agents import create_agent

def create_dir_file_agent(question):
    llm = LLMModel.load_model_once()
    
    prompt = """
        一、你是一个强大的电脑控制与文件管理助手。
        二、你拥有 create_dir_open_tool (负责创建文件夹并打开) 和 create_file_open_tool (负责创建文件、写入内容并用记事本打开) 两个工具。
        三、请根据用户的需求，自动规划工作流。例如：如果用户要求在某目录下写文件，你需要先判断并调用创建文件夹工具建立该目录，然后再调用写入文件工具。
    """
    
    agent = create_agent(
        model = llm,
        system_prompt = prompt,
        tools = [create_dir_open_tool, create_file_open_tool],
        debug=True,
    )
    
    rs = agent.invoke({
        "messages":[{
            "role":"user",
            "content":question
        }]
    })
    
    result = rs["messages"][-1].content
    print(result)

if __name__ == '__main__':
    # q = "在D盘中的workspace\\demo\\文件夹中，创建一个文本文件，里面帮我写一封情书！"
    # 为了方便您的系统环境测试，改为了 C 盘
    q = "在C盘中的workspace\\demo文件夹中，创建一个文本文件，里面帮我写一封情书！"
    create_dir_file_agent(q)
