import json
import secrets
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import StudentRegistrationForm
from .models import StudentProfile


def _auth_context(extra=None):
    ctx = {
        "google_enabled": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        "demo_enabled": settings.DEMO_MODE,
    }
    ctx.update(extra or {})
    return ctx


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Account created successfully! Please log in.")
            return redirect("login")
    else:
        form = StudentRegistrationForm()

    return render(request, "accounts/register.html", _auth_context({"form": form}))


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("dashboard")
        messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm(request)

    return render(request, "accounts/login.html", _auth_context({"form": form}))


@login_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.success(request, "You have logged out successfully.")
        return redirect("login")
    return redirect("dashboard")


@login_required
def profile_view(request):
    from .forms import StudentProfileUpdateForm

    StudentProfile.objects.get_or_create(
        user=request.user, defaults={"course": "Not set", "semester": "1"}
    )

    if request.method == "POST":
        form = StudentProfileUpdateForm(
            request.POST,
            request.FILES,
            user=request.user
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("profile")
    else:
        form = StudentProfileUpdateForm(user=request.user)

    return render(request, "accounts/profile.html", {
        "form": form
    })


# ------------------------------------------------------------------ demo account
def demo_login(request):
    """One-click demo account. Only works when DEMO_MODE=True."""
    if not settings.DEMO_MODE:
        raise Http404
    from hub.demo import ensure_demo_user

    user = ensure_demo_user()
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, "Welcome to the demo account! Explore freely. 🚀")
    return redirect("dashboard")


# ------------------------------------------------------------------ Google sign-in (OAuth 2.0 code flow)
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"


def _google_redirect_uri(request):
    return settings.GOOGLE_REDIRECT_URI or request.build_absolute_uri(reverse("google_callback"))


def _http_json(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def google_login(request):
    if not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET):
        raise Http404
    state = secrets.token_urlsafe(24)
    request.session["google_oauth_state"] = state
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": _google_redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return redirect(f"{GOOGLE_AUTH}?{urllib.parse.urlencode(params)}")


def google_callback(request):
    if not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET):
        raise Http404

    expected = request.session.pop("google_oauth_state", None)
    if not expected or request.GET.get("state") != expected or not request.GET.get("code"):
        messages.error(request, "Google sign-in failed. Please try again.")
        return redirect("login")

    try:
        token = _http_json(GOOGLE_TOKEN, data=urllib.parse.urlencode({
            "code": request.GET["code"],
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": _google_redirect_uri(request),
            "grant_type": "authorization_code",
        }).encode(), headers={"Content-Type": "application/x-www-form-urlencoded"})
        info = _http_json(GOOGLE_USERINFO, headers={"Authorization": f"Bearer {token['access_token']}"})
    except Exception:
        messages.error(request, "Could not verify your Google account. Please try again.")
        return redirect("login")

    email = (info.get("email") or "").lower()
    if not email or not info.get("email_verified"):
        messages.error(request, "Your Google email is not verified.")
        return redirect("login")

    User = get_user_model()
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        base = email.split("@")[0][:25] or "student"
        username, n = base, 1
        while User.objects.filter(username=username).exists():
            n += 1
            username = f"{base}{n}"
        user = User(username=username, email=email,
                    first_name=(info.get("given_name") or "")[:150],
                    last_name=(info.get("family_name") or "")[:150])
        user.set_unusable_password()
        user.save()
    StudentProfile.objects.get_or_create(user=user, defaults={"course": "Not set", "semester": "1"})

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, f"Signed in with Google. Welcome, {user.first_name or user.username}! 🎉")
    return redirect("dashboard")
