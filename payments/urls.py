from django.urls import path
from .views import CreateCheckoutSessionView, StripeWebhookView, StripePortalView

urlpatterns = [
    path('create-checkout-session/', CreateCheckoutSessionView.as_view(), name='checkout'),
    path('webhook/', StripeWebhookView.as_view(), name='webhook'),
    path('create-portal-session/', StripePortalView.as_view(), name='billing_portal'),
]
