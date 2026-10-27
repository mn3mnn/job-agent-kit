# New in this fork. Cheap, deterministic eligibility checks run on each job
# description right after it's scraped, so jobs the candidate can't take never
# reach scoring: postings that need a language outside `allowed_languages`, and
# postings outside `work_authorized_countries` that won't sponsor a visa.
# Both are heuristics; a false negative just means the scorer sees the job.

import re
from typing import Optional

STOPWORDS = {
    "English": {"the", "and", "with", "you", "our", "for", "are", "will", "your", "of", "to", "in", "we", "is"},
    "German": {"und", "der", "die", "das", "mit", "für", "wir", "sie", "ist", "bei", "auf", "eine", "ein", "du", "dich", "dein", "deine", "zu", "von", "oder", "uns", "werden"},
    "French": {"et", "les", "des", "pour", "avec", "nous", "vous", "une", "est", "dans", "sur", "le", "la", "du"},
    "Spanish": {"y", "los", "las", "para", "con", "nuestro", "una", "es", "en", "el", "del", "por", "experiencia"},
    "Italian": {"e", "il", "per", "con", "della", "delle", "una", "sono", "nel", "di", "che", "esperienza", "lavoro"},
    "Dutch": {"en", "het", "de", "van", "voor", "met", "een", "wij", "jij", "je", "bij", "ons", "zijn"},
    "Polish": {"i", "w", "z", "na", "do", "dla", "oraz", "jest", "się", "nie", "doświadczenie", "pracy"},
    "Portuguese": {"e", "os", "as", "para", "com", "uma", "em", "do", "da", "dos", "experiência", "você"},
}

LANGUAGE_NAMES = ["German", "French", "Spanish", "Italian", "Dutch", "Polish", "Portuguese", "Swedish",
                  "Danish", "Norwegian", "Finnish", "Czech", "Turkish", "Hebrew", "Japanese", "Mandarin",
                  "Chinese", "Korean", "Russian", "Hungarian", "Romanian", "Greek", "Flemish", "Deutsch"]

# "fluent German", "German (C1)", "German is required", "business-level German"...
REQUIRED_LANG = re.compile(
    r"(?:fluent|fluency|native|business[- ]?(?:level|fluent)|professional|proficien\w*|very good|excellent|strong|good|"
    r"advanced|full)\s+(?:(?:written|spoken|verbal|command of|knowledge of|skills in|in|both|and|or)\s+){0,4}"
    r"(?:\w+\s+(?:and|&)\s+)?(?P<a>{langs})"
    r"|(?P<b>{langs})\s*(?:\(|:|-)?\s*(?:(?:language|proficiency|skills|level|at|of|or|above|minimum|min\.?)\s*){0,5}(?:B2|C1|C2)"
    r"|(?P<c>{langs})\s+(?:\w+\s+){0,3}(?:is|are)\s+(?:a\s+)?(?:must|required|mandatory|essential)"
    r"|(?:sehr gute|fließende|verhandlungssichere|gute)\s+deutsch"
    r"|(?:in\s+)?both\s+(?:{langs})\s+and\s+English|English\s+and\s+(?:{langs})\s+(?:language\s+)?(?:is\s+)?(?:required|mandatory|essential)"
    r"|deutschkenntnisse\s*\(?(?:B2|C1|C2|verhandlungssicher|fließend|sehr gut)"
    r"|(?P<d>{langs})\s+at\s+(?:a\s+)?(?:business|professional|native(?:[- ]speaker)?|fluent)\s+level"
    r"|English\s+and\s+(?P<e>{langs})\s*\(\s*(?:native|fluent|full)"
    r"|(?:kommunizierst|sprichst)\s+(?:sicher|fließend|sehr gut)\s+(?:auf\s+)?deutsch".replace("{langs}", "|".join(LANGUAGE_NAMES)),
    re.IGNORECASE,
)
SOFT_HINT = re.compile(r"\b(?:plus|nice[- ]to[- ]have|advantage|bonus|preferred|beneficial|desirable|helpful)\b", re.IGNORECASE)

