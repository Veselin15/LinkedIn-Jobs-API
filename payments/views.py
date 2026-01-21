import stripe
import sys
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages  # <--- NEW: To show errors
from rest_framework_api_key.models import APIKey
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import UserSubscription

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY


class CreateCheckoutSessionView(LoginRequiredMixin, View):
    """
    Redirects the user to Stripe to pay.
    """

    def post(self, request, *args, **kwargs):
        domain_url = settings.SITE_URL

        # 1. Determine Plan
        plan_type = request.POST.get('plan', 'pro')

        # 2. Select Price ID
        if plan_type == 'business':
            price_id = getattr(settings, 'STRIPE_PRICE_ID_BUSINESS', None)
        else:
            price_id = getattr(settings, 'STRIPE_PRICE_ID_PRO', getattr(settings, 'STRIPE_PRICE_ID', None))

        if not price_id:
            messages.error(request, "Configuration Error: Price ID missing.")
            return redirect('dashboard')

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=domain_url + '/dashboard/?success=true',
                cancel_url=domain_url + '/dashboard/?canceled=true',
                customer_email=request.user.email,
                client_reference_id=request.user.id,
                metadata={
                    'plan_type': plan_type
                }
            )
            return redirect(checkout_session.url)
        except Exception as e:
            messages.error(request, f"Stripe Error: {str(e)}")
            return redirect('dashboard')


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """
    Handles Stripe Events:
    1. New Subscriptions (checkout.session.completed)
    2. Plan Changes (customer.subscription.updated) <--- NEW!
    3. Cancellations (customer.subscription.deleted)
    """

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        event = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            return HttpResponse(status=400)

        # --- EVENT 1: NEW PURCHASE ---
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            customer_email = session.get('customer_details', {}).get('email')
            stripe_customer_id = session.get('customer')

            metadata = session.get('metadata', {})
            plan_type = metadata.get('plan_type', 'pro')

            if customer_email:
                try:
                    user = User.objects.get(email=customer_email)
                    UserSubscription.objects.update_or_create(
                        user=user,
                        defaults={
                            'plan_type': plan_type,
                            'stripe_customer_id': stripe_customer_id
                        }
                    )
                    # Refresh API Key
                    APIKey.objects.filter(name=customer_email).delete()
                    _, key_string = APIKey.objects.create_key(name=customer_email)

                    send_mail(
                        subject="Welcome to TechJobsData!",
                        message=f"Your {plan_type.upper()} plan is active.\nAPI Key: {key_string}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[customer_email],
                        fail_silently=True,
                    )
                except User.DoesNotExist:
                    pass

        # --- EVENT 2: PLAN SWITCH / UPDATE (The Fix) ---
        elif event['type'] == 'customer.subscription.updated':
            session = event['data']['object']
            customer_id = session.get('customer')

            # Find which plan corresponds to the new Price ID
            # Stripe sends a list of items; usually the first one is the plan.
            try:
                current_price_id = session['items']['data'][0]['price']['id']

                # Map Price ID -> Plan Name
                new_plan_type = 'pro'  # default fallback
                if current_price_id == getattr(settings, 'STRIPE_PRICE_ID_BUSINESS', 'xxx'):
                    new_plan_type = 'business'
                elif current_price_id == getattr(settings, 'STRIPE_PRICE_ID_PRO', 'xxx'):
                    new_plan_type = 'pro'

                # Update Database
                print(f"🔄 Syncing Plan Update: {customer_id} -> {new_plan_type}", file=sys.stderr)
                UserSubscription.objects.filter(stripe_customer_id=customer_id).update(plan_type=new_plan_type)

            except Exception as e:
                print(f"Error syncing subscription update: {e}", file=sys.stderr)

        # --- EVENT 3: CANCELLATION ---
        elif event['type'] == 'customer.subscription.deleted':
            session = event['data']['object']
            customer_id = session.get('customer')

            try:
                sub = UserSubscription.objects.filter(stripe_customer_id=customer_id).first()
                if sub:
                    # Downgrade logic
                    sub.plan_type = 'free'
                    sub.save()
                    APIKey.objects.filter(name=sub.user.email).delete()
            except Exception:
                pass

        return HttpResponse(status=200)
class StripePortalView(LoginRequiredMixin, View):
    """
    Redirects to Stripe Billing Portal.
    Now handles errors gracefully!
    """

    def post(self, request, *args, **kwargs):
        domain_url = settings.SITE_URL
        customer_id = None

        # 1. Try to get ID from our Database (Best Method)
        if hasattr(request.user, 'subscription'):
            customer_id = request.user.subscription.stripe_customer_id

        # 2. If missing, ask Stripe (Fallback Method)
        if not customer_id:
            try:
                customers = stripe.Customer.list(email=request.user.email, limit=1)
                if customers.data:
                    customer_id = customers.data[0].id
            except Exception:
                pass

        # 3. If still no ID, they probably never paid via Stripe
        if not customer_id:
            messages.error(request, "No billing account found. Have you subscribed yet?")
            return redirect('dashboard')

        try:
            # 4. Create the Portal Session
            portal_session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=domain_url + '/dashboard/',
            )
            return redirect(portal_session.url)

        except Exception as e:
            messages.error(request, f"Billing Portal Error: {str(e)}")
            return redirect('dashboard')