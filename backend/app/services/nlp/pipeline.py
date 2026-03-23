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
INVALID_ENTITY_PREFIXES = {
    "a",
    "amid",
    "aren",
    "are",
    "at",
    "best",
    "can",
    "how",
    "it",
    "new",
    "the",
    "there",
    "this",
    "what",
    "why",
}
INVALID_ENTITY_TOKENS = {
    "accidentally",
    "almost",
    "ban",
    "bet",
    "calls",
    "coming",
    "conference",
    "court",
    "crazy",
    "developers",
    "disappoints",
    "filing",
    "future",
    "game",
    "gamers",
    "governments",
    "gtc",
    "happened",
    "hate",
    "investors",
    "jury",
    "legal",
    "misled",
    "project",
    "reveals",
    "robot",
    "says",
    "scientists",
    "street",
    "turmoil",
    "users",
    "wall",
    "week",
    "win",
}
PERSON_TITLE_PREFIXES = {"ceo", "cto", "founder", "president"}
PERSON_NAME_STOPWORDS = {
    "about",
    "ai",
    "aren",
    "been",
    "built",
    "code",
    "could",
    "coupon",
    "culture",
    "denies",
    "dm",
    "dms",
    "end-to-end",
    "ev",
    "excited",
    "fun",
    "gas",
    "get",
    "girl",
    "has",
    "if",
    "instagram",
    "is",
    "it",
    "killing",
    "plus",
    "promo",
    "retreat",
    "sabotage",
    "seem",
    "shy",
}


