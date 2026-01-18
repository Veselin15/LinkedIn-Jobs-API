import re
from datetime import date, timedelta
from typing import List, Tuple, Optional, Set

from .constants import (
    TECH_KEYWORDS, NEGATION_PATTERNS, SENIORITY_MAP,
    SALARY_IGNORE_TERMS, SALARY_HINTS, SALARY_MULTIPLIERS
)

# --- 1. PRE-COMPILE PATTERNS FOR PERFORMANCE ---
# compiling regex once at the module level is much faster than doing it for every job

# Skills: Handle C++ and C# specifically, otherwise use word boundaries
SKILL_PATTERNS = []
for skill in TECH_KEYWORDS:
    if skill in ["C++", "C#", ".NET"]:
        pattern = re.escape(skill.lower())
    else:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
    SKILL_PATTERNS.append((skill, re.compile(pattern)))

NEGATION_REGEXES = [re.compile(p) for p in NEGATION_PATTERNS]

# Seniority: Compile all patterns
SENIORITY_PATTERNS = {
    level: [re.compile(r'\b' + kw + r'\b') for kw in kws]
    for level, kws in SENIORITY_MAP.items()
}

# Salary Ignore Terms
SALARY_IGNORE_REGEX = re.compile(r'\b(' + '|'.join(SALARY_IGNORE_TERMS) + r')\b')


def extract_skills(text: str) -> List[str]:
    """
    Extracts tech skills from text, filtering out negated contexts.
    Example: "No Python experience required" -> Python is NOT extracted.
    """
    if not text:
        return []

    text_lower = text.lower()
    found_skills = set()

    for skill_name, pattern in SKILL_PATTERNS:
        # Fast search
        for match in pattern.finditer(text_lower):
            start, end = match.span()

            # Context Window: Check 40 chars before/after for negation
            ctx_start = max(0, start - 40)
            ctx_end = min(len(text_lower), end + 40)
            context = text_lower[ctx_start:ctx_end]

            # Check negation
            if not any(neg.search(context) for neg in NEGATION_REGEXES):
                found_skills.add(skill_name)
                # Once found valid, break loop for this specific skill
                # (no need to find the same skill twice)
                break

    return list(found_skills)


def extract_seniority(title: str, description: str) -> str:
    """
    Determines seniority. Title has higher priority than description.
    Includes logic to ignore "Reporting to Senior Manager" type phrases.
    """
    text_title = title.lower() if title else ""
    text_desc = description.lower() if description else ""

    # 1. Title Scan (High Confidence)
    for level, patterns in SENIORITY_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(text_title):
                return level

    # 2. Description Scan (Lower Confidence + Context Check)
    # Exclude phrases indicating a supervisor, not the role itself
    exclusion_pattern = re.compile(r'(report(ing|s)?\s+to|supervised\s+by)\s+[\w\s]*$')

    for level, patterns in SENIORITY_PATTERNS.items():
        for pattern in patterns:
            # Find all matches in description
            for match in pattern.finditer(text_desc):
                # Check context 25 chars before the match
                start = match.start()
                pre_context = text_desc[max(0, start - 25):start]

                # Only accept if NOT preceded by "reporting to"
                if not exclusion_pattern.search(pre_context):
                    return level

    return "Not Specified"


