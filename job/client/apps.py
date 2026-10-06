from django.apps import AppConfig


class ClientConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "client"
    def ready(self):
        from django.contrib.auth import get_user_model
        from . import admin as admin_module
        from .models import Job, Application, Transaction

        User = get_user_model()

        from django.contrib import admin as django_admin

        registry = getattr(django_admin.site, "_registry", {})

        if User not in registry:
            django_admin.site.register(User, admin_module.UserAdmin)
        if Job not in registry:
            django_admin.site.register(Job, admin_module.JobAdmin)
        if Application not in registry:
            django_admin.site.register(Application, admin_module.ApplicationAdmin)
        if Transaction not in registry:
            django_admin.site.register(Transaction, admin_module.TransactionAdmin)