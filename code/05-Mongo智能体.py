import os
from code.tools.send_email_tool import send_email
from code.tools.mongo_query_tool import mongo_query
from langchain.agents import create_agent
from code.schemas.product_schema import ProductList
from code.models.llm_model import LLMModel

def sales_data(question):
    # 加载大模型（按照要求，不传入禁用 thinking 模式的 kwargs）
    model = LLMModel.load_model_once()
    
    # 动态获取项目目录并读取人格
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    persona_path = os.path.join(base_dir, "docs", "叶瞬光.md")
    try:
        with open(persona_path, "r", encoding="utf-8") as f:
            persona_content = f.read()
    except Exception:
        persona_content = "你是一个全能的数据助手。"

    prompt = f"""
        【角色设定】
{persona_content}
        附加要求：请始终以该角色设定及语气执行任务。

        你负责查询相关装备/销售数据并发送邮件通知。

        【数据库集合结构】
        1. sales_orders 集合（销售订单表）：
           - id: 订单ID
           - order_date: 订单日期
           - product_name: 产品/装备名称
           - category: 类别
           - quantity: 数量
           - unit_price: 单价
           - total_amount: 总金额
           - customer_city: 城市
           - currency: 货币
           - purchaser: 购买人
           - order_status: 状态
           - order_note: 备注

        2. users 集合（用户表）：
           - username: 用户名
           - email: 邮箱地址

        【工作流程】
        步骤一：利用 mongo_query 独立执行查询（查询条件为合法的双引号JSON格式）
            查询1：在 sales_orders 集合查询装备购买数据。示例（日期范围查询）：{{"order_date": {{"$gte": "2026-01-01", "$lt": "2026-02-01"}}}}
            查询2：在 users 集合查询收件人邮箱。示例：{{"username": "叶瞬光"}}

        步骤二：调用 send_email 发送邮件
            - 收件人：查询到的邮箱
            - 邮件格式要求：列举出购买的装备清单详情（包括单价、数量等）及总消费金额。请结合叶瞬光的身份和语气来撰写，使其生动自然。

        步骤三：提取并返回数据
            完成以上操作后，请将 sales_orders 集合中查询到的详细数据，完整映射为指定的结构化格式(ProductList)并作为最终结果返回。
    """
    
    agent = create_agent(
        model = model,
        system_prompt = prompt,
        tools = [mongo_query, send_email],
        response_format = ProductList,  # 将大模型查询的数据强约束封装到 Python 类
        debug=True
    )
    
    rs = agent.invoke({
        "messages":[{
            "role":"user",
            "content": question
        }]
    })
    
    print("=======================================")
    print(rs["messages"][-1].content)  # 因为是强结构化，最后打印出 Pydantic 对象
    print("=======================================")

if __name__ == "__main__":
    sales_data("看一下我们采购的东西有什么适合作为礼物，然后写一封信给鲁建平，告诉他过段时间我们给他送去")
