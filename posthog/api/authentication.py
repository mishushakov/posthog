import time
from typing import Any, Dict, Optional, cast
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.core.signing import BadSignature
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_protect
from django_otp import login as otp_login
from loginas.utils import is_impersonated_session, restore_original_login
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from social_django.views import auth
from two_factor.utils import default_device
from two_factor.views.core import REMEMBER_COOKIE_PREFIX
from two_factor.views.utils import (
    get_remember_device_cookie,
    validate_remember_device_cookie,
)

from posthog.api.email_verification import EmailVerifier
from posthog.email import is_email_available
from posthog.event_usage import report_user_logged_in
from posthog.models import OrganizationDomain, User
from posthog.utils import get_instance_available_sso_providers


@csrf_protect
def logout(request):
    if request.user.is_authenticated:
        request.user.temporary_token = None
        request.user.save()

    if is_impersonated_session(request):
        restore_original_login(request)
        return redirect("/admin/")

    response = auth_views.logout_then_login(request)
    return response


def axes_locked_out(*args, **kwargs):
    return JsonResponse(
        {
            "type": "authentication_error",
            "code": "too_many_failed_attempts",
            "detail": "Too many failed login attempts. Please try again in"
            f" {int(settings.AXES_COOLOFF_TIME.seconds / 60)} minutes.",
            "attr": None,
        },
        status=status.HTTP_403_FORBIDDEN,
    )


def sso_login(request: HttpRequest, backend: str) -> HttpResponse:
    request.session.flush()
    sso_providers = get_instance_available_sso_providers()
    # because SAML is configured at the domain-level, we have to assume it's enabled for someone in the instance
    sso_providers["saml"] = settings.EE_AVAILABLE

    if backend not in sso_providers:
        return redirect(f"/login?error_code=invalid_sso_provider")

    if not sso_providers[backend]:
        return redirect(f"/login?error_code=improperly_configured_sso")

    return auth(request, backend)


class TwoFactorRequired(APIException):
    status_code = 401
    default_detail = "2FA is required."
    default_code = "2fa_required"


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def to_representation(self, instance: Any) -> Dict[str, Any]:
        return {"success": True}

    def _check_if_2fa_required(self, user: User) -> bool:
        device = default_device(user)
        if not device:
            return False
        # If user has a valid 2FA cookie, use that instead of showing them the 2FA screen
        for key, value in self.context["request"].COOKIES.items():
            if key.startswith(REMEMBER_COOKIE_PREFIX) and value:
                try:
                    if validate_remember_device_cookie(value, user=user, otp_device_id=device.persistent_id):
                        user.otp_device = device  # type: ignore
                        device.throttle_reset()
                        return False
                except BadSignature:
                    # Workaround for signature mismatches due to Django upgrades.
                    # See https://github.com/PostHog/posthog/issues/19350
                    pass
        return True

    def create(self, validated_data: Dict[str, str]) -> Any:
        # Check SSO enforcement (which happens at the domain level)
        sso_enforcement = OrganizationDomain.objects.get_sso_enforcement_for_email_address(validated_data["email"])
        if sso_enforcement:
            raise serializers.ValidationError(
                f"You can only login with SSO for this account ({sso_enforcement}).",
                code="sso_enforced",
            )

        request = self.context["request"]
        user = cast(
            Optional[User],
            authenticate(
                request,
                email=validated_data["email"],
                password=validated_data["password"],
            ),
        )

        if not user:
            raise serializers.ValidationError("Invalid email or password.", code="invalid_credentials")

        # We still let them log in if is_email_verified is null so existing users don't get locked out
        if is_email_available() and user.is_email_verified is not True:
            EmailVerifier.create_token_and_send_email_verification(user)
            # If it's None, we want to let them log in still since they are an existing user
            # If it's False, we want to tell them to check their email
            if user.is_email_verified is False:
                raise serializers.ValidationError(
                    "Your account is awaiting verification. Please check your email for a verification link.",
                    code="not_verified",
                )

        if self._check_if_2fa_required(user):
            request.session["user_authenticated_but_no_2fa"] = user.pk
            request.session["user_authenticated_time"] = time.time()
            raise TwoFactorRequired()

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        report_user_logged_in(user, social_provider="")
        return user


class LoginPrecheckSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def to_representation(self, instance: Dict[str, str]) -> Dict[str, Any]:
        return instance

    def create(self, validated_data: Dict[str, str]) -> Any:
        email = validated_data.get("email", "")
        # TODO: Refactor methods below to remove duplicate queries
        return {
            "sso_enforcement": OrganizationDomain.objects.get_sso_enforcement_for_email_address(email),
            "saml_available": OrganizationDomain.objects.get_is_saml_available_for_email(email),
        }


class NonCreatingViewSetMixin(mixins.CreateModelMixin):
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Method `create()` is overridden to send a more appropriate HTTP
        status code (as no object is actually created).
        """
        response = super().create(request, *args, **kwargs)
        response.status_code = getattr(self, "SUCCESS_STATUS_CODE", status.HTTP_200_OK)
        return response


class LoginViewSet(NonCreatingViewSetMixin, viewsets.GenericViewSet):
    queryset = User.objects.none()
    serializer_class = LoginSerializer
    permission_classes = (permissions.AllowAny,)
    # NOTE: Throttling is handled by the `axes` package


class TwoFactorSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)


class TwoFactorViewSet(NonCreatingViewSetMixin, viewsets.GenericViewSet):
    serializer_class = TwoFactorSerializer
    queryset = User.objects.none()
    permission_classes = (permissions.AllowAny,)

    def _token_is_valid(self, request, user: User, device) -> Response:
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        otp_login(request, device)
        report_user_logged_in(user, social_provider="")
        device.throttle_reset()

        cookie_key = REMEMBER_COOKIE_PREFIX + str(uuid4())
        cookie_value = get_remember_device_cookie(user=user, otp_device_id=device.persistent_id)
        response = Response({"success": True})
        response.set_cookie(
            cookie_key,
            cookie_value,
            max_age=settings.TWO_FACTOR_REMEMBER_COOKIE_AGE,
            domain=getattr(settings, "TWO_FACTOR_REMEMBER_COOKIE_DOMAIN", None),
            path=getattr(settings, "TWO_FACTOR_REMEMBER_COOKIE_PATH", "/"),
            secure=getattr(settings, "TWO_FACTOR_REMEMBER_COOKIE_SECURE", True),
            httponly=getattr(settings, "TWO_FACTOR_REMEMBER_COOKIE_HTTPONLY", True),
            samesite=getattr(settings, "TWO_FACTOR_REMEMBER_COOKIE_SAMESITE", "Strict"),
        )
        return response

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Any:
        user = User.objects.get(pk=request.session["user_authenticated_but_no_2fa"])
        expiration_time = request.session["user_authenticated_time"] + getattr(
            settings, "TWO_FACTOR_LOGIN_TIMEOUT", 600
        )
        if int(time.time()) > expiration_time:
            raise serializers.ValidationError(
                detail="Login attempt has expired. Re-enter username/password.",
                code="2fa_expired",
            )

        with transaction.atomic():
            device = default_device(user)
            is_allowed = device.verify_is_allowed()
            if not is_allowed[0]:
                raise serializers.ValidationError(detail="Too many attempts.", code="2fa_too_many_attempts")
            if device.verify_token(request.data["token"]):
                return self._token_is_valid(request, user, device)

        # Failed attempt so increase throttle
        device.throttle_increment()
        raise serializers.ValidationError(detail="2FA token was not valid", code="2fa_invalid")


class LoginPrecheckViewSet(NonCreatingViewSetMixin, viewsets.GenericViewSet):
    queryset = User.objects.none()
    serializer_class = LoginPrecheckSerializer
    permission_classes = (permissions.AllowAny,)
