import os
import sys
from dotenv import load_dotenv

# 将项目根目录添加到 python path 中，确保 code 包能正常导入
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.join(current_dir, "..")
if root_dir not in sys.path:
    sys.path.append(root_dir)

from models.llm_model import LLMModel
from schemas.email_schema import EmailSchema
from langchain_core.messages import SystemMessage, HumanMessage

# 加载局部环境变量
load_dotenv(dotenv_path=os.path.join(current_dir, ".env"))

print("====== 02-大模型 实例化及结构化输出测试 ======")

# 1. 实例化/获取模型单例
try:
    llm = LLMModel.load_model_once()
    print("成功实例化并获取大模型单例！")
except Exception as e:
    print(f"获取模型单例失败: {e}")
    sys.exit(1)

# 2. 读取系统提示词 (结合 ipynb 中的配置，从 docs/叶瞬光.md 中读取)
prompt_path = os.path.join(root_dir, "docs", "叶瞬光.md")
if os.path.exists(prompt_path):
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
        print("已成功从 docs/叶瞬光.md 加载系统提示词。")
    except Exception as e:
        print(f"读取提示词文件失败，将使用默认提示词。错误: {e}")
        system_prompt = "你是一个能够根据指示生成结构化邮件信息的智能体。"
else:
    print("未在 docs/ 目录下找到叶瞬光.md，将使用默认提示词。")
    system_prompt = "你是一个能够根据指示生成结构化邮件信息的智能体。"

# 3. 结合 Pydantic 结构化输出
# 用 llm.with_structured_output(EmailSchema) 使大模型以 Pydantic 模型格式响应
try:
    structured_llm = llm.with_structured_output(EmailSchema)
    print("已成功绑定数据响应模型 EmailSchema。")
except Exception as e:
    print(f"绑定结构化输出失败 (可能模型不支持或版本不兼容): {e}")
    structured_llm = None

# 4. 构建输入并进行调用
user_input = "请帮我写一封邮件给同事张三（zhangsan@company.com），告诉他明天的会议改到了下午两点，主题是关于明天会议时间的调整。"

messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=user_input)
]

if structured_llm:
    try:
        print("正在发送请求获取结构化输出...")
        email_data = structured_llm.invoke(messages)
        print("\n================ 大模型返回的结构化数据 (EmailSchema) ================")
        print(f"收件人: {email_data.to}")
        print(f"主题: {email_data.subject}")
        print(f"内容:\n{email_data.content}")
        print("=====================================================================")
    except Exception as e:
        print(f"结构化调用失败: {e}")
else:
    # 降级：直接以普通文本形式调用
    try:
        print("降级方案：正在发送请求获取文本输出...")
        response = llm.invoke(messages)
        print("\n大模型普通文本回复：")
        print(response.content)
    except Exception as e:
        print(f"普通调用失败: {e}")
