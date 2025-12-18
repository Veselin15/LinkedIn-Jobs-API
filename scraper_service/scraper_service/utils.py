import re


def parse_salary(text):
    if not text:
        return None, None, None

    # 1. Identify Currency
    currency = "USD"  # Default
    if '€' in text or 'EUR' in text:
        currency = "EUR"
    elif '£' in text or 'GBP' in text:
        currency = "GBP"

    # 2. Strategy A: Look for explicit "k" pattern (e.g. 80k, 80-100k)
    # This finds "80" and "100k"
    matches_k = re.findall(r'(\d+[,\.]?\d*)\s*[-–to]*\s*(\d+[,\.]?\d*)\s*([kK])', text)

    clean_numbers = []

    if matches_k:
        # If we found a range like "80-100k", assume both are thousands
        for m in matches_k:
            num1 = float(m[0].replace(',', '').replace('.', ''))
            num2 = float(m[1].replace(',', '').replace('.', ''))
            clean_numbers.append(int(num1 * 1000))
            clean_numbers.append(int(num2 * 1000))

    # 2. Strategy B: Look for full numbers (e.g. 60,000)
    if not clean_numbers:
        matches_full = re.findall(r'(\d{2,3}[,\.]\d{3})', text)
        for num_str in matches_full:
            val = float(num_str.replace(',', '').replace('.', ''))
            # Sanity check: salaries usually between 10k and 500k
            if 10000 < val < 500000:
                clean_numbers.append(int(val))

    if not clean_numbers:
        return None, None, None

    salary_min = min(clean_numbers)
    salary_max = max(clean_numbers)

    return salary_min, salary_max, currency