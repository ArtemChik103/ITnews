from dataclasses import dataclass


@dataclass(slots=True)
class ExtractedEntity:
    name: str
    entity_type: str
    normalized_name: str


@dataclass(slots=True)
class ExtractedRelation:
    source_name: str
    source_type: str
    relation_type: str
    target_name: str
    target_type: str
