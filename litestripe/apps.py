from django.apps import AppConfig


class LitestripeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'litestripe'
    label = 'litestripe'

    def ready(self):
        from litestripe import handlers # noqa: F401
