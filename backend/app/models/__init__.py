# Alembic autogenerate'in tüm tabloları görmesi için hepsini burada içe aktar.
from app.db.base import Base
from app.models.catalog import Category, Market, PriceHistory, Product
from app.models.enums import ListStatus, PlanType, Unit
from app.models.matching import GroupMember, ProductGroup
from app.models.savings import SavingsRecord
from app.models.shopping import ShoppingList, ShoppingListItem
from app.models.user import User

__all__ = [
    "Base",
    "Category",
    "GroupMember",
    "ListStatus",
    "Market",
    "PlanType",
    "PriceHistory",
    "Product",
    "ProductGroup",
    "SavingsRecord",
    "ShoppingList",
    "ShoppingListItem",
    "Unit",
    "User",
]
