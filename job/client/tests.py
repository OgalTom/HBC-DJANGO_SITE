from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from .admin import user_has_section_access
from .forms import PlatformStaffForm
from .models import Application, Article, GalleryItem, Job, Partner, Transaction, User, UserAccessUnlock


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

    def test_index_page_renders_partner_marquee(self):
        Partner.objects.create(
            name="Alaska Logistics",
            short_description="Regional logistics partner",
            logo_url="https://example.com/logo.png",
            is_published=True,
            sort_order=1,
        )
        response = self.client.get(reverse("client:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trusted partners")
        self.assertContains(response, "Alaska Logistics")

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

    def test_member_only_job_is_visible_when_tier_unlock_is_active(self):
        self.user.membership_tier = User.MembershipTier.FREE
        self.user.save(update_fields=["membership_tier"])
        UserAccessUnlock.objects.create(
            user=self.user,
            tier=UserAccessUnlock.Tier.TIER_1,
            source=UserAccessUnlock.Source.MANUAL_ADMIN,
            is_active=True,
        )

        self.assertTrue(self.user.has_active_tier(UserAccessUnlock.Tier.TIER_1))
        self.assertTrue(self.member_job.is_visible_to(self.user))

    def test_job_auto_populates_country_flag_and_cover_image(self):
        job = Job.objects.create(
            title="Operations Supervisor",
            country="Kenya",
            sector="Logistics",
            description_masked="Operations summary",
            description_full="Detailed operations role",
            cover_image="https://example.com/kenya-job.jpg",
        )

        self.assertEqual(job.country_flag, "🇰🇪")
        self.assertEqual(job.cover_image, "https://example.com/kenya-job.jpg")
        self.assertEqual(job.image_url, "https://example.com/kenya-job.jpg")


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

    def test_section_access_checks_specific_admin_permissions(self):
        self.user.is_staff = True
        self.user.save()

        self.assertFalse(user_has_section_access(self.user, "ATS / applicant tracking"))

        self.user.user_permissions.add(Permission.objects.get(codename="view_application"))
        self.assertTrue(user_has_section_access(self.user, "ATS / applicant tracking"))

    def test_platform_roles_are_distinct_from_public_members(self):
        platform_roles = [
            User.Role.ADMIN,
            User.Role.ADMIN_HANDLER,
            User.Role.PARTNER,
            User.Role.CONTENT_MANAGER,
            User.Role.ATS_COORDINATOR,
            User.Role.FINANCE_OFFICER,
        ]

        for role in platform_roles:
            label = str(role).replace("ADMIN_", "").lower()
            user = User.objects.create_user(
                username=f"platform-{label}",
                email=f"{label}@example.com",
                password="StrongPass123!",
                first_name="Platform",
                last_name="Staff",
                phone_number=f"+254700{label[:3]}001",
                role=role,
            )
            self.assertTrue(user.is_platform_staff)
            self.assertTrue(user.is_staff)

    def test_platform_staff_form_omits_public_applicant_fields(self):
        form = PlatformStaffForm()
        self.assertNotIn("cv_summary", form.fields)
        self.assertNotIn("passport_number", form.fields)
        self.assertIn("role", form.fields)
        self.assertIn("email", form.fields)


class EditorialContentTests(TestCase):
    def setUp(self):
        self.story = Article.objects.create(
            title="From Nairobi to Germany",
            slug="from-nairobi-to-germany",
            category=Article.Category.STORY,
            excerpt="A candidate journey from Nairobi to Germany.",
            body="An inspiring journey into overseas healthcare recruitment.",
            image_url="https://example.com/story.jpg",
            is_published=True,
            author_name="HBC Team",
        )
        self.blog = Article.objects.create(
            title="How to prepare for overseas recruitment",
            slug="how-to-prepare-for-overseas-recruitment",
            category=Article.Category.BLOG,
            excerpt="Practical guidance for recruiters and applicants.",
            body="Candidates should prepare documents and licensing early.",
            image_url="https://example.com/blog.jpg",
            is_published=True,
            author_name="HBC Team",
        )

    def test_stories_page_lists_published_story_cards(self):
        response = self.client.get(reverse("client:stories"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.story.title)
        self.assertContains(response, self.story.excerpt)

    def test_blog_page_lists_published_blog_cards(self):
        response = self.client.get(reverse("client:blog"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.blog.title)
        self.assertContains(response, self.blog.excerpt)

    def test_story_detail_page_renders_article_content(self):
        response = self.client.get(reverse("client:story_detail", args=[self.story.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.story.title)
        self.assertContains(response, self.story.body)

    def test_gallery_page_renders_gallery_items(self):
        item = GalleryItem.objects.create(
            title="Recruitment Day in Nairobi",
            slug="recruitment-day-in-nairobi",
            description="A glimpse into our planning sessions and applicant onboarding.",
            image_url="https://example.com/gallery.jpg",
            is_published=True,
        )

        response = self.client.get(reverse("client:gallery"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, item.title)
        self.assertContains(response, item.description)


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
