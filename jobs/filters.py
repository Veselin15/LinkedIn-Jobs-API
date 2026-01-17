import django_filters
import re
from .models import Job

class JobFilter(django_filters.FilterSet):
    # Standard text searches
    title = django_filters.CharFilter(lookup_expr='icontains')
    company = django_filters.CharFilter(lookup_expr='icontains')
    location = django_filters.CharFilter(lookup_expr='icontains')
    seniority = django_filters.CharFilter(lookup_expr='icontains')
    source = django_filters.CharFilter(lookup_expr='icontains')

    # Salary Filter (Greater than or equal to)
    salary_min = django_filters.NumberFilter(field_name='salary_min', lookup_expr='gte')

    # Custom Skills Filter (Search inside JSON List)
    skills = django_filters.CharFilter(method='filter_skills')

    class Meta:
        model = Job
        fields = ['title', 'company', 'location', 'skills', 'seniority', 'salary_min', 'source']

    def filter_skills(self, queryset, name, value):
        """
        Searches for a specific skill inside the JSONField list.
        Example: Searching for 'Java' matches ["Java", "Python"] but NOT ["JavaScript"].
        """
        if not value:
            return queryset

        # We search for the exact string wrapped in quotes inside the JSON structure
        return queryset.filter(skills__iregex=f'"{re.escape(value)}"')