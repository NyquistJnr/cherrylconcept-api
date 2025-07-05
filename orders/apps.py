from django.apps import AppConfig

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.UUIDField'
    name = 'orders'
    
    def ready(self):
        import orders.signals
