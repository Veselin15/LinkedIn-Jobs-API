"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from jobs.views import JobListAPI, ScrapeTriggerAPI
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
urlpatterns = [
    path('admin/', admin.site.urls),
# 1. The Core App (Home & Dashboard)
    path('', include('core.urls')),
    # 2. Authentication (Login/Logout/Password Reset) - FREE from Django!
    path('accounts/', include('django.contrib.auth.urls')),
    # 3. Your API
    path('api/jobs/', include('jobs.urls')), # Assuming you have a jobs/urls.py, or link directly to view
    path('api/payments/', include('payments.urls')),
    path('api/jobs/', JobListAPI.as_view(), name='job-list'),

    # New Endpoint for triggering scrapes
    path('api/scrape/', ScrapeTriggerAPI.as_view(), name='job-scrape'),

# --- Swagger Documentation ---
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # This is the magic link:
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

# --- Payments ---
    path('api/payments/', include('payments.urls')),
]