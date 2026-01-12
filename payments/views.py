import stripe
import sys
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from rest_framework_api_key.models import APIKey
from django.contrib.auth.mixins import LoginRequiredMixin

stripe.api_key = settings.STRIPE_SECRET_KEY


# --- ADD THIS DECORATOR HERE ---
@method_decorator(csrf_exempt, name='dispatch')
class CreateCheckoutSessionView(View):
    """
    1. Frontend calls this to get a payment URL.
    2. We redirect user to Stripe.
    """
    def post(self, request, *args, **kwargs):
        domain_url = 'http://localhost:8000'
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': settings.STRIPE_PRICE_ID,
                    'quantity': 1,
                }],
                mode='subscription',
                #Redirect back to Dashboard with a flag
                success_url=domain_url + '/dashboard/?success=true',
                cancel_url=domain_url + '/dashboard/?canceled=true',

                client_reference_id=request.user.id,
                customer_email=request.user.email,
            )
            return redirect(checkout_session.url)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        event = None

        print(f"🔔 WEBHOOK RECEIVED! Signature: {sig_header[:10]}...", file=sys.stderr)

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            print("❌ Error: Invalid Payload", file=sys.stderr)
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            print("❌ Error: Invalid Signature (Check STRIPE_WEBHOOK_SECRET in settings.py)", file=sys.stderr)
            return HttpResponse(status=400)

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            customer_email = session.get('customer_details', {}).get('email')

            print(f"💰 Payment confirmed for: {customer_email}", file=sys.stderr)

            if customer_email:
                # CRITICAL FIX: Remove existing keys to prevent duplicates
                existing_keys = APIKey.objects.filter(name=customer_email)
                if existing_keys.exists():
                    print(f"⚠️ Found {existing_keys.count()} old keys. Revoking them...", file=sys.stderr)
                    existing_keys.delete()

                # Generate New Key
                api_key, key_string = APIKey.objects.create_key(name=customer_email)
                print(f"✅ SUCCESS: Generated New Key for {customer_email}", file=sys.stderr)

                # Send Email
                send_mail(
                    subject="Your Remote Jobs API Key 🚀",
                    message=f"Thanks for upgrading!\n\nYour API Key is: {key_string}\n\nKeep it safe!",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[customer_email],
                    fail_silently=True,
                )

        return HttpResponse(status=200)