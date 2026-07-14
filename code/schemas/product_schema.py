from pydantic import BaseModel, Field
from typing import List

class ProductSchema(BaseModel):
    id: int = Field(..., description="订单ID")
    order_date: str = Field(..., description="订单日期时间")
    product_name: str = Field(..., description="商品名称")
    category: str = Field(..., description="商品类别")
    quantity: int = Field(..., description="商品数量")
    unit_price: float = Field(..., description="商品单价")
    total_amount: float = Field(..., description="商品总价格")
    customer_city: str = Field(..., description="客户所在城市")
    currency: str = Field(..., description="货币种类")
    purchaser: str = Field(..., description="购买人")
    order_status: str = Field(..., description="订单状态")
    order_note: str = Field(..., description="订单备注")

class ProductList(BaseModel):
    product_list: List[ProductSchema] = Field(..., description="商品列表")
