import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


# ============================================================
# USER / CANDIDATE
# ============================================================


class User(AbstractUser):

    class Role(models.TextChoices):
        USER = "USER", "Candidate"
        ADMIN_HANDLER = "ADMIN_HANDLER", "Admin Handler"
        PARTNER = "PARTNER", "Partner Reviewer"

    class MembershipTier(models.TextChoices):
        FREE = "FREE", "Free"
        MEMBER = "MEMBER", "Member"
        PLACED = "PLACED", "Placed"

    class NeaimsStatus(models.TextChoices):
        PENDING = "PENDING_REGISTRATION", "Pending Registration"
        REGISTERED = "REGISTERED", "Registered"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    email = models.EmailField(unique=True)

    phone_number = models.CharField(
        max_length=20,
        unique=True
    )

    country = models.CharField(max_length=100, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    passport_number = models.CharField(max_length=50, blank=True, default="")
    cv_summary = models.TextField(blank=True, default="")
    bio = models.TextField(blank=True, default="")

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.USER,
        help_text="Controls how the user appears in the admin system and how they can access jobs.",
    )

    membership_tier = models.CharField(
        max_length=20,
        choices=MembershipTier.choices,
        default=MembershipTier.FREE
    )

    neaims_status = models.CharField(
        max_length=50,
        choices=NeaimsStatus.choices,
        default=NeaimsStatus.PENDING
    )

    # Override related names for auth relations to avoid clashes
    groups = models.ManyToManyField(
        Group,
        related_name="client_user_set",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name="client_user_permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def active_accesses(self):
        return UserAccessUnlock.objects.filter(user=self, is_active=True).order_by("-granted_at")

    def has_active_tier(self, tier):
        if self.role in {self.Role.ADMIN_HANDLER, self.Role.PARTNER}:
            return True
        if self.membership_tier == self.MembershipTier.PLACED:
            return True
        if self.membership_tier == self.MembershipTier.MEMBER and tier == UserAccessUnlock.Tier.TIER_1:
            return True
        return UserAccessUnlock.objects.filter(user=self, tier=tier, is_active=True).exists()

    def tier_balance(self):
        return {
            "tier_1": self.has_active_tier(UserAccessUnlock.Tier.TIER_1),
            "tier_2": self.has_active_tier(UserAccessUnlock.Tier.TIER_2),
            "tier_3": self.has_active_tier(UserAccessUnlock.Tier.TIER_3),
        }


class UserAccessUnlock(models.Model):
    class Tier(models.TextChoices):
        TIER_1 = "TIER_1", "Tier 1 - Membership"
        TIER_2 = "TIER_2", "Tier 2 - Verification"
        TIER_3 = "TIER_3", "Tier 3 - Placement"

    class Source(models.TextChoices):
        AUTO_PAYMENT = "AUTO_PAYMENT", "Automatic after payment verification"
        MANUAL_ADMIN = "MANUAL_ADMIN", "Manual admin approval"
        MANUAL_OFFLINE = "MANUAL_OFFLINE", "Manual offline receipt"
        SYSTEM = "SYSTEM", "System-generated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tier_unlocks")
    tier = models.CharField(max_length=12, choices=Tier.choices)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL_ADMIN)
    is_active = models.BooleanField(default=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="granted_tier_unlocks",
    )
    payment_reference = models.CharField(max_length=120, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    granted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-granted_at",)
        constraints = [
            models.UniqueConstraint(fields=["user", "tier"], name="unique_user_tier_unlock")
        ]

    def __str__(self):
        return f"{self.user} · {self.get_tier_display} · {self.get_source_display}"


# ============================================================
# JOBS
# ============================================================


class Job(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        FILLED = "FILLED", "Filled"
        CLOSED = "CLOSED", "Closed"

    class Visibility(models.TextChoices):
        PUBLIC = "PUBLIC", "Public"
        MEMBERS_ONLY = "MEMBERS_ONLY", "Members only"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    title = models.CharField(max_length=150)

    country = models.CharField(max_length=50)

    sector = models.CharField(max_length=50)

    description_masked = models.TextField()

    description_full = models.TextField()

    salary_disclosed = models.BooleanField(default=False)

    salary_range = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    tier_2_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    tier_3_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
        help_text="Public jobs are visible to everyone; member-only jobs require membership access.",
    )

    image_url = models.URLField(max_length=500, blank=True, default="")
    image_alt = models.CharField(max_length=150, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_visible_to(self, user):
        if self.visibility == self.Visibility.PUBLIC:
            return True
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "role", None) in {User.Role.ADMIN_HANDLER, User.Role.PARTNER}:
            return True
        return user.membership_tier in {User.MembershipTier.MEMBER, User.MembershipTier.PLACED}

    def __str__(self):
        return f"{self.title} - {self.country}"


# ============================================================
# APPLICATION / ATS
# ============================================================


class Application(models.Model):

    class ATSStage(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        VETTING = "VETTING", "Document Verification"
        AGENT_REVIEW = "AGENT_REVIEW", "Agent Review"
        INTERVIEW = "INTERVIEW", "Interview"
        OFFER = "OFFER", "Offer Extended"
        VISA = "VISA", "Visa Processing"
        DEPLOYED = "DEPLOYED", "Deployed"
        REJECTED = "REJECTED", "Rejected"

    class VisaReadiness(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not started"
        PENDING = "PENDING", "Pending"
        READY = "READY", "Ready"
        UNDER_REVIEW = "UNDER_REVIEW", "Under review"

    class DocumentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        UPLOADED = "UPLOADED", "Uploaded"
        UNDER_REVIEW = "UNDER_REVIEW", "Under review"
        VERIFIED = "VERIFIED", "Verified"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    current_country = models.CharField(max_length=100, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    passport_number = models.CharField(max_length=50, blank=True, default="")
    years_of_experience = models.PositiveIntegerField(default=0)
    cover_letter = models.TextField(blank=True, default="")
    visa_readiness = models.CharField(
        max_length=30,
        choices=VisaReadiness.choices,
        default=VisaReadiness.PENDING,
    )
    document_status = models.CharField(
        max_length=30,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
    )
    admin_notes = models.TextField(blank=True, default="")

    ats_stage = models.CharField(
        max_length=50,
        choices=ATSStage.choices,
        default=ATSStage.SUBMITTED
    )

    tier_2_paid = models.BooleanField(default=False)

    tier_3_paid = models.BooleanField(default=False)

    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_applications"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "job"],
                name="unique_candidate_job_application"
            )
        ]

    def __str__(self):
        return f"{self.candidate} → {self.job}"


# ============================================================
# TRANSACTIONS
# ============================================================


class Transaction(models.Model):

    class PaymentTier(models.TextChoices):
        TIER_1 = "TIER_1", "Tier 1 - Membership"
        TIER_2 = "TIER_2", "Tier 2 - Application & Verification"
        TIER_3 = "TIER_3", "Tier 3 - Placement & Processing"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    application = models.ForeignKey(
        Application,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions"
    )

    payment_tier = models.CharField(
        max_length=10,
        choices=PaymentTier.choices
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=5,
        default="KES"
    )

    gateway = models.CharField(
        max_length=30,
        choices=[
            ("M_PESA", "M-Pesa"),
            ("CARD", "Card / Visa"),
            ("PAYPAL", "PayPal"),
            ("BANK_TRANSFER", "Bank Transfer"),
            ("MANUAL_OFFLINE", "Manual Offline"),
        ],
        default="MANUAL_OFFLINE",
    )

    provider_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )

    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"{self.payment_tier} - "
            f"{self.amount} {self.currency} - "
            f"{self.payment_status}"
        )