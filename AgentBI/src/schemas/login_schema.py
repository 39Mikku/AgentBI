from pydantic import BaseModel, Field

# 定义一个 邮箱 用来接收前端的输入的邮箱地址
class SendCodeSchema(BaseModel):
    email: str = Field(..., description="邮箱地址或者是手机或者是用户名")

# 定义一个Python类，用来接收用户输入的邮箱和验证码
class LoginSchema(BaseModel):
    email: str = Field(..., description="邮箱地址或者是手机或者是用户名")
    code: str = Field(..., description="验证码")
