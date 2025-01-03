import stripe
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .handlers import stripe_webhook_handlers
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def stripe_webhook(request, hook_uuid):
    """Stripe webhook endpoint."""
    payload = request.body.decode("utf-8")
    received_sig = request.headers.get("Stripe-Signature", None)
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    # Validate the webhook UUID
    if str(hook_uuid) != settings.STRIPE_WEBHOOK_UUID:
        logger.warning(
            f"Received webhook with invalid UUID: {hook_uuid}. "
            f"Expected: {settings.STRIPE_WEBHOOK_UUID}"
        )
        return JsonResponse({"error": "Unconfigured endpoint"}, status=404)

    try:
        # Verify and construct the Stripe event
        event = stripe.Webhook.construct_event(payload, received_sig, webhook_secret)
    except ValueError:
        logger.error("Invalid payload received for Stripe webhook.")
        return JsonResponse({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature for Stripe webhook.")
        return JsonResponse({"error": "Invalid signature"}, status=400)

    event_type = event["type"]
    event_id = event["id"]
    logger.info(f"Stripe webhook received: id={event_id}, type={event_type}")

    # Dispatch the event to all registered handlers
    handlers = stripe_webhook_handlers.get(event_type, [])
    if handlers:
        for handler in handlers:
            try:
                handler(event)
                logger.info(f"Successfully handled event: {event_type} with {handler.__name__}")
            except Exception as e:
                logger.error(f"Error in handler {handler.__name__} for event {event_type}: {e}")
                # Let Stripe retry by returning success; detailed errors are logged
    else:
        logger.warning(f"No handlers registered for event type: {event_type}")

    return JsonResponse({"status": "success"}, status=200)
