import enum


class Unit(str, enum.Enum):
    """Normalize edilmiş temel birim. 1L -> 1000 ml, 1kg -> 1000 g."""

    ML = "ml"
    G = "g"
    PIECE = "adet"


class PlanType(str, enum.Enum):
    """Liste detayındaki optimizasyon sekmeleri."""

    SINGLE_MARKET = "single_market"  # Tek Market
    COMBINATION = "combination"  # Kombinasyon (seçili markalarla)
    OPPORTUNIST = "opportunist"  # Fırsatçı 🚀 (marka farketmez)
    NEARBY = "nearby"  # Yakın Market: en yakın şubeden, başka yerde belirgin ucuzsa orada


class ListStatus(str, enum.Enum):
    ACTIVE = "active"
    SHOPPING = "shopping"  # plan uygulandı, Alışveriş Modu
    COMPLETED = "completed"  # "Alışverişi Bitir" sonrası kilitli; "Tekrar kullan" ACTIVE'e döndürür


def enum_values(e: type[enum.Enum]) -> list[str]:
    return [m.value for m in e]
