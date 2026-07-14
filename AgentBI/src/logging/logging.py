# 导入Python日志模型
import logging
# 导入日志轮换处理,用于处理日志文件
from logging.handlers import RotatingFileHandler
# 导入Path，用来构建日志保存路径
from pathlib import Path

# 定义一个Python 类，用来保存日志
class Logger:
    # 定义一个私有属性，记录日志
    __loggers = {}
    # 定义一个静态方法，使用类进行调用
    @classmethod
    def get_logger(cls, name = __name__):
        '''
            按照模块名称，保存日志文件
            __name__：当前使用的python 文件/模块名称
        '''
        if not name:
            name = __name__
        if name in cls.__loggers:
            return cls.__loggers[name]
        # 创建文件并且保存文件，构建日志文件保存位置,resolve：获取当前文件的绝对路径，parent:表示返回上一级目录
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        # 将日志文件保存到项目的根目录下的 logs 文件夹
        log_dir = BASE_DIR / "logs"
        # 文件夹不存在时，创建文件夹
        log_dir.mkdir(exist_ok=True)
        # 将日志文件，保存到 logs 文件夹下，保存成一个 app.log 文件
        log_file = log_dir / "app.log"
        # 创建日志对象，使用 name 模块名称，进行命名
        logger = logging.getLogger(name)
        # 设置日志格式：INFO   WARNING  ERROR  DEBUG
        logger.setLevel(logging.INFO)
        # 判断日志处理器是否存在，如果不存在就创建日志处理
        if not logger.handlers:
            # 设置日志格式
            formatter = logging.Formatter(
                # 格式： 时间 -- 日志级别 --- 日志器名称/模块名称 --- 日志信息
                "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
            )
            # 在控制台打印日志信息
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            # 创建日志文件，分割日志文件，设置保存大小
            file_handler = RotatingFileHandler(
                log_file, # 日志存储位置
                maxBytes = 10 * 1024 * 1024,  # 日志大小
                backupCount = 10,
                encoding= "utf-8"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        cls.__loggers[name] = logger
        return logger

