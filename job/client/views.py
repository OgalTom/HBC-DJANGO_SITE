from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import (
    ApplicantReviewForm,
    ApplicationForm,
    JobForm,
    LoginForm,
    PartnerAssignmentForm,
    ProfileForm,
    RegisterForm,
)


def index(request):
    partners = Partner.objects.filter(is_published=True).order_by("sort_order", "name")
    return render(request, "home.html", {
        "title": "Healthcare recruitment made clear",
        "partners": partners,
    })


def about(request):
    return render(request, "client/about.html", {"title": "About"})


# ---------- AUTH ----------

class CustomLoginView(LoginView):
    template_name = "client/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_tab"] = "login"
        ctx["login_form"] = ctx.get("form") or self.authentication_form()
        ctx["register_form"] = RegisterForm()
        return ctx

    def get_success_url(self):
        user = self.request.user
        if user.is_authenticated:
            if _is_platform_staff(user):
                return "/admin/"
            if user.role == "PARTNER":
                return "/partner-panel/"
        return "/dashboard/"

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().first_name}!")
        return super().form_valid(form)


def register_view(request):
    if request.user.is_authenticated:
        return redirect("client:index")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(
                request,
                "Account created successfully. Welcome to HBC Job Majuu!",
            )
            return redirect("client:dashboard")
    else:
        form = RegisterForm()

    return render(request, "client/register.html", {
        "active_tab": "register",
        "register_form": form,
        "login_form": LoginForm(),
    })


from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from .models import Application, Article, GalleryItem, Job, Partner, Transaction, User, UserAccessUnlock


@login_required
def dashboard(request):
    user = request.user

    # ---------- Applications ----------
    applications_qs = (
        Application.objects
        .filter(candidate=user)
        .select_related("job")
        .order_by("-updated_at")
    )

    total_applications = applications_qs.count()

    active_applications = applications_qs.exclude(
        ats_stage__in=[
            Application.ATSStage.DEPLOYED,
            Application.ATSStage.REJECTED,
        ]
    ).count()

    deployed_count = applications_qs.filter(
        ats_stage=Application.ATSStage.DEPLOYED
    ).count()

    # ---------- Transactions ----------
    transactions_qs = (
        Transaction.objects
        .filter(user=user)
        .order_by("-created_at")
    )

    total_paid = (
        transactions_qs
        .filter(payment_status=Transaction.PaymentStatus.SUCCESS)
        .aggregate(total=Sum("amount"))
        .get("total")
        or 0
    )

    tier_1_paid = (
        transactions_qs.filter(
            payment_tier=Transaction.PaymentTier.TIER_1,
            payment_status=Transaction.PaymentStatus.SUCCESS,
        ).exists()
        or user.has_active_tier(UserAccessUnlock.Tier.TIER_1)
    )

    # ---------- Profile completeness ----------
    profile_fields = [
        bool(user.first_name),
        bool(user.last_name),
        bool(user.email),
        bool(user.phone_number and not user.phone_number.startswith("G-")),
    ]
    profile_score = int(round(100 * sum(profile_fields) / len(profile_fields)))

    # ---------- Recommended jobs ----------
    applied_job_ids = applications_qs.values_list("job_id", flat=True)
    recommended_jobs = (
        Job.objects
        .filter(status=Job.Status.ACTIVE)
        .exclude(id__in=applied_job_ids)
        .order_by("-created_at")[:4]
    )

    # ---------- Recent activity (last 5 apps, formatted) ----------
    recent_applications = applications_qs[:5]

    context = {
        "title": "Dashboard",
        "user_obj": user,
        "total_applications": total_applications,
        "active_applications": active_applications,
        "deployed_count": deployed_count,
        "total_paid": total_paid,
        "tier_1_paid": tier_1_paid,
        "tier_2_active": user.has_active_tier(UserAccessUnlock.Tier.TIER_2),
        "tier_3_active": user.has_active_tier(UserAccessUnlock.Tier.TIER_3),
        "profile_score": profile_score,
        "recommended_jobs": recommended_jobs,
        "recent_applications": recent_applications,
        "ats_stages": Application.ATSStage.choices,
    }
    return render(request, "client/dashboard.html", context)

# ---------- Stubs ----------


from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Application, Job, Transaction


# ============================================================
# JOBS LIST
# ============================================================