def parse_salary(text: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Robust salary parser. Handles:
    - Ranges: "80-100k", "$120k - $150k"
    - Decimals: "1.5k" -> 1500
    - Rates: "$60 / hour" -> Annualized to ~124k
    - Currencies: $, €, £, etc.
    """
    if not text:
        return None, None, None

    text_lower = text.lower()

    # 1. Currency Detection
    currency = "USD"  # Default
    if any(s in text for s in ['€', 'eur']):
        currency = "EUR"
    elif any(s in text for s in ['£', 'gbp']):
        currency = "GBP"
    elif 'bgn' in text_lower:
        currency = "BGN"
    elif 'aud' in text_lower:
        currency = "AUD"
    elif 'cad' in text_lower:
        currency = "CAD"

    # 2. Helper: Determine multiplier (Yearly vs Monthly vs Hourly)
    def get_period_multiplier(match_end_pos):
        # Look ahead 40 chars for "per month", "/hr", etc.
        suffix = text_lower[match_end_pos:match_end_pos + 40]
        for period, patterns in SALARY_MULTIPLIERS.items():
            for pattern in patterns:
                if re.search(pattern, suffix):
                    if period == 'monthly':
                        return 12
                    elif period == 'hourly':
                        return 2080  # 40h * 52w
                    elif period == 'daily':
                        return 260  # 5d * 52w
        return 1  # Default to Yearly

    # 3. Helper: Parse number string
    def parse_num(num_str, suffix_k):
        # Remove commas (100,000 -> 100000), keep dots (1.5 -> 1.5)
        clean = num_str.replace(',', '')
        try:
            val = float(clean)
            if suffix_k:
                val *= 1000
            return int(val)
        except ValueError:
            return None

    candidates = []

    # --- PATTERN A: Ranges (e.g. "80-100k", "80k - 100k", "$80,000 - $120,000") ---
    range_pattern = re.compile(
        r'([$£€]?\s*\d{1,3}(?:[,\.]\d{3})*(?:\.\d+)?)\s*([kK])?\s*[-–to]+\s*([$£€]?\s*\d{1,3}(?:[,\.]\d{3})*(?:\.\d+)?)\s*([kK])?')

    for m in range_pattern.finditer(text_lower):
        raw_n1 = re.sub(r'[$£€\s]', '', m.group(1))  # Clean symbols
        raw_n2 = re.sub(r'[$£€\s]', '', m.group(3))

        k1 = bool(m.group(2))  # First K?
        k2 = bool(m.group(4))  # Second K?

        # Logic: If "80-100k", apply 'k' to both
        if k2 and not k1: k1 = True

        v1 = parse_num(raw_n1, k1)
        v2 = parse_num(raw_n2, k2)

        if v1 and v2:
            mult = get_period_multiplier(m.end())
            candidates.append((v1 * mult, v2 * mult))

    # --- PATTERN B: Single Numbers (e.g. "$120k", "5000 / month") ---
    # Only if A didn't find anything or to supplement
    single_pattern = re.compile(r'([$£€])?\s*(\d{1,3}(?:[,\.]\d{3})*(?:\.\d+)?)\s*([kK])?')

    for m in single_pattern.finditer(text_lower):
        start, end = m.span()

        # Ignore if followed by invalid terms (e.g. "250,000 users")
        suffix_window = text_lower[end:end + 20]
        if SALARY_IGNORE_REGEX.search(suffix_window):
            continue

        raw_val = m.group(2)
        has_k = bool(m.group(3))
        has_curr = bool(m.group(1))

        # Valid salary must have a Currency Symbol OR 'k' OR 'salary' keyword nearby
        window = text_lower[max(0, start - 30):min(len(text_lower), end + 30)]
        is_valid_context = any(h in window for h in SALARY_HINTS) or has_curr or has_k

        if is_valid_context:
            val = parse_num(raw_val, has_k)
            if val:
                mult = get_period_multiplier(end)
                candidates.append((val * mult, val * mult))

    # 4. Selection Logic
    if not candidates:
        return None, None, None

    # Filter sanity (Annualized between 5k and 1M)
    valid_candidates = [
        (mn, mx) for mn, mx in candidates
        if 5000 <= mn <= 1000000
    ]

    if not valid_candidates:
        return None, None, None

    # Pick the best candidate (widest range usually indicates the main salary block)
    best = max(valid_candidates, key=lambda x: x[1])
    return best[0], best[1], currency


def parse_relative_date(text: str) -> date:
    """
    Parses '3 days ago', '1 week ago', 'just now'.
    """
    if not text:
        return date.today()

    text = text.lower().strip()
    today = date.today()

    if any(k in text for k in ['just now', 'today', 'hour', 'minute', 'second']):
        return today

    # Regex to capture specific number and unit
    match = re.search(r'(\d+)\+?\s*(day|week|month)', text)
    if match:
        num = int(match.group(1))
        unit = match.group(2)

        if 'day' in unit:
            return today - timedelta(days=num)
        if 'week' in unit:
            return today - timedelta(weeks=num)
        if 'month' in unit:
            return today - timedelta(days=num * 30)

    return today