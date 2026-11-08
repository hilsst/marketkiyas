"""Tarif arama: GET /api/recipes?q=..."""

from sqlalchemy import text


async def _names(client, q, **extra):
    r = await client.get("/api/recipes", params={"q": q, **extra})
    assert r.status_code == 200
    return [x["name"] for x in r.json()]


async def test_search_is_diacritic_and_case_insensitive(client):
    for q in ("kofte", "KÖFTE", "Köfte", "köfte"):
        names = await _names(client, q)
        assert names, q
        assert any("köfte" in n.lower() for n in names)
    assert await _names(client, "kofte") == await _names(client, "Köfte")


async def test_name_matches_come_before_ingredient_only_matches(client):
    names = await _names(client, "kofte")
    flags = ["köfte" in n.lower() for n in names]
    assert flags[0]
    assert flags == sorted(flags, reverse=True)  # önce ad eşleşmeleri, sonra yalnız malzemede geçenler


async def test_search_finds_by_ingredient(client):
    names = await _names(client, "nohut")
    assert names
    assert len(names) >= len([n for n in names if "nohut" in n.lower()])


async def test_multiple_words_must_all_match(client):
    both = await _names(client, "mercimek corba")
    assert both and "mercimek" in both[0].lower()
    assert len(both) <= len(await _names(client, "mercimek"))


async def test_no_match_returns_empty_and_blank_query_returns_all(client):
    assert await _names(client, "zzzxqy") == []
    assert len(await _names(client, "")) == len(await _names(client, " "))
    assert len(await _names(client, "")) > 100


async def test_filters_combine_with_search(client):
    allm = await _names(client, "tavuk")
    vegan = await _names(client, "tavuk", diet="vegan")
    assert len(vegan) < len(allm)


async def test_search_uses_trigram_index(db):
    await db.execute(text("SET enable_seqscan = off"))
    plan = "\n".join(r[0] for r in await db.execute(
        text("EXPLAIN SELECT id FROM recipes WHERE search_text LIKE '%kofte%'")))
    assert "ix_recipes_search_text_trgm" in plan


async def test_special_characters_are_harmless(client):
    for q in ("%", "_", "'; drop table recipes;--", "köfte%"):
        r = await client.get("/api/recipes", params={"q": q})
        assert r.status_code == 200
    assert len(await _names(client, "")) > 100