def jobs(request):
    """Public + member-gated job board with role-aware visibility."""
    user = request.user
    can_view_member_jobs = (
        user.is_authenticated
        and (
            _is_platform_staff(user)
            or user.has_active_tier(UserAccessUnlock.Tier.TIER_1)
            or user.membership_tier in ("MEMBER", "PLACED")
        )
    )

    qs = Job.objects.filter(status=Job.Status.ACTIVE).order_by("-created_at")
    if not can_view_member_jobs:
        qs = qs.filter(visibility=Job.Visibility.PUBLIC)

    q = request.GET.get("q", "").strip()
    country = request.GET.get("country", "").strip()
    sector = request.GET.get("sector", "").strip()

    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(country__icontains=q)
            | Q(sector__icontains=q)
        )
    if country:
        qs = qs.filter(country__iexact=country)
    if sector:
        qs = qs.filter(sector__iexact=sector)

    # Distinct country / sector lists for the filter dropdowns
    countries = (
        Job.objects.filter(status=Job.Status.ACTIVE)
        .values_list("country", flat=True)
        .distinct()
        .order_by("country")
    )
    sectors = (
        Job.objects.filter(status=Job.Status.ACTIVE)
        .values_list("sector", flat=True)
        .distinct()
        .order_by("sector")
    )

    paginator = Paginator(qs, 9)  # 9 per page
    page_obj = paginator.get_page(request.GET.get("page"))

    is_member = can_view_member_jobs

    context = {
        "title": "Jobs",
        "page_obj": page_obj,
        "countries": countries,
        "sectors": sectors,
        "q": q,
        "selected_country": country,
        "selected_sector": sector,
        "is_member": is_member,
        "total_jobs": qs.count(),
    }
    return render(request, "client/jobs.html", context)


# ============================================================
# JOB DETAIL
# ============================================================

def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    user = request.user

    can_view_member_jobs = (
        user.is_authenticated
        and (
            _is_platform_staff(user)
            or user.has_active_tier(UserAccessUnlock.Tier.TIER_1)
            or user.membership_tier in ("MEMBER", "PLACED")
        )
    )
    is_member = can_view_member_jobs
    can_view_full_details = can_view_member_jobs

    has_applied = False
    existing_application = None
    if user.is_authenticated:
        existing_application = Application.objects.filter(
            candidate=user, job=job
        ).first()
        has_applied = existing_application is not None

    context = {
        "title": job.title,
        "job": job,
        "is_member": is_member,
        "can_view_full_details": can_view_full_details,
        "has_applied": has_applied,
        "existing_application": existing_application,
    }
    return render(request, "client/job_detail.html", context)


# ============================================================
# APPLY (POST)
# ============================================================

@login_required
def apply_job(request, job_id):
    job = get_object_or_404(Job, id=job_id, status=Job.Status.ACTIVE)
    user = request.user

    has_tier_1 = user.has_active_tier(UserAccessUnlock.Tier.TIER_1) or user.membership_tier in ("MEMBER", "PLACED")
    if not has_tier_1:
        messages.warning(
            request,
            "Tier 1 platform access is required before you can view detailed roles and proceed with application verification.",
        )
        return redirect("client:job_detail", job_id=job.id)

    if Application.objects.filter(candidate=user, job=job).exists():
        messages.info(request, "You have already applied for this job.")
        return redirect("client:my_applications")

    if request.method == "POST":
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.candidate = user
            application.job = job
            application.ats_stage = Application.ATSStage.SUBMITTED
            application.tier_2_paid = False
            application.save()
            messages.success(
                request,
                f"Application submitted for {job.title}. Track its progress from your dashboard.",
            )
            return redirect("client:my_applications")
    else:
        form = ApplicationForm(initial={"visa_readiness": Application.VisaReadiness.PENDING})

    context = {
        "title": f"Apply for {job.title}",
        "job": job,
        "form": form,
        "is_member": user.membership_tier in ("MEMBER", "PLACED"),
    }
    return render(request, "client/application_form.html", context)


@login_required
def application_detail(request, application_id):
    application = get_object_or_404(
        Application.objects.select_related("candidate", "job", "assigned_agent"),
        id=application_id,
    )

    if not (
        request.user == application.candidate
        or _is_admin_handler(request.user)
        or _is_partner(request.user)
    ):
        messages.error(request, "You do not have access to this application record.")
        return redirect("client:dashboard")

    admin_form = None
    if _is_admin_handler(request.user) or _is_partner(request.user):
        if request.method == "POST":
            admin_form = ApplicantReviewForm(request.POST, instance=application)
            if admin_form.is_valid():
                admin_form.save()
                messages.success(request, "Application record updated successfully.")
                return redirect("client:application_detail", application_id=application.id)
        else:
            admin_form = ApplicantReviewForm(instance=application)

    context = {
        "title": f"Application: {application.job.title}",
        "application": application,
        "admin_form": admin_form,
    }
    return render(request, "client/application_detail.html", context)


