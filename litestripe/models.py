import json
from django.db import models

class OrphanedPayment(models.Model):
    """
    This shouldn't happen, but just in case it does, it's a big deal. So we make space for it.
    All stripe payment links / buttons must include client-reference-id / client_reference_id
        which you must have as a guid on your user or user profile object (so it can maintain a 1:1 map)
    If for any reason the checkout.session.completed event, which per spec will contain this id,
        does not send it to us in the webhook, then an entry here (new OrphanedPayment) is created.

    Best practice beyond stashing these would be to setup a signal and email admins. Never leave a
        paying customer behind!
    """
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)
    customer_email = models.EmailField(null=True, blank=True)
    event = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, null=True, blank=True)  # Reason for orphaned payment

    dt_created = models.DateTimeField(auto_now_add=True)                # automatic/django ORM
    dt_last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Orphaned Payment (pk: {self.pk}): {self.stripe_customer_id} ({self.customer_email})"

class StripeSubscription(models.Model):
    """
    A singular object with no SPI/PII which contains the necessary mappings
    between the various essential elements that facilitate stripe+app integration.
    """

    stripe_customer_id = models.CharField(max_length=512)               # checkout.session.completed
    client_reference_id = models.CharField(max_length=1024)             # checkout.session.completed
    stripe_subscription_id = models.CharField(max_length=512)           # checkout.session.completed
    created = models.DateTimeField(blank=True, null=True)               # customer.subscription.updated
    start_date = models.DateTimeField(blank=True, null=True)            # customer.subscription.updated
    cancel_at = models.DateTimeField(blank=True, null=True)             # customer.subscription.updated
    cancelled_at = models.DateTimeField(blank=True, null=True)          # customer.subscription.updated
    cancel_at_period_end = models.BooleanField(blank=True, null=True)   # customer.subscription.updated
    status = models.CharField(max_length=256)                           # customer.subscription.updated
    metadata = models.TextField(blank=True, null=True)                  # JSON-encoded metadata e.g., {'checkout.session.completed.points_limit: 10'} 
                                                                        #   if payment link conains this metadata kv pair.
    dt_created = models.DateTimeField(auto_now_add=True)                # automatic/django ORM
    dt_last_updated = models.DateTimeField(auto_now=True)

    def get_metadata(self):
        """Parse metadata field as JSON."""
        return json.loads(self.metadata) if self.metadata else {}

    def set_metadata(self, key, value):
        """Set a metadata value."""
        data = self.get_metadata()
        data[key] = value
        self.metadata = json.dumps(data)

    def get_metadata_key(self, key):
        """Retrieve a specific key from metadata."""
        return self.get_metadata().get(key)

    def __str__(self):
        if self.stripe_subscription_id:
            return f"StripeSubscription: {self.stripe_subscription_id}"
        return f"StripeSubscription (PK: {self.pk})"
