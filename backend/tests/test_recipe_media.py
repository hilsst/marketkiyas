from app.services import recipe_media


def test_stored_url_wins(tmp_path, monkeypatch):
    monkeypatch.setattr(recipe_media, "RECIPE_MEDIA_DIR", tmp_path)
    assert recipe_media.recipe_image_url("a", "https://cdn/x.jpg") == "https://cdn/x.jpg"


def test_file_found_by_slug(tmp_path, monkeypatch):
    monkeypatch.setattr(recipe_media, "RECIPE_MEDIA_DIR", tmp_path)
    (tmp_path / "hi-x.jpg").write_bytes(b"x")
    assert recipe_media.recipe_image_url("hi-x", None) == "/media/recipes/hi-x.jpg"
    assert recipe_media.recipe_image_url("yok", None) is None


def test_missing_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(recipe_media, "RECIPE_MEDIA_DIR", tmp_path / "yok")
    assert recipe_media.recipe_image_url("a", None) is None
