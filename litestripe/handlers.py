from functools import wraps
from datetime import datetime, timezone  # Import timezone directly from datetime
from django.utils.timezone import make_aware
from .models import OrphanedPayment, StripeSubscription
import logging

logger = logging.getLogger(__name__)

# A registry for webhook handlers
stripe_webhook_handlers = {}


def convert_to_datetime(timestamp):
    """Convert a Unix timestamp to a timezone-aware Python datetime object in UTC."""
    if timestamp:
        naive_dt = datetime.fromtimestamp(timestamp)  # Convert to naive datetime
        return make_aware(naive_dt, timezone=timezone.utc)  # Use Python's timezone.utc
    return None


def update_or_create_subscription(
    event_type, subscription_data, previous_attributes=None
):
    """Update or create a Stripe subscription record."""
    subscription_id = subscription_data.get("id")
    stripe_customer_id = subscription_data.get("customer")
    status = subscription_data.get("status")
    metadata = subscription_data.get("metadata", {})

    created_timestamp = subscription_data.get("created")
    start_date = subscription_data.get("start_date")
    cancel_at = subscription_data.get("cancel_at")
    cancelled_at = subscription_data.get("canceled_at")
    cancel_at_period_end = subscription_data.get("cancel_at_period_end")

    # Update or create the subscription record
    subscription, created = StripeSubscription.objects.get_or_create(
        stripe_subscription_id=subscription_id
    )

    # Check for subscription renewal
    def check_subscription_renewal(subscription, previous_attributes):
        """Check if a subscription has been renewed."""
        if previous_attributes:
            previous_cancel_at = previous_attributes.get("cancel_at")
            if previous_cancel_at:
                dt_previous_cancel_at = convert_to_datetime(previous_cancel_at)
                if (
                    dt_previous_cancel_at
                    and subscription.cancel_at == dt_previous_cancel_at
                ):
                    return True
        return False

    is_renewed = check_subscription_renewal(subscription, previous_attributes)

    # Update fields only if they are present
    if stripe_customer_id:
        subscription.stripe_customer_id = stripe_customer_id
    if created_timestamp is not None:
        subscription.created = convert_to_datetime(created_timestamp)
    if start_date is not None:
        subscription.start_date = convert_to_datetime(start_date)
    if cancel_at is not None or is_renewed:
        subscription.cancel_at = None if is_renewed else convert_to_datetime(cancel_at)
    if cancelled_at is not None or is_renewed:
        subscription.cancelled_at = (
            None if is_renewed else convert_to_datetime(cancelled_at)
        )
    if cancel_at_period_end is not None:
        subscription.cancel_at_period_end = cancel_at_period_end
    if status:
        subscription.status = status

    # Store metadata
    for key, value in metadata.items():
        subscription.set_metadata(f"{event_type}.{key}", value)

    if is_renewed:
        now = datetime.now().isoformat()
        subscription.set_metadata("litestripe.stripesubscription.last_renewed", now)
        logger.info(
            f"Renewal detected on {event_type} for subscription {subscription_id}"
            f"Renewal metadata entry added (litestripe.stripesubscription.last_renewed: {now}"
        )

    subscription.save()
    logger.info(
        f"Processed {event_type} for subscription {subscription_id}. "
        f"Metadata: {metadata}, Created: {created}"
    )


def orphaned_payment_handler(event_obj, stripe_customer_id, customer_email, reason):
    """Handle orphaned payments."""
    orphaned_payment = OrphanedPayment.objects.create(
        stripe_customer_id=stripe_customer_id,
        customer_email=customer_email,
        event=event_obj,
        reason=reason,  # Optional: Add a reason field in the OrphanedPayment model
    )
    logger.error(
        f"CRITICAL: Orphaned Payment {reason}. See OrphanedPayment object: {orphaned_payment}"
    )


# Primary Decorator
def stripe_webhook_handler(event_type):
    """Decorator to register Stripe webhook handlers."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Allow multiple handlers per event type
        if event_type not in stripe_webhook_handlers:
            stripe_webhook_handlers[event_type] = []
        stripe_webhook_handlers[event_type].append(wrapper)

        return wrapper

    return decorator


@stripe_webhook_handler("customer.subscription.created")
@stripe_webhook_handler("customer.subscription.updated")
def handle_customer_subscription_updated(event):
    """Handle customer.subscription.updated webhook."""
    subscription_data = event.data.object
    previous_data = event.data.previous_attributes or None
    event_type = event["type"]  # (keyerror thrown if missing)
    update_or_create_subscription(event_type, subscription_data, previous_data)


@stripe_webhook_handler("checkout.session.completed")
def handle_checkout_session_completed(event):
    """Handle checkout.session.completed webhook."""
    session = event.data.object
    subscription_id = session.get("subscription")  # Stripe subscription ID
    stripe_customer_id = session.get("customer")  # Stripe customer ID
    client_reference_id = session.get("client_reference_id")  # Custom reference ID
    metadata = session.get("metadata", {})  # Extract metadata from the session

    if not subscription_id:
        logger.warning("No subscription ID in checkout.session.completed event.")
        return

    # Update or create the subscription record
    subscription, created = StripeSubscription.objects.get_or_create(
        stripe_subscription_id=subscription_id
    )

    # Update fields only if they are present
    if stripe_customer_id:
        subscription.stripe_customer_id = stripe_customer_id
    if client_reference_id:
        subscription.client_reference_id = client_reference_id
    if session.get("created"):
        subscription.created = convert_to_datetime(session.get("created"))
    if metadata:
        for key, value in metadata.items():
            subscription.set_metadata(f"checkout.session.completed.{key}", value)

    subscription.save()
    logger.info(
        f"Processed checkout.session.completed for subscription {subscription_id}. "
        f"Metadata: {metadata}, Created: {created}"
    )
