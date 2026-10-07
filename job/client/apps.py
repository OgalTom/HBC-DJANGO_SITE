from django.apps import AppConfig


class ClientConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "client"
    verbose_name = "Editorials & Content"

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.contrib import admin as django_admin

        from . import admin as admin_module
        from .models import Application, BlogPost, GalleryItem, Job, Partner, PlatformUser, PublicUser, Story, Transaction

        User = get_user_model()
        registry = getattr(django_admin.site, "_registry", {})

        if User not in registry:
            django_admin.site.register(User, admin_module.UserAdmin)
        if PublicUser not in registry:
            django_admin.site.register(PublicUser, admin_module.PublicUserAdmin)
        if PlatformUser not in registry:
            django_admin.site.register(PlatformUser, admin_module.PlatformUserAdmin)
        if Story not in registry:
            django_admin.site.register(Story, admin_module.StoryAdmin)
        if BlogPost not in registry:
            django_admin.site.register(BlogPost, admin_module.BlogPostAdmin)
        if GalleryItem not in registry:
            django_admin.site.register(GalleryItem, admin_module.GalleryItemAdmin)
        if Partner not in registry:
            django_admin.site.register(Partner, admin_module.PartnerAdmin)
        if Job not in registry:
            django_admin.site.register(Job, admin_module.JobAdmin)
        if Application not in registry:
            django_admin.site.register(Application, admin_module.ApplicationAdmin)
        if Transaction not in registry:
            django_admin.site.register(Transaction, admin_module.TransactionAdmin)