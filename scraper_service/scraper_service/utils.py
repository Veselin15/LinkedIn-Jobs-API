import re


def parse_salary(text):
    if not text:
        return None, None, None

    # 1. Identify Currency (Default to USD, but check for others)
    currency = "USD"
    if '€' in text or 'EUR' in text:
        currency = "EUR"
    elif '£' in text or 'GBP' in text:
        currency = "GBP"

    # 2. Strategy A: Look for "k" ranges (e.g., "80-100k", "80k - 100k")
    # This regex looks for two numbers separated by a dash/to, where the second one has a 'k'
    matches_k_range = re.search(r'(\d+)\s*[-–to]\s*(\d+)\s*[kK]', text)

    clean_numbers = []

    if matches_k_range:
        # If found (e.g. "80-100k"), treat both as thousands
        n1 = int(matches_k_range.group(1))
        n2 = int(matches_k_range.group(2))
        clean_numbers = [n1 * 1000, n2 * 1000]
    else:
        # 3. Strategy B: Look for explicit individual numbers (e.g. "60k", "60,000")
        # Finds "60k" OR "60,000"
        matches = re.findall(r'(\d+[,\.]?\d*)\s*([kK])?', text)

        for num_str, suffix in matches:
            # Clean punctuation (remove commas/dots)
            clean_str = num_str.replace(',', '').replace('.', '')

            # Skip if it's not a number (safety check)
            if not clean_str.isdigit(): continue

            val = float(clean_str)

            # Handle 'k' suffix
            if suffix and suffix.lower() == 'k':
                val *= 1000

            # Sanity Filter: Salaries are usually between 10,000 and 500,000
            # This ignores year numbers like "2024" or small hourly rates
            if 15000 < val < 500000:
                clean_numbers.append(int(val))

    # 4. Determine Min/Max
    if not clean_numbers:
        return None, None, None

    salary_min = min(clean_numbers)
    # If we only found one number (e.g. "80k"), max is the same as min
    salary_max = max(clean_numbers) if len(clean_numbers) > 1 else salary_min

    return salary_min, salary_max, currency