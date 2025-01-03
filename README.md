# litestripe

A fast, user privacy–preserving, lightweight integration for Stripe subscriptions in your Django application.

Litestripe manages fully encapsulated `StripeSubscription` and `OrphanedPayment` models for your application's user transactions.  
Your application can access these (real-time or otherwise) via Django signals.  
Stripe metadata set on payment links is automatically stashed on the `StripeSubscription` model, including special handling for `client_reference_id`.

**Key points:**
- The `StripeSubscription` object contains no SPI/PII (or is designed not to).
- The `OrphanedPayment` object contains an email, specifically to enable fixing entitlement for a paying customer if no `guid` match occurs.
- Litestripe relies heavily on Stripe itself to handle sensitive information; we just store minimal references for subscription status and correlation.

---

## How it Works

### Models:
`StripeSubscription`: Contains all relevant subscription data, including metadata.
`OrphanedPayment`: Captures “should never happen” scenarios where a subscription can’t be matched to a user.

### Webhook Handling:
Litestripe intercepts Stripe subscription events (e.g. `customer.subscription.created`, `customer.subscription.updated`, `checkout.session.completed`) and updates your subscription records automatically.

### Signal Integration:
If you want real-time hooks, you can use standard Django signals on these
models (e.g., post_save) to react to subscription changes or orphaned payment
events. If you need a deeper, full sync with Stripe (including all objects,
invoices, etc.), consider an alternative like dj-stripe. However, if you only
need minimal Stripe subscription data in your app, Litestripe keeps it lean and
straightforward.

### Summary
1. Install with pip install git+https://github.com/<your-username>/litestripe.git.
2. Add 'litestripe.apps.LitestripeConfig' to INSTALLED_APPS.
3. Set up your environment variables (STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_UUID, etc.).
4. Run migrations to create the Litestripe models.
5. (Optional) Use Docker + Stripe CLI for local webhook integration.
6. Leverage the StripeSubscription and OrphanedPayment models in your Django signals or views as needed.

---

## Get Started

```bash
pip install git+https://github.com/<your-username>/litestripe.git
```

In your Django project's settings.py, add:

```python
INSTALLED_APPS = [
    ...
    'litestripe.apps.LitestripeConfig',
    ...
]
```
Then run migrations:

```bash
python manage.py migrate
```

To use the OrphanedPayment and StripeSubscription models, simply import them in your signals, views, or wherever else:

```python
from litestripe.models import OrphanedPayment, StripeSubscription
```

Configuration
1. .env (Environment Variables)
Below is a minimal set of environment variables you might include in your .env file:

```makefile
# Stripe keys
STRIPE_PUBLIC_KEY=pk_test_1234567890
STRIPE_SECRET_KEY=sk_test_1234567890
STRIPE_WEBHOOK_UUID=123e4567-e89b-12d3-a456-426655440000

# Litestripe config
LITESTRIPE_API_RATE_LIMIT_CACHE_KEY=litestripe_stripe_api_rate_limit
LITESTRIPE_MAX_REQUESTS_PER_MINUTE=75
```
(This example .env would typically live at the root of your project. Adapt as needed for production or local dev.)

2. settings.py
In your Django settings, make sure you read the environment variables (and optionally fetch the webhook secret from a file for local dev). Example snippet:

```python
import os
import re
import time

# Stripe environment variables
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_UUID = os.getenv('STRIPE_WEBHOOK_UUID', None)

# Litestripe rate-limiting config
LITESTRIPE_API_RATE_LIMIT_CACHE_KEY = os.getenv(
    'LITESTRIPE_API_RATE_LIMIT_CACHE_KEY',
    'litestripe_stripe_api_rate_limit'
)
LITESTRIPE_MAX_REQUESTS_PER_MINUTE = int(
    os.getenv('LITESTRIPE_MAX_REQUESTS_PER_MINUTE', '75')
)

# Optionally read the actual Stripe Webhook Secret from Docker or environment
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

def get_webhook_secret_from_file(file_path, max_retries=10, delay=2):
    """
    Reads a Stripe webhook secret from a file with retries (useful in local Docker dev).
    """
    secret_pattern = r"whsec_[a-zA-Z0-9]+"
    for _ in range(max_retries):
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                match = re.search(secret_pattern, content)
                if match:
                    return match.group(0)
        time.sleep(delay)
    return None

if not STRIPE_WEBHOOK_SECRET:
    # e.g., Docker container with stripe-cli writing to /run/secrets_djstripe/djstripe_webhook_secret
    secret_file_path = '/run/secrets_djstripe/djstripe_webhook_secret'
    STRIPE_WEBHOOK_SECRET = get_webhook_secret_from_file(secret_file_path) or ''

if not STRIPE_WEBHOOK_SECRET:
    raise RuntimeError("Unable to find STRIPE_WEBHOOK_SECRET. Check your configuration.")
```

Adjust the paths, function logic, or error handling to match your specific use case.
Note: If you have a simpler environment (e.g., pure local dev without Docker secrets), you can simply set STRIPE_WEBHOOK_SECRET in your .env.

##### Local Development with Docker + stripe-cli

The recommended development setup for Litestripe is Docker containerization
with the official Stripe CLI forwarding webhooks to your local Django app.
You’d typically start it by running:

```bash
docker compose --env-file .env.dev -f compose.yml --profile dev up --build -d
```

Check container logs to ensure it starts properly and that the ephemeral webhook secret is being written to /run/secrets_djstripe/djstripe_webhook_secret.

Example docker-compose.yml Service Snippet
```yaml
services:
  stripe-cli-listener:
    image: stripe/stripe-cli:latest
    profiles:
      - dev
    volumes:
      - dev-djstripe-whsecret:/run/secrets_djstripe
      - nginx-webapp-socket:/run/wsgi:rw
    environment:
      - STRIPE_API_KEY      # or pass in ${STRIPE_SECRET_KEY} from .env
      - DJANGO_APP_PORT     # whichever port your Django app is on
      - STRIPE_DEVICE_NAME  # name your device for reference
      - STRIPE_WEBHOOK_UUID # a valid UUID4 used to route the webhook path
    networks:
      - internal_private
    entrypoint: /bin/sh -c
    command: >
      "export KEY=$$(stripe listen --api-key ${STRIPE_SECRET_KEY} --print-secret) && \
      echo $$KEY > /run/secrets_djstripe/djstripe_webhook_secret && \
      echo \"Got whsec key [$$KEY] and also saved to file: $$(cat /run/secrets_djstripe/djstripe_webhook_secret)\" && \
      stripe listen \
      --api-key ${STRIPE_SECRET_KEY} \
      --forward-to https://nginx/ls/hook/${STRIPE_WEBHOOK_UUID}/ \
      -H 'Host: your-app-local-uri' \
      -H \"x-djstripe-webhook-secret: $$KEY\" \
      --skip-verify"
```
Where:

`https://nginx/ls/hook/${STRIPE_WEBHOOK_UUID}/` is your Django endpoint (defined by Litestripe’s urls.py).
Volumes and networks are shared to allow your Django container to read the whsec_... secret.
The container prints the ephemeral secret and also writes it to `/run/secrets_djstripe/djstripe_webhook_secret`.


