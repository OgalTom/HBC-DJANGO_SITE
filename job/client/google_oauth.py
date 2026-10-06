"""
Google OAuth 2.0 integration (Authorization Code flow).

Flow:
    1. GET /auth/google/           -> redirect to Google consent
    2. GET /auth/google/callback/  -> Google redirects back with ?code=...
    3. Exchange code for tokens, fetch userinfo
    4. Find-or-create local User, log them in
"""

import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

User = get_user_model()


# ------------------------------------------------------------
# STEP 1 — Redirect to Google
# ------------------------------------------------------------

def google_login(request):
    """Kick off the OAuth flow by redirecting to Google's consent screen."""
    if request.user.is_authenticated:
        return redirect("client:index")

    # CSRF protection: random state stored in session, verified on callback
    state = secrets.token_urlsafe(32)
    request.session["google_oauth_state"] = state

    # Where to send the user after successful login
    next_url = request.GET.get("next", "")
    if next_url:
        request.session["google_oauth_next"] = next_url

    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(settings.GOOGLE_OAUTH_SCOPES),
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }

    url = f"{settings.GOOGLE_OAUTH_AUTH_ENDPOINT}?{urlencode(params)}"
    return redirect(url)


# ------------------------------------------------------------
# STEP 2 — Handle the callback
# ------------------------------------------------------------

def google_callback(request):
    """Handle Google's redirect back to our app."""

    # --- 1. Handle user-denied / error ---
    error = request.GET.get("error")
    if error:
        messages.error(request, f"Google sign-in was cancelled ({error}).")
        return redirect("client:login")

    # --- 2. Verify state (CSRF) ---
    returned_state = request.GET.get("state", "")
    session_state = request.session.pop("google_oauth_state", None)
    if not session_state or returned_state != session_state:
        messages.error(request, "Invalid OAuth state. Please try again.")
        return redirect("client:login")

    code = request.GET.get("code")
    if not code:
        messages.error(request, "Google did not return an authorization code.")
        return redirect("client:login")

    # --- 3. Exchange code for tokens ---
    try:
        token_resp = requests.post(
            settings.GOOGLE_OAUTH_TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()
    except requests.RequestException as exc:
        messages.error(request, f"Could not reach Google: {exc}")
        return redirect("client:login")

    access_token = tokens.get("access_token")
    if not access_token:
        messages.error(request, "Google did not return an access token.")
        return redirect("client:login")

    # --- 4. Fetch user profile ---
    try:
        info_resp = requests.get(
            settings.GOOGLE_OAUTH_USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        info_resp.raise_for_status()
        profile = info_resp.json()
    except requests.RequestException as exc:
        messages.error(request, f"Could not fetch Google profile: {exc}")
        return redirect("client:login")

    email = (profile.get("email") or "").strip().lower()
    if not email:
        messages.error(request, "Google did not return an email address.")
        return redirect("client:login")

    if not profile.get("email_verified", False):
        messages.error(request, "Your Google email is not verified.")
        return redirect("client:login")

    # --- 5. Find or create local user ---
    user, created = _get_or_create_user_from_google(profile)

    # --- 6. Log them in ---
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    if created:
        messages.success(
            request,
            f"Welcome, {user.first_name or user.email}! "
            "Your account was created with Google.",
        )
    else:
        messages.success(request, f"Welcome back, {user.first_name or user.email}!")

    # --- 7. Redirect to next or dashboard ---
    next_url = request.session.pop("google_oauth_next", None)
    return redirect(next_url or reverse("client:dashboard"))


# ------------------------------------------------------------
# Helper — create user from Google profile
# ------------------------------------------------------------

def _get_or_create_user_from_google(profile):
    """
    Returns (user, created).

    Logic:
      - If a user with this email exists -> reuse it (and link by returning it).
      - Else create a new User.
    """
    email = profile["email"].strip().lower()
    first_name = (profile.get("given_name") or "").strip()
    last_name = (profile.get("family_name") or "").strip()

    # If a full name exists but parts are missing, split it.
    if not first_name and not last_name and profile.get("name"):
        parts = profile["name"].split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

    # --- Existing user? ---
    try:
        user = User.objects.get(email__iexact=email)
        # If first_name/last_name are empty on our side, fill them in
        changed = False
        if not user.first_name and first_name:
            user.first_name = first_name
            changed = True
        if not user.last_name and last_name:
            user.last_name = last_name
            changed = True
        if changed:
            user.save(update_fields=["first_name", "last_name"])
        return user, False
    except User.DoesNotExist:
        pass

    # --- Create new user ---
    # Our User model requires: first_name, last_name, email, phone_number (unique).
    # Google doesn't give us a phone number, so we generate a placeholder.
    phone_number = _unique_placeholder_phone()

    user = User.objects.create_user(
        username=email,             # keep username == email (see RegisterForm.save)
        email=email,
        first_name=first_name or "Google",
        last_name=last_name or "User",
        phone_number=phone_number,
        password=None,              # unusable password -> must log in via Google
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user, True


def _unique_placeholder_phone():
    """
    Generate a unique placeholder phone number.
    Google doesn't share phone numbers, but our model requires a unique one.
    Uses a 'G-' prefix so it's obvious these are Google-created accounts.
    """
    import uuid
    while True:
        candidate = f"G-{uuid.uuid4().hex[:12]}"
        if not User.objects.filter(phone_number=candidate).exists():
            return candidate