# ============================================================
# MY APPLICATIONS
# ============================================================

@login_required
def my_applications(request):
    applications = (
        Application.objects
        .filter(candidate=request.user)
        .select_related("job")
        .order_by("-updated_at")
    )

    context = {
        "title": "My Applications",
        "applications": applications,
        "ats_stages": Application.ATSStage.choices,
    }
    return render(request, "client/my_applications.html", context)


# ============================================================
# PUBLIC LANDING PAGES
# ============================================================

def visas(request):
    return render(request, "client/visas.html", {"title": "Visas"})


def stories(request):
    articles = list(
        Article.objects.filter(
            category=Article.Category.STORY,
        ).filter(Q(status=Article.Status.PUBLISHED) | Q(is_published=True)).order_by("-published_at", "-created_at")
    )
    return render(request, "client/stories.html", {
        "title": "Stories",
        "articles": articles,
    })


def story_detail(request, slug):
    article = get_object_or_404(
        Article.objects.filter(category=Article.Category.STORY).filter(Q(status=Article.Status.PUBLISHED) | Q(is_published=True)),
        slug=slug,
    )
    related_articles = list(
        Article.objects.filter(
            category=Article.Category.STORY,
        ).filter(Q(status=Article.Status.PUBLISHED) | Q(is_published=True)).exclude(id=article.id).order_by("-published_at")[:3]
    )
    return render(request, "client/article_detail.html", {
        "title": article.title,
        "article": article,
        "related_articles": related_articles,
    })


def blog(request):
    articles = list(
        Article.objects.filter(
            category=Article.Category.BLOG,
        ).filter(Q(status=Article.Status.PUBLISHED) | Q(is_published=True)).order_by("-published_at", "-created_at")
    )
    return render(request, "client/blog.html", {
        "title": "Blog",
        "articles": articles,
    })


def blog_detail(request, slug):
    article = get_object_or_404(
        Article.objects.filter(category=Article.Category.BLOG).filter(Q(status=Article.Status.PUBLISHED) | Q(is_published=True)),
        slug=slug,
    )
    related_articles = list(
        Article.objects.filter(
            category=Article.Category.BLOG,
        ).filter(Q(status=Article.Status.PUBLISHED) | Q(is_published=True)).exclude(id=article.id).order_by("-published_at")[:3]
    )
    return render(request, "client/article_detail.html", {
        "title": article.title,
        "article": article,
        "related_articles": related_articles,
    })


def gallery(request):
    items = GalleryItem.objects.filter(is_published=True).order_by("-created_at")
    return render(request, "client/gallery.html", {
        "title": "Gallery",
        "gallery_items": items,
    })


# ============================================================
# USER PORTAL / PERSONAL PAGES
# ============================================================

@login_required
def profile(request):
    user = request.user
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile was updated successfully.")
            return redirect("client:profile")
    else:
        form = ProfileForm(instance=user)

    profile_score = 0
    checks = [
        bool(user.first_name),
        bool(user.last_name),
        bool(user.email),
        bool(user.phone_number and not user.phone_number.startswith("G-")),
        bool(user.country),
        bool(user.city),
        bool(user.passport_number),
        bool(user.cv_summary),
        user.membership_tier != "FREE",
    ]
    profile_score = int(round((sum(checks) / len(checks)) * 100))

    context = {
        "title": "Profile",
        "user_obj": user,
        "profile_score": profile_score,
        "checks": checks,
        "form": form,
    }
    return render(request, "client/profile.html", context)


@login_required
def document_vault(request):
    applications = Application.objects.filter(candidate=request.user).select_related("job").order_by("-updated_at")
    required_docs = [
        "Passport bio-data page",
        "Academic certificates",
        "Work experience letters",
        "Police clearance / good conduct",
        "Professional registration / licensing",
        "Medical examination summary",
    ]
    context = {
        "title": "Document Vault",
        "required_docs": required_docs,
        "applications": applications,
        "application_count": applications.count(),
    }
    return render(request, "client/document_vault.html", context)


@login_required
def visa_readiness(request):
    applications = Application.objects.filter(candidate=request.user).select_related("job").order_by("-updated_at")
    checklist = [
        ("Passport validity", "Ready" if request.user.email else "Pending"),
        ("Document review", applications.filter(document_status=Application.DocumentStatus.VERIFIED).count() > 0 and "Ready" or "Pending"),
        ("Visa status", applications.filter(visa_readiness=Application.VisaReadiness.READY).count() > 0 and "Ready" or "Pending"),
        ("Travel / vaccine records", "Ready"),
    ]
    context = {
        "title": "Visa Readiness",
        "checklist": checklist,
        "applications": applications,
    }
    return render(request, "client/visa_readiness.html", context)


