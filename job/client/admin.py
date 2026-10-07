from django.contrib import admin
from django.contrib.admin import AdminSite

from .models import (
    Application,
    Article,
    BlogPost,
    GalleryItem,
    Job,
    Partner,
    PlatformUser,
    PublicUser,
    Story,
    Transaction,
    User,
    UserAccessUnlock,
)

SECTION_ACCESS_PERMISSIONS = {
    "Public users": {"view_user", "change_user", "add_user", "delete_user"},
    "Platform users": {"view_user", "change_user", "add_user", "delete_user"},
    "Partners & trust": {"view_partner", "change_partner", "add_partner", "delete_partner"},
    "Stories & blog": {"view_story", "change_story", "add_story", "delete_story", "view_blogpost", "change_blogpost", "add_blogpost", "delete_blogpost", "view_article", "change_article", "add_article", "delete_article", "view_galleryitem", "change_galleryitem", "add_galleryitem", "delete_galleryitem"},
    "ATS / applicant tracking": {"view_application", "change_application", "add_application", "delete_application"},
    "Finance & access management": {"view_transaction", "change_transaction", "add_transaction", "delete_transaction", "view_useraccessunlock", "change_useraccessunlock", "add_useraccessunlock", "delete_useraccessunlock"},
}

ROLE_SECTION_ACCESS = {
    User.Role.ADMIN: {
        "Public users",
        "Platform users",
        "Partners & trust",
        "Stories & blog",
        "ATS / applicant tracking",
        "Finance & access management",
    },
    User.Role.ADMIN_SUPER: {
        "Public users",
        "Platform users",
        "Partners & trust",
        "Stories & blog",
        "ATS / applicant tracking",
        "Finance & access management",
    },
    User.Role.ADMIN_HANDLER: {
        "Public users",
        "Platform users",
        "Partners & trust",
        "Stories & blog",
        "ATS / applicant tracking",
        "Finance & access management",
    },
    User.Role.PARTNER: {"ATS / applicant tracking"},
    User.Role.CONTENT_MANAGER: {"Stories & blog", "Partners & trust"},
    User.Role.DIGITAL_MARKETING: {"Stories & blog", "Partners & trust"},
    User.Role.FINANCE_OFFICER: {"Finance & access management", "Platform users"},
    User.Role.ATS_COORDINATOR: {"ATS / applicant tracking"},
}


def user_has_section_access(user, section_name):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if not getattr(user, "is_staff", False):
        return False

    if section_name in ROLE_SECTION_ACCESS.get(getattr(user, "role", ""), set()):
        return True

    requested = SECTION_ACCESS_PERMISSIONS.get(section_name, set())
    if not requested:
        return True

    user_perm_codenames = set(
        user.user_permissions.values_list("codename", flat=True)
    )
    group_perm_codenames = set(
        user.groups.values_list("permissions__codename", flat=True)
    )

    return any(perm in user_perm_codenames or perm in group_perm_codenames for perm in requested)


class UserAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "role",
        "membership_tier",
        "neaims_status",
        "is_staff",
        "created_at",
    )
    list_filter = (
        "role",
        "membership_tier",
        "neaims_status",
        "is_staff",
        "is_active",
    )
    search_fields = (
        "first_name",
        "last_name",
        "email",
        "phone_number",
    )
    ordering = ("-created_at",)

    def save_model(self, request, obj, form, change):
        if obj.role in {
            User.Role.ADMIN,
            User.Role.ADMIN_SUPER,
            User.Role.ADMIN_HANDLER,
            User.Role.PARTNER,
            User.Role.CONTENT_MANAGER,
            User.Role.DIGITAL_MARKETING,
            User.Role.FINANCE_OFFICER,
            User.Role.ATS_COORDINATOR,
        }:
            obj.is_staff = True
        elif obj.role == User.Role.USER:
            obj.is_staff = False
        super().save_model(request, obj, form, change)


class PublicUserAdmin(UserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=User.Role.USER)


class PlatformUserAdmin(UserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            role__in=[
                User.Role.ADMIN,
                User.Role.ADMIN_SUPER,
                User.Role.ADMIN_HANDLER,
                User.Role.PARTNER,
                User.Role.CONTENT_MANAGER,
                User.Role.DIGITAL_MARKETING,
                User.Role.FINANCE_OFFICER,
                User.Role.ATS_COORDINATOR,
            ]
        )


class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "status",
        "is_published",
        "author_name",
        "published_at",
        "created_at",
    )
    list_filter = (
        "category",
        "status",
        "is_published",
        "author_name",
    )
    search_fields = (
        "title",
        "excerpt",
        "body",
        "author_name",
    )
    ordering = ("-published_at", "-created_at")
    prepopulated_fields = {"slug": ("title",)}


class StoryAdmin(ArticleAdmin):
    list_filter = ("status", "is_published", "author_name", "published_at")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(category=Article.Category.STORY)


