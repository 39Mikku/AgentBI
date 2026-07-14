from pydantic import BaseModel, Field

# 定义一个数据响应的Python类，用于接收大模型返回的信息

class EmailSchema(BaseModel):  # 邮箱工具参数
    # ... 标识必选参数
    to: str = Field(..., description="收件人邮箱")
    subject: str = Field(..., description="邮件主题")
    content: str = Field(..., description="邮件内容")
