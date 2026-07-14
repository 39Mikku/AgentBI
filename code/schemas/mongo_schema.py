from pydantic import BaseModel, Field

# 用来接收大模型生成的 MongoDB 查询
class MongoSchema(BaseModel):
    collection: str = Field(..., description="要查询的集合(Collection)名称")
    query: str = Field(..., description="MongoDB的查询条件，必须是合法的JSON字符串，例如 '{\"name\": \"Alice\"}'。如果查询全部请传入 '{}'")
