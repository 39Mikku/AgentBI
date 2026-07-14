from pydantic import BaseModel, Field

class EmailSchema(BaseModel):
    to: str = Field(..., description="收件人邮箱地址")
    subject: str = Field(..., description="邮件主题")
    content: str = Field(..., description="邮件正文内容")

class EmailResp(BaseModel):
    code: int = Field(..., description="状态码，如200表示成功，400表示失败")
    msg: str = Field(..., description="响应消息，如'验证码发送成功！'")
    data: str = Field(..., description="响应数据，如验证码'908712'等")
    target_email: str = Field(..., description="最终实际发送验证码的目标邮箱地址")