@login_required
def payments(request):
    transactions = Transaction.objects.filter(user=request.user).order_by("-created_at")[:10]
    access_unlocks = UserAccessUnlock.objects.filter(user=request.user).order_by("-granted_at")
    context = {
        "title": "Payments & Receipts",
        "transactions": transactions,
        "access_unlocks": access_unlocks,
        "total_spend": sum(float(t.amount) for t in transactions if t.payment_status == Transaction.PaymentStatus.SUCCESS),
        "tier_1_active": request.user.has_active_tier(UserAccessUnlock.Tier.TIER_1),
        "tier_2_active": request.user.has_active_tier(UserAccessUnlock.Tier.TIER_2),
        "tier_3_active": request.user.has_active_tier(UserAccessUnlock.Tier.TIER_3),
    }
    return render(request, "client/payments.html", context)


@login_required
def payment_checkout(request):
    if request.method != "POST":
        return redirect("client:payments")

    payment_tier = request.POST.get("payment_tier") or Transaction.PaymentTier.TIER_1
    gateway = request.POST.get("gateway") or "MANUAL_OFFLINE"
    amount_raw = request.POST.get("amount", "0")
    try:
        amount = Decimal(amount_raw)
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0")

    payment_status = request.POST.get("payment_status") or Transaction.PaymentStatus.PENDING
    provider_reference = request.POST.get("provider_reference", "").strip()
    notes = request.POST.get("notes", "").strip()
    application_id = request.POST.get("application_id")
    application = None
    if application_id:
        application = get_object_or_404(Application, id=application_id)

    Transaction.objects.create(
        user=request.user,
        application=application,
        payment_tier=payment_tier,
        amount=amount,
        gateway=gateway,
        provider_reference=provider_reference,
        payment_status=payment_status,
        notes=notes,
    )

    if payment_status == Transaction.PaymentStatus.SUCCESS:
        unlock_tier = {
            Transaction.PaymentTier.TIER_1: UserAccessUnlock.Tier.TIER_1,
            Transaction.PaymentTier.TIER_2: UserAccessUnlock.Tier.TIER_2,
            Transaction.PaymentTier.TIER_3: UserAccessUnlock.Tier.TIER_3,
        }.get(payment_tier, UserAccessUnlock.Tier.TIER_1)

        source = (
            UserAccessUnlock.Source.AUTO_PAYMENT
            if gateway not in {"MANUAL_OFFLINE", "BANK_TRANSFER"}
            else UserAccessUnlock.Source.MANUAL_OFFLINE
        )

        UserAccessUnlock.objects.update_or_create(
            user=request.user,
            tier=unlock_tier,
            defaults={
                "source": source,
                "is_active": True,
                "granted_by": request.user,
                "payment_reference": provider_reference,
                "notes": notes,
            },
        )

        if unlock_tier == UserAccessUnlock.Tier.TIER_1:
            request.user.membership_tier = User.MembershipTier.MEMBER
        elif unlock_tier == UserAccessUnlock.Tier.TIER_3:
            request.user.membership_tier = User.MembershipTier.PLACED
        else:
            request.user.membership_tier = request.user.membership_tier
        request.user.save(update_fields=["membership_tier"])

        messages.success(request, f"Payment verified and {unlock_tier} access granted.")
    else:
        messages.info(request, "Payment recorded and awaiting verification.")

    return redirect("client:payments")


@login_required
def manage_access(request):
    if not _is_admin_handler(request.user):
        return redirect("client:dashboard")

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        tier = request.POST.get("tier")
        source = request.POST.get("source", UserAccessUnlock.Source.MANUAL_ADMIN)
        is_active = request.POST.get("is_active") == "on"
        notes = request.POST.get("notes", "")
        payment_reference = request.POST.get("payment_reference", "")

        if user_id and tier:
            user = get_object_or_404(request.user.__class__, id=user_id)
            unlock, _ = UserAccessUnlock.objects.update_or_create(
                user=user,
                tier=tier,
                defaults={
                    "source": source,
                    "is_active": is_active,
                    "granted_by": request.user,
                    "payment_reference": payment_reference,
                    "notes": notes,
                },
            )
            if is_active and tier == UserAccessUnlock.Tier.TIER_1:
                user.membership_tier = "MEMBER"
                user.save(update_fields=["membership_tier"])
            elif is_active and tier == UserAccessUnlock.Tier.TIER_3:
                user.membership_tier = "PLACED"
                user.save(update_fields=["membership_tier"])
            messages.success(request, f"Access updated for {user.get_full_name() or user.email}.")
            return redirect("client:admin_dashboard")

    users = request.user.__class__.objects.order_by("-created_at")[:50]
    context = {
        "title": "Manage user access",
        "users": users,
        "tiers": UserAccessUnlock.Tier.choices,
        "sources": UserAccessUnlock.Source.choices,
    }
    return render(request, "client/manage_access.html", context)


