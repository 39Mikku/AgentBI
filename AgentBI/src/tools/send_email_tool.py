import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from langchain_core.tools import tool
from AgentBI.src.schemas.email_schema import EmailSchema

# 读取配置文件信息
load_dotenv()

# 定义Python方法
@tool("send_email", args_schema=EmailSchema)  # tool("智能体工具名称", args="大模型响应数据")
def send_email(to: str, subject: str, content: str) -> str:  # 将Python方法，注册为智能体工具，需要使用 @tool
    """
    邮件发送
    """
    # 创建邮箱对象
    try:
        msg = MIMEText(content)
        # 设置收件人邮箱
        msg["To"] = to
        # 设置发件人
        msg["From"] = os.getenv("EMAIL_FROM")
        # 设置邮箱主题
        msg["Subject"] = subject

        # 设置 smtp 服务器对象 (QQ邮箱 SMTP 配置，端口 465)
        smtp = smtplib.SMTP_SSL(os.getenv("EMAIL_HOST"), port=465)
        # 登录邮箱
        smtp.login(os.getenv("EMAIL_FROM"), os.getenv("EMAIL_PASSWORD"))
        # 发送邮件
        smtp.sendmail(os.getenv("EMAIL_FROM"), to, msg.as_string())
        smtp.quit()  # 退出登录
        return "邮件发送成功！"
    except Exception as e:
        return f"邮件发送失败: {str(e)}"
