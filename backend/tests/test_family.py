from decimal import Decimal as D

from tests.test_lists_api import catalog  # noqa: F401  (fixture)


async def _user(client, email):
    r = await client.post("/api/auth/register", json={"email": email, "password": "gizli-sifre-123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_family_members_share_all_lists_without_code(client, catalog):  # noqa: F811
    _, ids = catalog
    kemal = await _user(client, "kemal@example.com")
    esi = await _user(client, "esi@example.com")
    lid = (await client.post("/api/lists", json={"name": "HaftalÄ±k"}, headers=kemal)).json()["id"]
    assert (await client.get(f"/api/lists/{lid}", headers=esi)).status_code == 404

    r = await client.post("/api/family", json={"name": "YÄ±lmazlar"}, headers=kemal)
    assert r.status_code == 201
    fam = r.json()["family"]
    assert fam["members"][0]["is_owner"] and fam["max_members"] == 8

    # E-postayla davet â†’ eÅŸi kartÄ± gÃ¶rÃ¼r ve kabul eder
    r = await client.post("/api/family/invites", json={"email": "ESI@example.com"}, headers=kemal)
    assert r.json()["family"]["pending_invites"] == ["esi@example.com"]
    mine = (await client.get("/api/family", headers=esi)).json()
    assert mine["family"] is None and mine["invites"][0]["family_name"] == "YÄ±lmazlar"
    r = await client.post(f"/api/family/invites/{mine['invites'][0]['id']}/accept", headers=esi)
    assert len(r.json()["family"]["members"]) == 2
    assert r.json()["family"]["pending_invites"] == []

    # EÅŸi kod paylaÅŸmadan listeyi gÃ¶rÃ¼r ve Ã¼rÃ¼n ekler; yeni listeleri de karÅŸÄ±lÄ±klÄ± gÃ¶rÃ¼nÃ¼r
    assert [x["id"] for x in (await client.get("/api/lists", headers=esi)).json()] == [lid]
    r = await client.post(f"/api/lists/{lid}/items", json={"group_id": ids["milk"], "preferred_brand": "Pınar"}, headers=esi)
    assert r.status_code == 201 and r.json()["items"][0]["added_by_name"] == "esi"
    lid2 = (await client.post("/api/lists", json={"name": "EÅŸimin"}, headers=esi)).json()["id"]
    assert lid2 in [x["id"] for x in (await client.get("/api/lists", headers=kemal)).json()]

    # Tasarruf bitirene yazÄ±lÄ±r, aile toplamÄ±nda gÃ¶rÃ¼nÃ¼r
    applied = (await client.post(f"/api/lists/{lid}/apply", json={"plan_type": "opportunist"}, headers=esi)).json()
    await client.patch(f"/api/lists/{lid}/items/{applied['items'][0]['id']}", json={"is_checked": True}, headers=esi)
    done = (await client.post(f"/api/lists/{lid}/complete", headers=esi)).json()
    assert D(done["saved_amount"]) == D("0.50")
    assert (await client.get("/api/savings", headers=kemal)).json()["record_count"] == 0
    fam = (await client.get("/api/family", headers=kemal)).json()["family"]
    assert D(fam["month_saved"]) == D(done["saved_amount"])

    # AyrÄ±lÄ±nca eriÅŸim biter
    esi_id = next(m["user_id"] for m in fam["members"] if not m["is_owner"])
    assert (await client.delete(f"/api/family/members/{esi_id}", headers=esi)).status_code == 204
    assert (await client.get(f"/api/lists/{lid}", headers=esi)).status_code == 404
    assert (await client.get("/api/family", headers=esi)).json()["family"] is None


async def test_family_code_limit_and_permissions(client):
    owner = await _user(client, "kurucu@example.com")
    fam = (await client.post("/api/family", json={"name": "BÃ¼yÃ¼k"}, headers=owner)).json()["family"]
    code = fam["invite_code"]
    assert len(code) == 8

    members = []
    for i in range(7):
        h = await _user(client, f"uye{i}@example.com")
        r = await client.post("/api/family/join", json={"code": code.lower()}, headers=h)
        assert r.status_code == 200
        members.append(h)
    late = await _user(client, "gec@example.com")
    r = await client.post("/api/family/join", json={"code": code}, headers=late)
    assert r.status_code == 409  # 8 kiÅŸi dolu
    assert (await client.post("/api/family", json={"name": "Ä°kinci"}, headers=members[0])).status_code == 409
    assert (await client.post("/api/family/join", json={"code": "YANLIS99"}, headers=late)).status_code == 404

    fam = (await client.get("/api/family", headers=owner)).json()["family"]
    ids = [m["user_id"] for m in fam["members"]]
    # Ãœye baÅŸkasÄ±nÄ± Ã§Ä±karamaz, kurucu Ã§Ä±karabilir
    assert (await client.delete(f"/api/family/members/{ids[2]}", headers=members[0])).status_code == 403
    assert (await client.delete(f"/api/family/members/{ids[2]}", headers=owner)).status_code == 204
    # Kurucu ayrÄ±lÄ±nca kuruculuk en eski Ã¼yeye geÃ§er
    assert (await client.delete(f"/api/family/members/{ids[0]}", headers=owner)).status_code == 204
    fam = (await client.get("/api/family", headers=members[0])).json()["family"]
    assert fam["owner_id"] == ids[1] and len(fam["members"]) == 6
