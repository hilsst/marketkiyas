import enum


class Unit(str, enum.Enum):
    """Normalize edilmiş temel birim. 1L -> 1000 ml, 1kg -> 1000 g."""

    ML = "ml"
    G = "g"
    PIECE = "adet"


class PlanType(str, enum.Enum):
    """Liste detayındaki 3 optimizasyon sekmesi."""

    SINGLE_MARKET = "single_market"  # Tek Market
    COMBINATION = "combination"  # Kombinasyon (seçili markalarla)
    OPPORTUNIST = "opportunist"  # Fırsatçı 🚀 (marka farketmez)


class ListStatus(str, enum.Enum):
    ACTIVE = "active"
    SHOPPING = "shopping"  # plan uygulandı, Alışveriş Modu
    COMPLETED = "completed"  # "Alışverişi Bitir" dendi


def enum_values(e: type[enum.Enum]) -> list[str]:
    return [m.value for m in e]
