from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import Unit
from app.models.meals import Allergen, CourseType, Diet, MealSlot, PlanPeriod
from app.schemas.lists import ListDetail


class CuisineOut(BaseModel):
    slug: str
    name: str
    icon: str | None
    is_default: bool
    recipe_count: int


class Nutrition(BaseModel):
    """Kişi başı yaklaşık besin değerleri (tarif için bir porsiyon, plan için günlük ortalama)."""

    kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int


class RecipeSummary(BaseModel):
    id: int
    slug: str
    name: str
    cuisine: str  # slug
    course: str  # gösterim: "Çorba"
    course_type: CourseType
    pairs_with: list[str]  # içecek: uyumlu ana yemekler (slug), boş = hepsi; yan yemek: yalnız bunlar
    meal_slots: list[MealSlot]
    servings: int
    prep_minutes: int
    cook_minutes: int
    description: str
    icon: str | None
    image_url: str | None
    allergens: list[Allergen]
    diets: list[Diet]
    nutrition: Nutrition | None  # kişi başı bir porsiyon, yaklaşık
    like_count: int
    liked: bool  # giriş yapan kullanıcı beğendi mi


class IngredientOut(BaseModel):
    name: str
    amount_text: str
    quantity: Decimal
    unit: Unit
    is_pantry: bool


class MatchedGroup(BaseModel):
    """Malzeme için katalogda bulunan, kullanıcının marketlerinde en uygun ürün grubu."""

    group_id: int
    name: str
    quantity: Decimal | None
    unit: Unit | None
    image_url: str | None
    price: Decimal  # en ucuz marketteki paket fiyatı
    market_id: int | None


class CostLine(BaseModel):
    name: str
    needed_quantity: Decimal  # plan için gereken toplam (temel birim)
    unit: Unit
    is_pantry: bool
    recipes: list[str]  # hangi yemeklerde kullanılıyor
    match: MatchedGroup | None  # None: katalogda / şubelerde bulunamadı
    packages: int  # alınacak paket sayısı
    purchase_cost: Decimal | None  # paketler x fiyat (markette ödenecek)
    used_cost: Decimal | None  # yalnızca kullanılan kısım (porsiyon maliyeti için)
    approximate: bool  # paket birimi tarif birimiyle uyuşmuyor; 1 paket varsayıldı


class CostOut(BaseModel):
    purchase_total: Decimal  # alışveriş tutarı (paketler)
    used_total: Decimal  # yemeklerde kullanılan malzemenin değeri
    per_serving: Decimal | None  # kişi başı bir öğün (çorba, ana yemek, tatlı... hepsi dahil)
    portions: int  # öğün x kişi
    missing_count: int  # fiyatı bulunamayan malzeme sayısı
    include_pantry: bool
    lines: list[CostLine]
    pantry: list[str]  # evde var sayılan (maliyete katılmayan) malzemeler


class RecipeDetail(RecipeSummary):
    steps: list[str]
    ingredients: list[IngredientOut]
    cost: CostOut  # istenen kişi sayısı için


class MealPlanCreate(BaseModel):
    period: PlanPeriod = PlanPeriod.WEEKLY
    cuisine: str | None = Field(default=None, max_length=32)  # boş = varsayılan mutfak (Anadolu)
    servings: int = Field(default=2, ge=1, le=12)
    meal_slots: list[MealSlot] = Field(default_factory=lambda: [MealSlot.DINNER], min_length=1)
    # Öğle/akşam menüsünde olacak türler; çıkarılan tür (ör. çorba) hiç önerilmez
    courses: list[CourseType] = Field(
        default_factory=lambda: [c for c in CourseType if c is not CourseType.SNACK], min_length=1
    )
    start_date: date | None = None  # boş = bugün
    name: str | None = Field(default=None, max_length=120)
    # Yalnız bu diyetlere uyan ve bu alerjenleri içermeyen tarifler önerilir
    diets: list[Diet] = Field(default_factory=list)
    avoid_allergens: list[Allergen] = Field(default_factory=list)


class MealPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    servings: int | None = Field(default=None, ge=1, le=12)


class EntryUpdate(BaseModel):
    """recipe_id boş: bu öğün için başka bir yemek öner."""

    recipe_id: int | None = None


class EntryCreate(BaseModel):
    """Kaldırılan bir yemeği geri ekle; recipe_id boşsa önerilir."""

    day_index: int = Field(ge=0, le=6)
    slot: MealSlot
    course: CourseType
    recipe_id: int | None = None


class MealPlanEntryOut(BaseModel):
    id: int
    day_index: int
    date: date
    slot: MealSlot
    course: CourseType
    recipe: RecipeSummary


class MealPlanSummary(BaseModel):
    id: int
    name: str
    period: PlanPeriod
    cuisine: str
    start_date: date
    days: int
    servings: int
    meal_slots: list[MealSlot]
    courses: list[CourseType]
    diets: list[Diet]
    avoid_allergens: list[Allergen]
    entry_count: int  # öğün sayısı (gün x öğün)
    exported_list_id: int | None
    created_at: datetime


class MealPlanDetail(MealPlanSummary):
    entries: list[MealPlanEntryOut]
    daily_nutrition: Nutrition | None  # kişi başı günlük ortalama, yaklaşık
    cost: CostOut


class ExportRequest(BaseModel):
    """list_id boşsa yeni liste açılır (adı list_name ya da plan adı)."""

    list_id: int | None = None
    list_name: str | None = Field(default=None, min_length=1, max_length=120)
    include_pantry: bool = False


class ExportOut(BaseModel):
    list: ListDetail
    added: int  # listeye eklenen / miktarı artan kalem
    skipped: list[str]  # bulunamadığı için eklenemeyen malzemeler
