import re


def parse_salary(text):
    if not text:
        return None, None, None

    # Pattern for "60k - 80k" or "60000 - 80000"
    pattern = re.compile(r'(\d+)[kK]?\s*[-–to]\s*(\d+)[kK]?')
    match = pattern.search(text)

    if match:
        min_sal = int(match.group(1).replace('k', '000'))
        max_sal = int(match.group(2).replace('k', '000'))
        # Normalize: if someone writes "60 - 80k", assume they mean "60k"
        if min_sal < 1000: min_sal *= 1000

        return min_sal, max_sal, "EUR"  # Defaulting currency for now

    return None, None, None