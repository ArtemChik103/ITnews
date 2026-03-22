import re

from bs4 import BeautifulSoup
from langdetect import DetectorFactory, LangDetectException, detect

from app.core.config import get_settings

DetectorFactory.seed = 0
WHITESPACE_RE = re.compile(r"\s+")


def clean_html(raw_text: str) -> str:
    soup = BeautifulSoup(raw_text or "", "html.parser")
    text = soup.get_text(separator=" ")
    return WHITESPACE_RE.sub(" ", text).strip()


def normalize_text(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip().lower()


def detect_language(text: str) -> str:
    settings = get_settings()
    try:
        language = detect(text) if text.strip() else settings.default_language
    except LangDetectException:
        language = settings.default_language
    return language if language in settings.languages else settings.default_language
