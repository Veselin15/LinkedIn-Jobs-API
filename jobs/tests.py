from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import Job


class JobSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create test data
        Job.objects.create(
            title="Senior Python Developer",
            company="Tech Corp",
            description="We need a backend expert.",
            skills=["Python", "Django"],
            url="http://example.com/1"
        )
        Job.objects.create(
            title="Java Engineer",
            company="Old School Inc",
            description="Enterprise java applications.",
            url="http://example.com/2"
        )
        Job.objects.create(
            title="Frontend React Dev",
            company="Tech Corp",
            description="React and Redux.",
            url="http://example.com/3"
        )

    def test_search_stemming(self):
        """
        Test if searching for 'developing' finds 'Developer' (stemming).
        This confirms that Postgres SearchVector is working, not just icontains.
        """
        url = reverse('job-list')  # Ensure name='job-list' is in urls.py
        response = self.client.get(url, {'search': 'developing'})  # Search for a related word

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data

        # Should find 'Senior Python Developer'
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Senior Python Developer")

    def test_search_company_weight(self):
        """
        Test searching by company name.
        """
        url = reverse('job-list')
        response = self.client.get(url, {'search': 'Tech Corp'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 2)