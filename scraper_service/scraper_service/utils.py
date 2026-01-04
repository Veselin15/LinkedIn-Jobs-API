import re

# 1. Define the Skills List (Add more as you see fit)
TECH_KEYWORDS = [
    "Python", "Django", "Flask", "FastAPI", "React", "Angular", "Vue", "Node.js",
    "JavaScript", "TypeScript", "HTML", "CSS", "SQL", "PostgreSQL", "MySQL",
    "Redis", "MongoDB", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Linux",
    "Git", "CI/CD", "Machine Learning", "AI", "Data Science", "Pandas", "NumPy",
    "Scikit-learn", "TensorFlow", "PyTorch", "Celery", "RabbitMQ", "GraphQL",
    "REST API", "DevOps", "Terraform", "Ansible", "C++", "Java", "Go", "Rust"
]


def extract_skills(text):
    """
    Scans the text for keywords and returns a list of unique matches.
    """
    if not text:
        return []

    found_skills = set()
    text_lower = text.lower()

    for skill in TECH_KEYWORDS:
        # Use regex to find whole words only (avoids matching "Go" in "Google")
        # re.escape handles special chars like C++
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'

        # C++ and C# need special handling because boundaries \b ignore + and #
        if skill in ["C++", "C#"]:
            if skill.lower() in text_lower:
                found_skills.add(skill)
        elif re.search(pattern, text_lower):
            found_skills.add(skill)

    return list(found_skills)


def parse_salary(text):
    if not text:
        return None, None, None

    # Identify Currency
    currency = "USD"
    if '€' in text or 'EUR' in text:
        currency = "EUR"
    elif '£' in text or 'GBP' in text:
        currency = "GBP"

    # Strategy A: Ranges (80-100k)
    matches_k_range = re.search(r'(\d+)\s*[-–to]\s*(\d+)\s*[kK]', text)
    clean_numbers = []

    if matches_k_range:
        n1 = int(matches_k_range.group(1))
        n2 = int(matches_k_range.group(2))
        clean_numbers = [n1 * 1000, n2 * 1000]
    else:
        # Strategy B: Individual numbers (60k, 60,000)
        matches = re.findall(r'(\d+[,\.]?\d*)\s*([kK])?', text)
        for num_str, suffix in matches:
            clean_str = num_str.replace(',', '').replace('.', '')
            if not clean_str.isdigit(): continue
            val = float(clean_str)
            if suffix and suffix.lower() == 'k': val *= 1000
            if 15000 < val < 500000:  # Sanity check
                clean_numbers.append(int(val))

    if not clean_numbers:
        return None, None, None

    salary_min = min(clean_numbers)
    salary_max = max(clean_numbers) if len(clean_numbers) > 1 else salary_min

    return salary_min, salary_max, currency