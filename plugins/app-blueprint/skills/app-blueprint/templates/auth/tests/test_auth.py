from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from {{pkg}}.api.app import create_app
from {{pkg}}.auth import SESSION_COOKIE, User


class FakeWorkOS:
    """Sessions are plain strings: "s1" is valid, "expired" refreshes into "s2", anything else is signed out."""

    def __init__(self, email="ann@example.com"):
        self.user = User(id="user_1", email=email)

    def authorization_url(self, redirect_uri, state):
        return f"https://authkit.test/authorize?redirect_uri={redirect_uri}&state={state}"

    async def sign_in(self, code):
        return self.user, "s1"

    async def check(self, sealed):
        sessions = {"s1": (self.user, None), "s2": (self.user, None), "expired": (self.user, "s2")}
        return sessions.get(sealed, (None, None))

    def logout_url(self, sealed, return_to):
        return f"https://authkit.test/logout?return_to={return_to}"


@pytest.fixture
def auth_settings(settings):
    return settings.model_copy(update={"workos_client_id": "client_test", "session_secret": "test-secret"})


def make_client(settings, workos=None):
    return TestClient(create_app(settings, workos=workos or FakeWorkOS()), follow_redirects=False)


def sign_in(client, next_path="/"):
    login = client.get(f"/auth/login?next={next_path}")
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
    return client.get(f"/auth/callback?code=c&state={state}")


def test_off_by_default(client):
    assert client.get("/api/me").json() == {"user": None}


def test_signed_out_api_is_401_and_pages_redirect(auth_settings):
    with make_client(auth_settings) as c:
        assert c.get("/api/me").status_code == 401
        assert c.get("/some/page").headers["location"] == "/auth/login?next=/some/page"
        assert c.get("/api/health").status_code == 200


def test_sign_in_and_out(auth_settings):
    with make_client(auth_settings) as c:
        assert sign_in(c).status_code == 303
        assert c.get("/api/me").json() == {"user": {"id": "user_1", "email": "ann@example.com"}}
        assert c.get("/auth/logout").headers["location"].startswith("https://authkit.test/logout")
        c.cookies.clear()
        assert c.get("/api/me").status_code == 401


def test_an_expired_session_is_refreshed_into_the_cookie(auth_settings):
    with make_client(auth_settings) as c:
        c.cookies.set(SESSION_COOKIE, "expired")
        res = c.get("/api/me")
        assert res.status_code == 200
        assert f"{SESSION_COOKIE}=s2" in res.headers["set-cookie"]


def test_callback_with_a_wrong_state_starts_over(auth_settings):
    with make_client(auth_settings) as c:
        c.get("/auth/login")
        assert c.get("/auth/callback?code=c&state=forged").headers["location"] == "/auth/login"


def test_allowed_users(auth_settings):
    with make_client(auth_settings.model_copy(update={"allowed_users": "bob@example.com"})) as c:
        assert sign_in(c).status_code == 403


def test_next_stays_on_this_site(auth_settings):
    with make_client(auth_settings) as c:
        assert sign_in(c, "//evil.test").headers["location"] == "/"
        assert sign_in(c, "/notes?x=1").headers["location"] == "/notes?x=1"