class BlogPostAdmin(ArticleAdmin):
    list_filter = ("status", "is_published", "author_name", "published_at")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(category=Article.Category.BLOG)


class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "image_url", "created_at")
    list_filter = ("is_published",)
    search_fields = ("title", "description", "slug")
    ordering = ("-created_at",)
    prepopulated_fields = {"slug": ("title",)}


class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "is_published", "sort_order", "website", "created_at")
    list_editable = ("is_published", "sort_order")
    list_filter = ("is_published",)
    search_fields = ("name", "short_description", "website")
    ordering = ("sort_order", "name")


class JobAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "country",
        "sector",
        "status",
        "visibility",
        "salary_disclosed",
        "created_at",
    )
    list_editable = (
        "status",
        "visibility",
        "salary_disclosed",
    )
    list_filter = (
        "status",
        "visibility",
        "country",
        "sector",
        "salary_disclosed",
    )
    search_fields = (
        "title",
        "country",
        "sector",
        "description_masked",
        "description_full",
    )
    ordering = ("-created_at",)


class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "job",
        "current_country",
        "passport_number",
        "ats_stage",
        "document_status",
        "visa_readiness",
        "tier_2_paid",
        "tier_3_paid",
        "assigned_agent",
        "created_at",
    )
    list_editable = (
        "ats_stage",
        "document_status",
        "visa_readiness",
        "assigned_agent",
        "tier_2_paid",
        "tier_3_paid",
    )
    list_filter = (
        "ats_stage",
        "document_status",
        "visa_readiness",
        "tier_2_paid",
        "tier_3_paid",
        "assigned_agent__role",
    )
    search_fields = (
        "candidate__first_name",
        "candidate__last_name",
        "candidate__email",
        "job__title",
        "job__country",
        "passport_number",
    )
    ordering = ("-created_at",)


class UserAccessUnlockAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "tier",
        "source",
        "is_active",
        "granted_by",
        "payment_reference",
        "granted_at",
    )
    list_filter = (
        "tier",
        "source",
        "is_active",
        "granted_by",
    )
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email",
        "payment_reference",
        "notes",
    )
    ordering = ("-granted_at",)


class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "payment_tier",
        "amount",
        "currency",
        "payment_status",
        "provider_reference",
        "created_at",
    )
    list_filter = (
        "payment_tier",
        "payment_status",
        "currency",
    )
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email",
        "provider_reference",
    )
    ordering = ("-created_at",)


class HBCAdminSite(AdminSite):
    site_title = "HBC Job Majuu admin"
    site_header = "HBC Job Majuu admin"
    index_title = "Admin dashboard"

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label=app_label)
        grouped = []
        model_lookup = {}

        for app in app_list:
            for model in app["models"]:
                model_lookup[model["object_name"].lower()] = model

        section_order = [
            ("Public users", ["publicuser", "user"]),
            ("Platform users", ["platformuser", "user"]),
            ("Partners & trust", ["partner"]),
            ("Stories & blog", ["story", "blogpost", "article", "galleryitem"]),
            ("ATS / applicant tracking", ["application"]),
            ("Finance & access management", ["transaction", "useraccessunlock"]),
        ]

        for section_name, section_models in section_order:
            if not user_has_section_access(request.user, section_name):
                continue
            models = []
            seen = set()
            for key in section_models:
                model = model_lookup.get(key)
                if model and model["object_name"].lower() not in seen:
                    models.append(model)
                    seen.add(model["object_name"].lower())
            if models:
                grouped.append({
                    "name": section_name,
                    "app_label": "client",
                    "models": models,
                    "has_module_perms": True,
                })

        for app in app_list:
            if app["app_label"] == "client":
                app_models = []
                for model in app["models"]:
                    obj_name = model["object_name"].lower()
                    if obj_name in {item for _, keys in section_order for item in keys}:
                        continue
                    app_models.append(model)
                if app_models:
                    grouped.append({
                        "name": app["name"],
                        "app_label": app["app_label"],
                        "models": app_models,
                        "has_module_perms": app["has_module_perms"],
                    })

        return grouped


admin_site = HBCAdminSite(name="hbc_admin")

admin_site.register(User, UserAdmin)
admin_site.register(PublicUser, PublicUserAdmin)
admin_site.register(PlatformUser, PlatformUserAdmin)
admin_site.register(Story, StoryAdmin)
admin_site.register(BlogPost, BlogPostAdmin)
admin_site.register(Article, ArticleAdmin)
admin_site.register(GalleryItem, GalleryItemAdmin)
admin_site.register(Job, JobAdmin)
admin_site.register(Application, ApplicationAdmin)
admin_site.register(Transaction, TransactionAdmin)
admin_site.register(UserAccessUnlock, UserAccessUnlockAdmin)