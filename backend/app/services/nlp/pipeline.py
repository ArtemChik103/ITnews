import re

from app.models.article import Article
from app.services.nlp.schemas import ExtractedEntity, ExtractedRelation

KNOWN_ORGANIZATIONS = {
    "amazon",
    "anthropic",
    "apple",
    "blue origin",
    "byd",
    "doordash",
    "google",
    "kalshi",
    "meta",
    "microsoft",
    "newegg",
    "nvidia",
    "openai",
    "palantir",
    "paramount plus",
    "pinterest",
    "strava",
    "tesla",
    "tinder",
    "twitter",
    "wordpress",
}
ORG_MARKERS = {
    "inc",
    "corp",
    "corporation",
    "company",
    "ltd",
    "llc",
    "gmbh",
    "group",
    "labs",
    "technologies",
    "банк",
    "компания",
}
KNOWN_LOCATIONS = {
    "moscow",
    "london",
    "paris",
    "berlin",
    "san francisco",
    "new york",
    "washington",
    "tokyo",
    "beijing",
    "kyiv",
    "minsk",
}


def extract_entities(article: Article) -> list[ExtractedEntity]:
    text = build_analysis_text(article)
    candidates = re.findall(r"\b[A-ZА-Я][a-zа-яA-ZА-Я-]+(?:\s+[A-ZА-Я][a-zа-яA-ZА-Я-]+){0,2}\b", text)
    entities: dict[tuple[str, str], ExtractedEntity] = {}
    for candidate in candidates:
        entity_type = classify_entity(candidate)
        if entity_type is None:
            continue
        normalized = normalize_entity_name(candidate)
        entities[(normalized, entity_type)] = ExtractedEntity(
            name=candidate.strip(),
            entity_type=entity_type,
            normalized_name=normalized,
        )

    lower_text = text.lower()
    for organization in KNOWN_ORGANIZATIONS:
        if organization in lower_text:
            entities[(organization, "ORGANIZATION")] = ExtractedEntity(
                name=organization.title(),
                entity_type="ORGANIZATION",
                normalized_name=organization,
            )
    for location in KNOWN_LOCATIONS:
        if location in lower_text:
            entities[(location, "LOCATION")] = ExtractedEntity(
                name=location.title(),
                entity_type="LOCATION",
                normalized_name=location,
            )
    return list(entities.values())


def extract_relations(article: Article, entities: list[ExtractedEntity]) -> list[ExtractedRelation]:
    text = build_analysis_text(article)
    relations: list[ExtractedRelation] = []
    by_normalized = {entity.normalized_name: entity for entity in entities}

    works_patterns = [
        re.compile(r"(?P<person>[A-ZА-Я][\w'-]+(?:\s+[A-ZА-Я][\w'-]+){0,2})\s+(?:works at|joined|leads|heads)\s+(?P<org>[A-ZА-Я][\w&.'-]+(?:\s+[A-ZА-Я][\w&.'-]+){0,3})"),
        re.compile(r"(?P<person>[A-ZА-Я][\w'-]+(?:\s+[A-ZА-Я][\w'-]+){0,2}),?\s+(?:CEO|CTO|founder|president)\s+of\s+(?P<org>[A-ZА-Я][\w&.'-]+(?:\s+[A-ZА-Я][\w&.'-]+){0,3})"),
        re.compile(r"(?P<org>[A-ZА-Я][\w&.'-]+(?:\s+[A-ZА-Я][\w&.'-]+){0,3})\s+(?:CEO|CTO|founder|president)\s+(?P<person>[A-ZА-Я][\w'-]+(?:\s+[A-ZА-Я][\w'-]+){0,2})"),
    ]
    location_patterns = [
        re.compile(r"(?P<org>[A-ZА-Я][\w&.'-]+(?:\s+[A-ZА-Я][\w&.'-]+){0,3})\s+(?:is based in|headquartered in|located in)\s+(?P<loc>[A-ZА-Я][\w'-]+(?:\s+[A-ZА-Я][\w'-]+){0,2})")
    ]

    for pattern in works_patterns:
        for match in pattern.finditer(text):
            person = by_normalized.get(normalize_entity_name(match.group("person")))
            org = by_normalized.get(normalize_entity_name(match.group("org")))
            if person and org:
                relations.append(
                    ExtractedRelation(
                        source_name=person.name,
                        source_type=person.entity_type,
                        relation_type="ASSOCIATED_WITH",
                        target_name=org.name,
                        target_type=org.entity_type,
                    )
                )

    for pattern in location_patterns:
        for match in pattern.finditer(text):
            org = by_normalized.get(normalize_entity_name(match.group("org")))
            location = by_normalized.get(normalize_entity_name(match.group("loc")))
            if org and location:
                relations.append(
                    ExtractedRelation(
                        source_name=org.name,
                        source_type=org.entity_type,
                        relation_type="LOCATED_IN",
                        target_name=location.name,
                        target_type=location.entity_type,
                    )
                )
    return relations


def classify_entity(value: str) -> str | None:
    lowered = value.lower()
    parts = lowered.split()
    if lowered in KNOWN_LOCATIONS:
        return "LOCATION"
    if lowered in KNOWN_ORGANIZATIONS:
        return "ORGANIZATION"
    if any(marker in parts or marker in lowered for marker in ORG_MARKERS):
        return "ORGANIZATION"
    if len(parts) >= 2:
        return "PERSON"
    return None


def build_analysis_text(article: Article) -> str:
    segments = [article.title.strip(), article.content_clean.strip()]
    return ". ".join(segment for segment in segments if segment)


def normalize_entity_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()
