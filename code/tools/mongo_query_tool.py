from langchain.tools import tool
from dotenv import load_dotenv
import os
import json
from code.schemas.mongo_schema import MongoSchema
import pymongo # pip install pymongo

load_dotenv()

@tool("mongo_query", args_schema=MongoSchema)
def mongo_query(collection: str, query: str) -> str:
    """
    执行 MongoDB 查询
    """
    try:
        # 从环境变量获取连接信息
        uri = os.getenv("MONGO_URI")
        db_name = os.getenv("MONGO_DATABASE", "chat_bi")
        
        if not uri:
            return "数据库连接失败: 未在 .env 中配置 MONGO_URI 环境变量"
            
        # 创建连接对象
        client = pymongo.MongoClient(uri)
        db = client[db_name]
        col = db[collection]
        print(f"成功连接至数据库: {db_name}，游标集合: {collection}")
        
        # 解析JSON字符串为字典
        try:
            query_dict = json.loads(query)
        except json.JSONDecodeError:
            return "查询条件解析失败，请确保大模型生成的是合法的 JSON 字符串。"
        
        print(f"执行 MongoDB 查询: {query_dict}")
        
        # 执行查询，默认去掉 _id，避免返回的 ObjectId 对象导致序列化报错
        result = list(col.find(query_dict, {"_id": 0}))
        
        print("数据库查询结果:", result)
        client.close()
        return str(result)
        
    except Exception as e:
        return f"数据库连接或查询失败: {str(e)}"

if __name__ == "__main__":
    # 测试一下工具是否能正常运行
    print(mongo_query.invoke({"collection": "users", "query": "{}"}))
