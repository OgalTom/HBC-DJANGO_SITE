from django.test import TestCase
from django.urls import reverse

from .models import Application, Job, Transaction, User, UserAccessUnlock


class AuthPageTests(TestCase):
    def test_login_page_renders_email_and_password_fields(self):
        response = self.client.get(reverse("client:login"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("login_form", response.context)
        self.assertContains(response, "Email or Username")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')


class JobVisibilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="candidate@example.com",
            email="candidate@example.com",
            password="StrongPass123!",
            first_name="Jane",
            last_name="Doe",
            phone_number="+254700000001",
        )
        self.member = User.objects.create_user(
            username="member@example.com",
            email="member@example.com",
            password="StrongPass123!",
            first_name="Maya",
            last_name="Member",
            phone_number="+254700000002",
            membership_tier=User.MembershipTier.MEMBER,
        )
        self.partner = User.objects.create_user(
            username="partner@example.com",
            email="partner@example.com",
            password="StrongPass123!",
            first_name="Asha",
            last_name="Partner",
            phone_number="+254700000003",
            role=User.Role.PARTNER,
        )
        self.public_job = Job.objects.create(
            title="Public role",
            country="Kenya",
            sector="IT",
            description_masked="Public summary",
            description_full="Public details",
            visibility=Job.Visibility.PUBLIC,
        )
        self.member_job = Job.objects.create(
            title="Member role",
            country="UAE",
            sector="Healthcare",
            description_masked="Member summary",
            description_full="Member details",
            visibility=Job.Visibility.MEMBERS_ONLY,
        )

    def test_public_jobs_visible_to_free_users(self):
        self.assertTrue(self.public_job.is_visible_to(self.user))
        self.assertFalse(self.member_job.is_visible_to(self.user))

    def test_member_jobs_visible_to_members(self):
        self.assertTrue(self.member_job.is_visible_to(self.member))

    def test_jobs_page_hides_member_only_jobs_from_free_users(self):
        response = self.client.get(reverse("client:jobs"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.public_job.title)
        self.assertNotContains(response, self.member_job.title)

    def test_index_page_has_core_landing_sections(self):
        response = self.client.get(reverse("client:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Global recruitment platform")
        self.assertContains(response, "Tier 1")

    def test_partner_review_page_for_assigned_application(self):
        application = self.public_job.applications.create(
            candidate=self.user,
            ats_stage="AGENT_REVIEW",
            assigned_agent=self.partner,
        )
        self.client.force_login(self.partner)
        response = self.client.get(reverse("client:partner_review", args=[application.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, application.job.title)

    def test_about_page_renders(self):
        response = self.client.get(reverse("client:about"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "About")

    def test_job_detail_page_renders_for_public_job(self):
        response = self.client.get(reverse("client:job_detail", args=[self.public_job.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.public_job.title)


class UnlockAndProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="unlock@example.com",
            email="unlock@example.com",
            password="StrongPass123!",
            first_name="Nora",
            last_name="Kiptoo",
            phone_number="+254700333001",
            country="Kenya",
            city="Nairobi",
            passport_number="P9988776",
        )

    def test_manual_tier_unlock_is_active_for_user(self):
        unlock = UserAccessUnlock.objects.create(
            user=self.user,
            tier=UserAccessUnlock.Tier.TIER_1,
            source=UserAccessUnlock.Source.MANUAL_ADMIN,
            is_active=True,
            notes="Admin verified mobile money payment.",
        )

        self.assertTrue(self.user.has_active_tier(UserAccessUnlock.Tier.TIER_1))
        self.assertIn(unlock, self.user.active_accesses())

    def test_profile_update_form_saves_profile_fields(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("client:profile"),
            {
                "first_name": "Nora",
                "last_name": "Kiptoo",
                "email": "unlock@example.com",
                "phone_number": "+254700333001",
                "country": "Uganda",
                "city": "Kampala",
                "passport_number": "P9988779",
                "cv_summary": "Experienced logistics coordinator.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.country, "Uganda")
        self.assertEqual(self.user.city, "Kampala")
        self.assertEqual(self.user.passport_number, "P9988779")
        self.assertIn("logistics", self.user.cv_summary.lower())

    def test_successful_payment_verification_grants_tier_access(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("client:payment_checkout"),
            {
                "payment_tier": "TIER_1",
                "gateway": "MANUAL_OFFLINE",
                "amount": "2500.00",
                "provider_reference": "OFFLINE-001",
                "payment_status": "SUCCESS",
                "notes": "Verified by admin after receipt upload.",
            },
        )

        self.assertRedirects(response, reverse("client:payments"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_active_tier(UserAccessUnlock.Tier.TIER_1))
        self.assertTrue(
            Transaction.objects.filter(
                user=self.user,
                payment_tier=Transaction.PaymentTier.TIER_1,
                payment_status=Transaction.PaymentStatus.SUCCESS,
            ).exists()
        )


class ApplicantWorkflowTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(
            username="applicant@example.com",
            email="applicant@example.com",
            password="StrongPass123!",
            first_name="Amina",
            last_name="Ali",
            phone_number="+254700000099",
            membership_tier=User.MembershipTier.MEMBER,
        )
        self.job = Job.objects.create(
            title="Operations Manager",
            country="Kenya",
            sector="Logistics",
            description_masked="Operations role",
            description_full="Full description",
            status=Job.Status.ACTIVE,
            visibility=Job.Visibility.PUBLIC,
        )

    def test_apply_page_renders_application_form(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("client:apply_job", args=[self.job.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Application form")
        self.assertContains(response, 'name="current_country"')
        self.assertContains(response, 'name="cover_letter"')

    def test_application_submit_saves_tracking_fields(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("client:apply_job", args=[self.job.id]),
            {
                "current_country": "Kenya",
                "city": "Nairobi",
                "passport_number": "P1234567",
                "years_of_experience": 5,
                "cover_letter": "I am excited to join your team.",
                "visa_readiness": "READY",
            },
        )

        self.assertRedirects(response, reverse("client:my_applications"))
        application = Application.objects.get(candidate=self.member, job=self.job)
        self.assertEqual(application.current_country, "Kenya")
        self.assertEqual(application.city, "Nairobi")
        self.assertEqual(application.passport_number, "P1234567")
        self.assertEqual(application.years_of_experience, 5)
        self.assertIn("excited", application.cover_letter)
        self.assertEqual(application.visa_readiness, "READY")
