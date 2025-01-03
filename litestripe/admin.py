from django.contrib import admin
from .models import OrphanedPayment, StripeSubscription

admin.site.register(OrphanedPayment)
admin.site.register(StripeSubscription)