NO_SPONSORSHIP = re.compile(
    r"(?:no|not|unable to|cannot|can't|won't|will not|do not|don't|does not|doesn't)\s+(?:\w+\s+){0,3}"
    r"(?:offer|provide|support|sponsor)\w*\s+(?:\w+\s+){0,2}(?:visa|sponsorship|work permit|relocation)"
    r"|(?:visa\s+)?sponsorship\s+(?:is\s+)?(?:not\s+(?:available|offered|provided|possible)|unavailable)"
    r"|without\s+(?:the\s+need\s+for\s+)?(?:visa\s+)?sponsorship"
    r"|must\s+(?:already\s+)?(?:have|hold|possess)\s+(?:\w+\s+){0,4}(?:right to work|work permit|work authori[sz]ation|eu citizenship)"
    r"|must\s+(?:be\s+)?(?:already\s+)?(?:authori[sz]ed|eligible)\s+to\s+work"
    r"|(?:right\s+to\s+work|work\s+authori[sz]ation)\s+(?:is\s+)?(?:required|must\s+have|needed)"
    r"|valid\s+(?:\w+\s+){0,2}work\s+(?:authori[sz]ation|permit)\s*\(?required"
    r"|relocation\s+(?:support|assistance|package)\s+(?:is\s+)?not\s+(?:provided|offered|available)"
    r"|must\s+(?:currently\s+)?(?:reside|live|be\s+based)\s+in"
    r"|^\s*(?:residency|residence)\s+in\s+\w+\s*$"
    r"|national\s+of\s+a\s+(?:\w+\s+){0,3}member"
    r"|must\s+(?:own|have|hold)\s+a\s+valid\s+work\s+permit"
    r"|only\s+consider\s+candidates\s+who\s+are\s+(?:currently\s+)?(?:residing|based|living|located)"
    r"|(?:eu|uk|us) citizens? only|only (?:eu|uk|us) citizens",
    re.IGNORECASE | re.MULTILINE,
)
YES_SPONSORSHIP = re.compile(
    r"(?:visa|work permit|relocation)\s+(?:\w+\s+){0,2}(?:sponsorship|support|assistance|provided|offered|available)"
    r"|(?:we|will|can|happy to|able to)\s+(?:\w+\s+){0,2}sponsor"
    r"|sponsorship\s+(?:is\s+)?(?:available|offered|provided|possible)",
    re.IGNORECASE,
)

# Ported from Auto_Jobs_Applier_AIHawk's _min_years_required: "3+ years of
# experience", "5-7 years professional"... needs an experience word nearby so
# "founded 10 years ago" doesn't count.
YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:-|to|or)?\s*(?:\d{1,2})?\s*\+?\s*(?:years?|yrs)\b"
                      r"(?P<tail>(?:[\s'\"’,]+[\w-]+){0,4})", re.IGNORECASE)
EXPERIENCE_WORDS = ("experience", "exp", "professional", "industry", "relevant", "commercial",
                    "background", "hands-on", "hands on", "work", "engineering", "development",
                    "backend", "software", "programming", "coding")


def min_years_required(text: str) -> Optional[int]:
    years = [int(m.group(1)) for m in YEARS_RE.finditer(text)
             if any(k in (m.group("tail") or "").lower() for k in EXPERIENCE_WORDS)]
    # ranges use their lower bound, but across separate requirements the
    # largest one binds ("5+ years overall, 3+ with Python" means 5)
    return max(years) if years else None


def detect_language(text: str) -> str:
    words = re.findall(r"[a-zA-ZÀ-ž']+", text.lower())
    if not words:
        return "English"
    counts = {lang: sum(w in sw for w in words) for lang, sw in STOPWORDS.items()}
    return max(counts, key=counts.get)


def required_language(description: str, allowed: list[str]) -> Optional[str]:
    """Return the name of a required language the candidate doesn't speak, else None."""
    allowed_l = {a.lower() for a in allowed}
    body_lang = detect_language(description)
    if body_lang.lower() not in allowed_l:
        return body_lang
    for m in REQUIRED_LANG.finditer(description):
        lang = (m.group("a") or m.group("b") or m.group("c") or m.group("d") or m.group("e") or "German").title()
        lang = "German" if lang == "Deutsch" else lang
        if lang.lower() in allowed_l:
            continue
        # "German is a plus" / "fluent German is nice to have" is not a requirement
        window = description[m.start(): m.end() + 80].split("\n")[0]
        if SOFT_HINT.search(window):
            continue
        return lang
    return None


def sponsorship_problem(location: str, description: str, authorized: list[str]) -> Optional[str]:
    """Return a skip reason when the job needs a visa the employer won't sponsor."""
    loc = location.lower()
    if any(c.lower() in loc for c in authorized):
        return None
    # Only an explicit refusal disqualifies; silence is fine (user, 2026-10-25).
    if NO_SPONSORSHIP.search(description) and not YES_SPONSORSHIP.search(description):
        return "no visa sponsorship"
    return None


def eligibility_skip_reason(job, parameters: dict) -> Optional[str]:
    allowed = parameters.get("allowed_languages") or ["English"]
    authorized = parameters.get("work_authorized_countries") or []
    lang = required_language(job.description or "", allowed)
    if lang:
        return f"requires {lang}"
    max_years = parameters.get("max_years_experience")
    years = min_years_required(job.description or "")
    if max_years is not None and years is not None and years > max_years:
        return f"requires {years}+ years"
    if authorized:
        return sponsorship_problem(job.location or "", job.description or "", authorized)
    return None