def extract_entities(article: Article) -> list[ExtractedEntity]:
    text = build_analysis_text(article)
    candidates = re.findall(r"\b[A-ZА-Я][a-zа-яA-ZА-Я-]+(?:\s+[A-ZА-Я][a-zа-яA-ZА-Я-]+){0,2}\b", text)
    entities: dict[tuple[str, str], ExtractedEntity] = {}
    for candidate in candidates:
        candidate = sanitize_entity_candidate(candidate)
        if not is_valid_entity_candidate(candidate):
            continue
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
    sentences = split_sentences(text)

    works_patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"(?P<person>[A-ZА-Я][\w'-]+(?:\s+[A-ZА-Я][\w'-]+){0,2})\s+(?:works at|joined|leads|heads)\s+(?P<org>[A-ZА-Я][\w&.'-]+(?:\s+[A-ZА-Я][\w&.'-]+){0,3})"), "WORKS_AT"),
        (re.compile(r"(?P<person>[A-ZА-Я][\w'-]+(?:\s+[A-ZА-Я][\w'-]+){0,2}),?\s+(?:CEO|CTO|founder|president|co-founder)\s+of\s+(?P<org>[A-ZА-Я][\w&.'-]+(?:\s+[A-ZА-Я][\w&.'-]+){0,3})"), "LEADS"),
        (re.compile(r"(?P<org>[A-ZА-Я][\w&.'-]+(?:\s+[A-ZА-Я][\w&.'-]+){0,3})\s+(?:CEO|CTO|founder|president|co-founder)\s+(?P<person>[A-ZА-Я][\w'-]+(?:\s+[A-ZА-Я][\w'-]+){0,2})"), "LEADS"),
        (re.compile(r"(?P<org>[A-ZА-Я][\w&.'-]+(?:\s+[A-ZА-Я][\w&.'-]+){0,3})\s+(?:hired|appointed|named)\s+(?P<person>[A-ZА-Я][\w'-]+(?:\s+[A-ZА-Я][\w'-]+){0,2})"), "HIRED_BY"),
        (re.compile(r"(?P<person>[A-ZА-Я][\w'-]+(?:\s+[A-ZА-Я][\w'-]+){0,2})\s+(?:at|from)\s+(?P<org>[A-ZА-Я][\w&.'-]+(?:\s+[A-ZА-Я][\w&.'-]+){0,3})"), "ASSOCIATED_WITH"),
    ]
    location_patterns = [
        re.compile(r"(?P<org>[A-ZА-Я][\w&.'-]+(?:\s+[A-ZА-Я][\w&.'-]+){0,3})\s+(?:is based in|headquartered in|located in|opens in|expands to)\s+(?P<loc>[A-ZА-Я][\w'-]+(?:\s+[A-ZА-Я][\w'-]+){0,2})")
    ]

    for pattern, rel_type in works_patterns:
        for match in pattern.finditer(text):
            person = by_normalized.get(normalize_entity_name(match.group("person")))
            org = by_normalized.get(normalize_entity_name(match.group("org")))
            if person and org:
                relations.append(
                    ExtractedRelation(
                        source_name=person.name,
                        source_type=person.entity_type,
                        relation_type=rel_type,
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

    for sentence in sentences:
        sentence_entities = entities_in_text(sentence, entities)
        sentence_people = [entity for entity in sentence_entities if entity.entity_type == "PERSON"]
        sentence_orgs = [entity for entity in sentence_entities if entity.entity_type == "ORGANIZATION"]
        sentence_locations = [entity for entity in sentence_entities if entity.entity_type == "LOCATION"]

        if sentence_people and sentence_orgs and len(sentence_entities) <= 6:
            for person in sentence_people[:2]:
                for org in sentence_orgs[:2]:
                    relations.append(
                        ExtractedRelation(
                            source_name=person.name,
                            source_type=person.entity_type,
                            relation_type="ASSOCIATED_WITH",
                            target_name=org.name,
                            target_type=org.entity_type,
                        )
                    )

        if sentence_orgs and sentence_locations and len(sentence_entities) <= 6:
            for org in sentence_orgs[:2]:
                for location in sentence_locations[:2]:
                    relations.append(
                        ExtractedRelation(
                            source_name=org.name,
                            source_type=org.entity_type,
                            relation_type="LOCATED_IN",
                            target_name=location.name,
                            target_type=location.entity_type,
                        )
                    )

    people = [entity for entity in entities if entity.entity_type == "PERSON"]
    organizations = [entity for entity in entities if entity.entity_type == "ORGANIZATION"]
    locations = [entity for entity in entities if entity.entity_type == "LOCATION"]
    title_entities = entities_in_text(article.title, entities)
    title_people = [entity for entity in title_entities if entity.entity_type == "PERSON"]
    title_orgs = [entity for entity in title_entities if entity.entity_type == "ORGANIZATION"]
    title_locations = [entity for entity in title_entities if entity.entity_type == "LOCATION"]

    if not relations and title_people and title_orgs:
        for person in title_people[:2]:
            for org in title_orgs[:2]:
                relations.append(
                    ExtractedRelation(
                        source_name=person.name,
                        source_type=person.entity_type,
                        relation_type="ASSOCIATED_WITH",
                        target_name=org.name,
                        target_type=org.entity_type,
                    )
                )

    if not relations and title_orgs and title_locations:
        for org in title_orgs[:2]:
            for location in title_locations[:2]:
                relations.append(
                    ExtractedRelation(
                        source_name=org.name,
                        source_type=org.entity_type,
                        relation_type="LOCATED_IN",
                        target_name=location.name,
                        target_type=location.entity_type,
                    )
                )

    if not relations and len(people) == 1 and organizations:
        for org in organizations[:2]:
            relations.append(
                ExtractedRelation(
                    source_name=people[0].name,
                    source_type=people[0].entity_type,
                    relation_type="ASSOCIATED_WITH",
                    target_name=org.name,
                    target_type=org.entity_type,
                )
            )

    if not relations and len(organizations) == 1 and locations:
        for location in locations[:2]:
            relations.append(
                ExtractedRelation(
                    source_name=organizations[0].name,
                    source_type=organizations[0].entity_type,
                    relation_type="LOCATED_IN",
                    target_name=location.name,
                    target_type=location.entity_type,
                )
            )

    deduplicated: dict[tuple[str, str, str, str, str], ExtractedRelation] = {}
    for relation in relations:
        key = (
            normalize_entity_name(relation.source_name),
            relation.source_type,
            relation.relation_type,
            normalize_entity_name(relation.target_name),
            relation.target_type,
        )
        if is_valid_relation(relation):
            deduplicated[key] = relation
    return list(deduplicated.values())


def classify_entity(value: str) -> str | None:
    lowered = value.lower()
    parts = lowered.split()
    if lowered in KNOWN_LOCATIONS:
        return "LOCATION"
    if lowered in KNOWN_ORGANIZATIONS:
        return "ORGANIZATION"
    if any(marker in parts or marker in lowered for marker in ORG_MARKERS):
        return "ORGANIZATION"
    if 2 <= len(parts) <= 3:
        return "PERSON"
    return None


def build_analysis_text(article: Article) -> str:
    segments = [article.title.strip(), article.content_clean.strip()]
    return ". ".join(segment for segment in segments if segment)


def normalize_entity_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()


def split_sentences(text: str) -> list[str]:
    return [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", text) if segment.strip()]


def entities_in_text(text: str, entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
    lowered = text.lower()
    return [entity for entity in entities if entity.normalized_name in lowered]


def is_valid_entity_candidate(value: str) -> bool:
    lowered = normalize_entity_name(value)
    parts = lowered.split()
    if len(parts) < 2:
        return False
    if parts[0] in INVALID_ENTITY_PREFIXES:
        return False
    if any(token in INVALID_ENTITY_TOKENS for token in parts):
        return False
    if lowered.endswith("'s"):
        return False
    return True


def sanitize_entity_candidate(value: str) -> str:
    parts = value.strip().split()
    if len(parts) >= 3 and parts[0].lower() in PERSON_TITLE_PREFIXES:
        parts = parts[1:]
    return " ".join(parts)


def is_valid_relation(relation: ExtractedRelation) -> bool:
    if relation.relation_type == "LOCATED_IN":
        return relation.source_type == "ORGANIZATION" and relation.target_type == "LOCATION"
    if relation.relation_type in ("ASSOCIATED_WITH", "WORKS_AT", "LEADS", "HIRED_BY"):
        return (
            relation.source_type == "PERSON"
            and relation.target_type == "ORGANIZATION"
            and looks_like_person_name(relation.source_name)
        )
    return True


def looks_like_person_name(value: str) -> bool:
    parts = normalize_entity_name(value).split()
    if not 2 <= len(parts) <= 3:
        return False
    if any(part in PERSON_NAME_STOPWORDS for part in parts):
        return False
    if parts[0] in KNOWN_ORGANIZATIONS:
        return False
    return True
