import re
from .constants import TECH_KEYWORDS, NEGATION_PATTERNS, SENIORITY_MAP  # <--- Import from new file


def extract_skills(text):
    """
    Finds skills but ignores them if they appear near 'no experience' phrases.
    """
    if not text:
        return []

    found_skills = set()
    text_lower = text.lower()

    for skill in TECH_KEYWORDS:
        # Escape the skill for regex (e.g., C++)
        skill_esc = re.escape(skill.lower())
        pattern = r'\b' + skill_esc + r'\b'

        # C++ and C# handling
        if skill in ["C++", "C#", ".NET"]:
            pattern = re.escape(skill.lower())

        # Find all occurrences of the skill
        for match in re.finditer(pattern, text_lower):
            start, end = match.span()

            # Context Window: 50 chars before and 50 chars after
            context_start = max(0, start - 50)
            context_end = min(len(text_lower), end + 50)
            context_window = text_lower[context_start:context_end]

            # Check for negations in this window
            is_negative = False
            for neg in NEGATION_PATTERNS:
                if re.search(neg, context_window):
                    is_negative = True
                    break

            if not is_negative:
                found_skills.add(skill)
                # Once found valid, move to next skill
                break

    return list(found_skills)


def extract_seniority(title, description):
    """
    Determines seniority. Title has higher priority than description.
    """
    text_title = title.lower() if title else ""
    text_desc = description.lower() if description else ""

    # 1. Check Title First (Strongest Signal)
    for level, keywords in SENIORITY_MAP.items():
        for kw in keywords:
            if re.search(r'\b' + kw + r'\b', text_title):
                return level

    # 2. Check Description (Weaker Signal)
    for level, keywords in SENIORITY_MAP.items():
        for kw in keywords:
            if re.search(r'\b' + kw + r'\b', text_desc):
                return level

    # Default
    return "Not Specified"


def parse_salary(text):
    if not text:
        return None, None, None

    # Identify Currency
    currency = "USD"
    if '€' in text or 'EUR' in text:
        currency = "EUR"
    elif '£' in text or 'GBP' in text:
        currency = "GBP"
    elif 'BGN' in text or 'lv' in text:
        currency = "BGN"  # Added support for local currency if needed

    text_lower = text.lower()
    clean_numbers = []

    # Helper function to check if a match is "safe" (not followed by 'people', etc.)
    def is_safe_match(match_obj):
        end_pos = match_obj.end()
        # Look at the next 20 characters
        suffix = text_lower[end_pos:end_pos + 20]

        for ignore_term in SALARY_IGNORE_TERMS:
            # Check if the ignore term appears immediately after the number
            if re.match(r'\s*' + ignore_term, suffix):
                return False
        return True

    # Strategy A: Ranges (80-100k)
    # matches like "80-100k" or "80k - 100k"
    matches_k_range = re.finditer(r'(\d+)\s*[-–to]\s*(\d+)\s*[kK]', text_lower)
    for m in matches_k_range:
        if is_safe_match(m):
            n1 = int(m.group(1))
            n2 = int(m.group(2))
            clean_numbers.extend([n1 * 1000, n2 * 1000])

    # Strategy B: Individual numbers (60k, 60,000)
    # Only run if Strategy A found nothing (to avoid double counting)
    if not clean_numbers:
        matches = re.finditer(r'(\d+[,\.]?\d*)\s*([kK])?', text_lower)
        for m in matches:
            if not is_safe_match(m):
                continue

            num_str = m.group(1)
            suffix = m.group(2)

            clean_str = num_str.replace(',', '').replace('.', '')
            if not clean_str.isdigit(): continue

            val = float(clean_str)
            if suffix and suffix.lower() == 'k': val *= 1000

            clean_numbers.append(val)

    if not clean_numbers:
        return None, None, None

    salary_min = min(clean_numbers)
    salary_max = max(clean_numbers) if len(clean_numbers) > 1 else salary_min

    return salary_min, salary_max, currency