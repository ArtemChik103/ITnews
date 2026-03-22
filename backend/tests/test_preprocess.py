from app.services.ingestion.preprocess import clean_html, detect_language, normalize_text
from app.services.nlp.pipeline import extract_entities


class DummyArticle:
    def __init__(self, title: str, content_clean: str) -> None:
        self.title = title
        self.content_clean = content_clean


def test_clean_html_removes_tags() -> None:
    assert clean_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_normalize_text_lowercases_and_compacts_whitespace() -> None:
    assert normalize_text(" Hello   WORLD ") == "hello world"


def test_detect_language_has_fallback() -> None:
    assert detect_language("") in {"en", "ru"}


def test_extract_entities_uses_title_and_known_orgs() -> None:
    article = DummyArticle(
        title="Jeff Bezos joins Blue Origin in New York",
        content_clean="",
    )
    entities = {(entity.name, entity.entity_type) for entity in extract_entities(article)}
    assert ("Jeff Bezos", "PERSON") in entities
    assert ("Blue Origin", "ORGANIZATION") in entities
    assert ("New York", "LOCATION") in entities
