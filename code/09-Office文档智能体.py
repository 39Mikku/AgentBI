import os
from code.models.llm_model import LLMModel
from code.tools.create_dir_open_tool import create_dir_open_tool
from code.tools.office_cli_tool import office_cli_tool
from langchain.agents import create_agent

def create_office_doc_agent(question):
    llm = LLMModel.load_model_once()
    
    prompt = """
        一、你是一个高级文档管理助手。
        二、你拥有两个工具：
            1. create_dir_open_tool: 负责创建并打开本地文件夹。
            2. office_cli_tool: 负责通过终端命令行生成和编辑 Office 文档。
            
        三、officecli 工具极简操作指南：
            你可以利用 office_cli_tool 工具传入命令字符串。请严格按照以下格式执行（注意：文件路径请使用完整的绝对路径，并尽量使用正斜杠 / 避免转义错误）：
            
            【Word 核心操作 (.docx)】
            1. 创建空白文件: officecli create <文件绝对路径>
            2. 写入段落内容: officecli add <文件绝对路径> /body --type paragraph --prop text="你要写入的文本"
            
            【Excel 核心操作 (.xlsx)】
            1. 创建空白文件: officecli create <文件绝对路径>
            2. 写入特定单元格: officecli set <文件绝对路径> /Sheet1/A1 --prop value="你要写入的数据"
            
        四、工作流规划建议：
            当用户提出需求时，请先调用 create_dir_open_tool 确保目标文件夹已创建，然后再使用 office_cli_tool 依次发送创建文件和写入内容的命令。
    """
    
    agent = create_agent(
        model = llm,
        system_prompt = prompt,
        tools = [create_dir_open_tool, office_cli_tool],
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
    q = "在D盘中的 workspace/report 文件夹中，帮我建一个总结文档.docx，并在里面写一些示例文档"
    create_office_doc_agent(q)
