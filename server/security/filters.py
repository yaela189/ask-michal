# -*- coding: utf-8 -*-
import re
from dataclasses import dataclass


@dataclass
class FilterResult:
    blocked: bool
    refusal_message: str = ""
    reason: str = ""


# Hebrew refusal messages
REFUSAL_PII = (
    "אינני רשאית לעבד מידע אישי מזהה. "
    "אנא הסר/י פרטים אישיים מהשאלה ונסה/י שנית."
)
REFUSAL_PERSONAL = (
    "אינני רשאית לספק מידע אישי על חיילים. "
    "אפשר לעזור בשאלות כלליות על נהלים וזכויות."
)
REFUSAL_INJECTION = "אינני יכולה לעבד בקשה זו."


class InputFilter:
    """Filter incoming questions for PII and security violations."""

    # Israeli ID (Teudat Zehut): exactly 9 digits
    TEUDAT_ZEHUT_PATTERN = re.compile(r"\b\d{9}\b")

    # Israeli phone numbers
    PHONE_PATTERN = re.compile(r"\b0[2-9]\d{7,8}\b|(\+972|972)\d{8,9}\b")

    # Patterns suggesting a query about a specific person
    PERSONAL_QUERY_PATTERNS = [
        re.compile(r"מספר\s+אישי"),
        re.compile(r"תעודת\s+זהות"),
        re.compile(r"ת\.?ז\.?"),
        re.compile(r"כתובת\s+של"),
        re.compile(r"טלפון\s+של"),
        re.compile(r"איפה\s+(?:גר|גרה)\b"),
        re.compile(r"מידע\s+על\s+[\u05d0-\u05ea]+\s+[\u05d0-\u05ea]+"),
        # IDF ranks followed by a name
        re.compile(
            r'(טוראי|רב"ט|סמל|סמ"ר|רס"ל|סא"ל|אל"מ|תא"ל|רב\s*אלוף|סגן|סרן|רס"ן)'
            r"\s+[\u05d0-\u05ea]+"
        ),
    ]

    # Prompt injection patterns (Hebrew + English)
    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(previous|above|all)\s+(instructions|prompts)", re.I),
        re.compile(r"forget\s+(your|all)\s+(instructions|rules)", re.I),
        re.compile(r"התעלם\s+מ(ה?(הנחיות|כללים|הוראות))"),
        re.compile(r"שנה\s+את\s+הזהות"),
        re.compile(r"אתה\s+לא\s+מיכל"),
        re.compile(r"system\s*prompt", re.I),
        re.compile(r"you\s+are\s+now", re.I),
        re.compile(r"act\s+as\s+(?!a\s+hr)", re.I),
    ]

    def check(self, text: str) -> FilterResult:
        # Check for PII data in the question itself
        if self.TEUDAT_ZEHUT_PATTERN.search(text):
            return FilterResult(
                blocked=True, refusal_message=REFUSAL_PII, reason="teudat_zehut"
            )

        if self.PHONE_PATTERN.search(text):
            return FilterResult(
                blocked=True, refusal_message=REFUSAL_PII, reason="phone_number"
            )

        # Check for queries about specific individuals
        for pattern in self.PERSONAL_QUERY_PATTERNS:
            if pattern.search(text):
                return FilterResult(
                    blocked=True,
                    refusal_message=REFUSAL_PERSONAL,
                    reason="personal_query",
                )

        # Check for prompt injection attempts
        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(text):
                return FilterResult(
                    blocked=True,
                    refusal_message=REFUSAL_INJECTION,
                    reason="injection_attempt",
                )

        return FilterResult(blocked=False)


class OutputFilter:
    """Sanitize model output to remove any accidentally leaked PII."""

    TEUDAT_ZEHUT_PATTERN = re.compile(r"\b\d{9}\b")
    PHONE_PATTERN = re.compile(r"\b0[2-9]\d{7,8}\b|(\+972|972)\d{8,9}\b")

    def sanitize(self, text: str) -> str:
        text = self.TEUDAT_ZEHUT_PATTERN.sub("[מספר מזהה הוסר]", text)
        text = self.PHONE_PATTERN.sub("[מספר טלפון הוסר]", text)
        return text
