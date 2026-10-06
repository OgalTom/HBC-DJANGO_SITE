from django.contrib import admin

from .models import Application, Job, Transaction, User, UserAccessUnlock


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
        if obj.role in {User.Role.ADMIN_HANDLER, User.Role.PARTNER}:
            obj.is_staff = True
        elif obj.role == User.Role.USER:
            obj.is_staff = False
        super().save_model(request, obj, form, change)


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


admin.site.register(User, UserAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(Application, ApplicationAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(UserAccessUnlock, UserAccessUnlockAdmin)