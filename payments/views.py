import stripe
import sys
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework_api_key.models import APIKey

stripe.api_key = settings.STRIPE_SECRET_KEY


class CreateCheckoutSessionView(LoginRequiredMixin, View):
    """
    Redirects the user to Stripe to pay.
    """

    def post(self, request, *args, **kwargs):
        domain_url = 'http://localhost:8000'  # Update this when you deploy!
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': settings.STRIPE_PRICE_ID,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=domain_url + '/dashboard/?success=true',
                cancel_url=domain_url + '/dashboard/?canceled=true',
                # We tag the transaction with the User's Email so the Webhook knows who it is
                customer_email=request.user.email,
                client_reference_id=request.user.id,
            )
            return redirect(checkout_session.url)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """
    The Brain of your Payment System.
    Handles:
    1. New Subscriptions -> Generates Key
    2. Cancelled Subscriptions -> Deletes Key
    """

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        event = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            return HttpResponse(status=400)

        # --- EVENT 1: NEW SUBSCRIPTION (Payment Success) ---
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            customer_email = session.get('customer_details', {}).get('email')

            if customer_email:
                print(f"💰 New Subscription for: {customer_email}", file=sys.stderr)

                # 1. Clear any old keys to avoid duplicates
                APIKey.objects.filter(name=customer_email).delete()

                # 2. Create the new Premium Key
                api_key, key_string = APIKey.objects.create_key(name=customer_email)

                # 3. Email it
                send_mail(
                    subject="Your Remote Jobs API Key 🚀",
                    message=f"Welcome to Premium!\n\nYour API Key is: {key_string}\n\nKeep it safe!",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[customer_email],
                    fail_silently=True,
                )

        # --- EVENT 2: SUBSCRIPTION ENDED (User Cancelled or Payment Failed) ---
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            # Stripe sends the Customer ID, not the email, so we must fetch it
            customer_id = subscription.get('customer')

            try:
                # Ask Stripe "Who is this customer?"
                customer = stripe.Customer.retrieve(customer_id)
                customer_email = customer.get('email')

                if customer_email:
                    print(f"❌ Subscription Cancelled for: {customer_email}. Revoking access...", file=sys.stderr)

                    # 1. REVOKE ACCESS (Delete Key)
                    deleted_count, _ = APIKey.objects.filter(name=customer_email).delete()

                    # 2. Send Goodbye Email
                    if deleted_count > 0:
                        send_mail(
                            subject="Your Subscription has Ended 😢",
                            message="Your subscription has been cancelled and your API Key is now inactive.\n\nThank you for trying our service!",
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[customer_email],
                            fail_silently=True,
                        )
            except Exception as e:
                print(f"Error handling cancellation: {e}", file=sys.stderr)

        return HttpResponse(status=200)