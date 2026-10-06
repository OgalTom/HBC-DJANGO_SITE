from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import google_oauth


app_name = "client"

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("jobs/", views.jobs, name="jobs"),
    path("jobs/<uuid:job_id>/", views.job_detail, name="job_detail"),
    path("jobs/<uuid:job_id>/apply/", views.apply_job, name="apply_job"),

    path("applications/<uuid:application_id>/", views.application_detail, name="application_detail"),
    path("my-applications/", views.my_applications, name="my_applications"),
    path("visas/", views.visas, name="visas"),
    path("stories/", views.stories, name="stories"),
    path("blog/", views.blog, name="blog"),

    # Auth
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", auth_views.LogoutView.as_view(next_page="client:index"), name="logout"),

    # Account area
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("document-vault/", views.document_vault, name="document_vault"),
    path("visa-readiness/", views.visa_readiness, name="visa_readiness"),
    path("payments/", views.payments, name="payments"),
    path("payment-checkout/", views.payment_checkout, name="payment_checkout"),
    path("cv-preview/", views.cv_preview, name="cv_preview"),

    # Operational / admin panels
    path("admin-panel/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-panel/jobs/", views.admin_jobs, name="admin_jobs"),
    path("admin-panel/manage-access/", views.manage_access, name="manage_access"),
    path("partner-panel/", views.partner_dashboard, name="partner_dashboard"),
    path("partner-review/<uuid:application_id>/", views.partner_review, name="partner_review"),

    path("auth/google/", google_oauth.google_login, name="google_login"),
    path("auth/google/callback/", google_oauth.google_callback, name="google_callback"),
]