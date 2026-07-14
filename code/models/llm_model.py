# 导入 langchain 用来创建大模型
from langchain_openai import ChatOpenAI
# 导入 dotenv 包用于获取环境变量文件的 配置信息
from dotenv import load_dotenv
import os
import threading  # 创建线程锁，让模型只加载一次

# 加载系统变量
# 保证不论在哪个路径下运行，都能正确加载 code/.env
current_dir = os.path.dirname(os.path.abspath(__file__))
local_env = os.path.join(current_dir, "..", ".env")
if os.path.exists(local_env):
    load_dotenv(dotenv_path=local_env)
else:
    load_dotenv()

# 使用 Python 类进行封装，使用格式： class 类名
class LLMModel:
    # 定义一类变量，用来存储 大模型
    _model = None
    
    # 创建一个线程锁
    _lock = threading.Lock()
    
    # 定义一Python方法，用于构建大模型
    # Python定义方法的格式： def 方法名称(零个或多个行为变量):
    @classmethod
    def load_model_once(cls, **kwargs):  # cls : 标识当前类的方法 --> LLMModel
        if cls._model is None:
            with cls._lock:
                if cls._model is None:
                    model_config = {
                        "model": os.getenv("MODEL_NAME"),
                        "api_key": os.getenv("API_KEY"),
                        "base_url": os.getenv("BASE_URL"),
                        "streaming": True
                    }
                    model_config.update(kwargs) # 添加其它参数
                    cls._model = ChatOpenAI(**model_config)
        return cls._model
