"""Yemek planlayıcı: mutfaklar, tarifler, malzemeler ve kullanıcıların günlük/haftalık planları.

Mutfak (cuisine) ayrı bir tablodur: yeni bir mutfak (İtalyan, Uzak Doğu...) eklemek için cuisines'e
bir satır ve o mutfağın tariflerini eklemek yeterlidir; plan oluşturma mutfağı slug ile seçer.

Malzemeler ürün gruplarına doğrudan bağlanmaz: katalog marketfiyati'den sürekli değiştiği için her
malzemenin bir arama ifadesi vardır ("kirmizi mercimek") ve maliyet hesabında o an kullanıcının
şubelerinde satılan en uygun ürün grubu bulunur.
"""

import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import Unit, enum_values


class MealSlot(str, enum.Enum):
    BREAKFAST = "kahvalti"
    LUNCH = "ogle"
    SNACK = "ara"  # ara öğün (ikindi)
    DINNER = "aksam"


class CourseType(str, enum.Enum):
    """Bir öğündeki yemek türü. Öğle/akşam: çorba + ana yemek + salata + tatlı + içecek."""

    SOUP = "corba"
    MAIN = "ana"  # ana yemek; kahvaltıda kahvaltılık (menemen)
    SALAD = "salata"
    DESSERT = "tatli"
    DRINK = "icecek"  # hazır içecek; ana yemekle uyumlu olanlar önerilir
    SNACK = "ara"  # ara öğün atıştırmalığı


class PlanPeriod(str, enum.Enum):
    DAILY = "daily"  # 1 gün
    WEEKLY = "weekly"  # 7 gün


class Cuisine(Base):
    __tablename__ = "cuisines"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(32), unique=True)  # "anadolu"
    name: Mapped[str] = mapped_column(String(64))  # "Anadolu (Türk) Mutfağı"
    icon: Mapped[str | None] = mapped_column(String(16))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    recipes: Mapped[list["Recipe"]] = relationship(back_populates="cuisine", order_by="Recipe.id")


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    cuisine_id: Mapped[int] = mapped_column(ForeignKey("cuisines.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    course: Mapped[str] = mapped_column(String(32))  # gösterim: "Çorba", "Ana yemek", "Kahvaltılık"
    course_type: Mapped[CourseType] = mapped_column(
        Enum(CourseType, native_enum=False, length=16, values_callable=enum_values)
    )
    # İçecekler için: hangi ana yemeklerle uyumlu (slug, virgülle); boş = hepsiyle
    pairs_with: Mapped[str | None] = mapped_column(String(255))
    # Hangi öğünlerde önerilebilir: "ogle,aksam"
    meal_slots: Mapped[str] = mapped_column(String(64))
    servings: Mapped[int] = mapped_column(Integer)  # tarifteki miktarlar kaç kişilik
    prep_minutes: Mapped[int] = mapped_column(Integer)
    cook_minutes: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(255))
    steps: Mapped[str] = mapped_column(Text)  # her satır bir adım
    icon: Mapped[str | None] = mapped_column(String(16))
    image_url: Mapped[str | None] = mapped_column(String(1024))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    cuisine: Mapped[Cuisine] = relationship(back_populates="recipes")
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeIngredient.position"
    )

    @property
    def slots(self) -> list[MealSlot]:
        return [MealSlot(s) for s in self.meal_slots.split(",") if s]

    def pairs(self, main: "Recipe | None") -> bool:
        if not self.pairs_with or main is None:
            return True
        return main.slug in self.pairs_with.split(",")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    name: Mapped[str] = mapped_column(String(120))  # "Kırmızı mercimek"
    amount_text: Mapped[str] = mapped_column(String(64))  # tarifteki ölçü: "1 su bardağı"
    # Tarif porsiyonu için temel birimde miktar (1 su bardağı mercimek = 200 g)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unit: Mapped[Unit] = mapped_column(Enum(Unit, native_enum=False, length=8, values_callable=enum_values))
    # Katalogda aranacak ifade ve karışmasın diye elenecek kelimeler ("salca" -> domates salçası değil)
    search_term: Mapped[str] = mapped_column(String(120))
    exclude_terms: Mapped[str | None] = mapped_column(String(255))  # virgülle: "salca,sos,ketcap"
    # Tuz, karabiber gibi evde bulunduğu varsayılanlar; istenirse maliyete/listeye eklenir
    is_pantry: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")


class MealPlan(TimestampMixin, Base):
    __tablename__ = "meal_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    period: Mapped[PlanPeriod] = mapped_column(
        Enum(PlanPeriod, native_enum=False, length=16, values_callable=enum_values)
    )
    cuisine_id: Mapped[int] = mapped_column(ForeignKey("cuisines.id", ondelete="RESTRICT"))
    start_date: Mapped[date] = mapped_column(Date)
    servings: Mapped[int] = mapped_column(Integer)  # kaç kişilik
    meal_slots: Mapped[str] = mapped_column(String(64))  # plandaki öğünler: "ogle,aksam"
    # Öğle/akşam (ve kahvaltı) menüsünde olacak yemek türleri: "corba,ana,salata,tatli,icecek"
    courses: Mapped[str] = mapped_column(String(64))
    # En son aktarıldığı alışveriş listesi (bilgi amaçlı)
    exported_list_id: Mapped[int | None] = mapped_column(ForeignKey("shopping_lists.id", ondelete="SET NULL"))

    cuisine: Mapped[Cuisine] = relationship()
    entries: Mapped[list["MealPlanEntry"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by=lambda: [MealPlanEntry.day_index, MealPlanEntry.slot_order]
    )

    @property
    def slots(self) -> list[MealSlot]:
        return [MealSlot(s) for s in self.meal_slots.split(",") if s]

    @property
    def course_list(self) -> list[CourseType]:
        return [CourseType(c) for c in self.courses.split(",") if c]


class MealPlanEntry(Base):
    __tablename__ = "meal_plan_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("meal_plans.id", ondelete="CASCADE"), index=True)
    day_index: Mapped[int] = mapped_column(Integer)  # 0 = start_date
    slot: Mapped[MealSlot] = mapped_column(
        Enum(MealSlot, native_enum=False, length=16, values_callable=enum_values)
    )
    course: Mapped[CourseType] = mapped_column(
        Enum(CourseType, native_enum=False, length=16, values_callable=enum_values)
    )
    # Sıralama: öğün (kahvaltı < öğle < ara < akşam) x 10 + yemek türü (çorba < ana < salata < tatlı < içecek)
    slot_order: Mapped[int] = mapped_column(Integer)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="RESTRICT"))

    plan: Mapped[MealPlan] = relationship(back_populates="entries")
    recipe: Mapped[Recipe] = relationship()