@login_required
def cv_preview(request):
    if not request.user.has_active_tier(UserAccessUnlock.Tier.TIER_1):
        messages.warning(request, "Tier 1 access is required to preview your CV in the dashboard.")
        return redirect("client:dashboard")

    cv_text = request.user.cv_summary or "Candidate profile summary not added yet."
    context = {
        "title": "CV Preview",
        "cv_text": cv_text,
        "user_obj": request.user,
    }
    return render(request, "client/cv_preview.html", context)


# ============================================================
# ADMIN / PARTNER PANELS
# ============================================================

def _is_admin_handler(user):
    return user.is_authenticated and user.role in {
        User.Role.ADMIN,
        User.Role.ADMIN_SUPER,
        User.Role.ADMIN_HANDLER,
    }


def _is_partner(user):
    return user.is_authenticated and user.role in {
        User.Role.PARTNER,
        User.Role.ATS_COORDINATOR,
    }


def _is_platform_staff(user):
    return user.is_authenticated and user.role in {
        User.Role.ADMIN,
        User.Role.ADMIN_SUPER,
        User.Role.ADMIN_HANDLER,
        User.Role.PARTNER,
        User.Role.CONTENT_MANAGER,
        User.Role.DIGITAL_MARKETING,
        User.Role.FINANCE_OFFICER,
        User.Role.ATS_COORDINATOR,
    }


@login_required
def admin_dashboard(request):
    if not _is_admin_handler(request.user):
        return redirect("client:dashboard")

    total_users = Transaction.objects.none() if False else None
    total_users = request.user.__class__.objects.count()
    total_jobs = Job.objects.count()
    total_applications = Application.objects.count()
    active_applications = Application.objects.exclude(ats_stage__in=[
        Application.ATSStage.DEPLOYED,
        Application.ATSStage.REJECTED,
    ]).count()
    pending_review = Application.objects.filter(ats_stage=Application.ATSStage.AGENT_REVIEW).count()

    context = {
        "title": "Admin Dashboard",
        "total_users": total_users,
        "total_jobs": total_jobs,
        "total_applications": total_applications,
        "active_applications": active_applications,
        "pending_review": pending_review,
        "recent_applications": Application.objects.select_related("candidate", "job").order_by("-created_at")[:8],
    }
    return render(request, "client/admin_dashboard.html", context)


@login_required
def partner_dashboard(request):
    if not _is_partner(request.user):
        return redirect("client:dashboard")

    assigned_apps = Application.objects.filter(assigned_agent=request.user).select_related("candidate", "job").order_by("-updated_at")
    context = {
        "title": "Partner Dashboard",
        "assigned_apps": assigned_apps,
        "review_queue": Application.objects.filter(ats_stage=Application.ATSStage.AGENT_REVIEW).select_related("candidate", "job").order_by("-created_at")[:10],
    }
    return render(request, "client/partner_dashboard.html", context)


@login_required
def partner_review(request, application_id):
    if not (_is_partner(request.user) or _is_admin_handler(request.user)):
        return redirect("client:dashboard")

    application = get_object_or_404(
        Application.objects.select_related("candidate", "job", "assigned_agent"),
        id=application_id,
    )
    if request.method == "POST" and _is_admin_handler(request.user):
        form = PartnerAssignmentForm(request.POST, instance=application)
        if form.is_valid():
            form.save()
            messages.success(request, "Application assignment was updated.")
            return redirect("client:partner_review", application_id=application.id)
    else:
        form = PartnerAssignmentForm(instance=application)

    context = {
        "title": f"Application review: {application.job.title}",
        "application": application,
        "candidate": application.candidate,
        "form": form,
    }
    return render(request, "client/partner_review.html", context)


@login_required
def admin_jobs(request):
    if not _is_admin_handler(request.user):
        return redirect("client:dashboard")

    jobs = Job.objects.order_by("-created_at")
    if request.method == "POST":
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save()
            messages.success(request, f"{job.title} was added to the job board.")
            return redirect("client:admin_jobs")
    else:
        form = JobForm()

    context = {
        "title": "Job management",
        "jobs": jobs,
        "job_form": form,
    }
    return render(request, "client/admin_jobs.html", context)
