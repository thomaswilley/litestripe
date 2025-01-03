from django.urls import path
from .views import stripe_webhook

urlpatterns = [
    path("ls/hook/<uuid:hook_uuid>/", stripe_webhook, name="stripe-webhook"),
]
