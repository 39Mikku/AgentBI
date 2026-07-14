# 智能体开发要求

本项目规范化开发一个 Python 智能体模块，目录结构存放在 `code` 文件夹中。

## 目录结构要求
```text
code/
├── models/
│   ├── __init__.py
│   └── llm_model.py               # 封装大模型初始化类（单例模式）
├── schemas/
│   ├── __init__.py
│   └── email_schema.py            # 定义大模型的数据响应模型（Pydantic 模式）
├── .env                           # 局部环境变量配置文件
├── 01-调用大模型.py                 # 直接调用大模型基础测试脚本
├── 02-大模型实例化调用.py            # 实例化调用大模型并进行结构化输出测试
├── __init__.py                    # 标记 code 为 Python 包
└── NOTE.md                        # 本要求及开发笔记说明文件
```

## 开发细节要求

### 1. 局部环境变量配置 `.env`
在 `code/.env` 中配置以下环境变量：
- `MODEL_NAME`：大模型名称（结合 `ipynb` 的配置，如 `gpt-4o-mini`）
- `API_KEY`：API 密钥
- `BASE_URL`：API 接口地址
- `EMAIL_HOST`：邮箱服务器地址（如 `smtp.qq.com`）
- `EMAIL_FROM`：发件人邮箱（如 `jaeeun_humg@foxmail.com`）
- `EMAIL_PASSWORD`：邮箱授权码（如 `ygjmkaajzykzbja`）

### 2. 封装大模型 `models/llm_model.py`
使用类 `LLMModel` 封装大模型的加载。通过线程锁（`threading.Lock`）保证模型为**单例模式**（即一次加载，多次调用），实现 `load_model_once(cls)` 方法。

### 3. 数据响应模型 `schemas/email_schema.py`
使用 `pydantic` 的 `BaseModel` 和 `Field` 声明数据响应结构体 `EmailSchema`，包含以下字段：
- `to` (str): 收件人邮箱
- `subject` (str): 邮件主题
- `content` (str): 邮件内容

### 4. 大模型调用脚本
- **`01-调用大模型.py`**：读取 `code/.env`，直接初始化 `ChatOpenAI` 客户端并发送测试对话。
- **`02-大模型实例化调用.py`**：调用 `LLMModel.load_model_once()` 获取模型单例，结合 `EmailSchema` 进行结构化数据输出，提取或生成完整的邮件格式数据。

### 5. 发送邮件工具 `tools/send_email_tool.py`
根据最新需求，使用 `langchain.tools.tool` 装饰器构建一个名为 `send_email` 的发送邮件智能体工具。
要求：
- 输入使用 `EmailSchema`。
- 使用 **Outlook** 邮箱的 SMTP 服务器，端口号为 **587**（需要通过 `starttls()` 开启安全传输）。
- 读取 `.env` 中的 `EMAIL_HOST`、`EMAIL_FROM`、`EMAIL_PASSWORD` 等配置项。
