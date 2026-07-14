from pydantic import BaseModel, Field

class MongoSchema(BaseModel):
    collection: str = Field(..., description="要查询的集合名称")
    query: str = Field(..., description="JSON格式的查询条件")
