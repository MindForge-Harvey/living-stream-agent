"""HTTP contract tests for portal identity, cookie writes and user ownership."""

import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app

REAL_CLIENT = httpx.AsyncClient


class PortalAuthTests(unittest.TestCase):
    def setUp(self):
        self.old = (settings.PORTAL_AUTH_URL, settings.APP_PUBLIC_URL)
        settings.PORTAL_AUTH_URL = "http://trusted-portal:8080"
        settings.APP_PUBLIC_URL = "https://www.agent-show.com/living-stream-agent"
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        event.listen(self.engine, "connect", lambda db, _: db.create_function("greatest", -1, max))
        Base.metadata.create_all(self.engine)
        factory = sessionmaker(bind=self.engine)

        def db():
            with factory() as session:
                yield session

        app.dependency_overrides[get_db] = db

        def respond(request):
            self.assertEqual(str(request.url), "http://trusted-portal:8080/api/auth/me")
            cookie = request.headers.get("cookie", "")
            if "portal_session=outage" in cookie:
                return httpx.Response(503)
            uid = "account-a" if "portal_session=a" in cookie else "account-b" if "portal_session=b" in cookie else None
            return httpx.Response(200, json={"authenticated": bool(uid), "user": {"uid": uid, "username": uid, "displayName": uid} if uid else None})

        self.mock = patch("app.core.portal.httpx.AsyncClient", side_effect=lambda **kw: REAL_CLIENT(transport=httpx.MockTransport(respond), **kw))
        self.mock.start()
        self.client = TestClient(app)
        self.write = {"Origin": "https://www.agent-show.com", "X-Living-Stream-Request": "1"}

    def tearDown(self):
        self.client.close()
        self.mock.stop()
        app.dependency_overrides.clear()
        settings.PORTAL_AUTH_URL, settings.APP_PUBLIC_URL = self.old
        self.engine.dispose()

    def login(self, user):
        self.client.cookies.set("portal_session", user)

    def test_forged_jwt_and_header_do_not_authenticate(self):
        token = create_access_token({"sub": "account-a"})
        response = self.client.get("/chat/api/conversations", headers={"Authorization": f"Bearer {token}", "X-Portal-User": "account-a"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["content-type"], "application/json")
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_session_uses_verified_uid_and_rejects_old_account(self):
        self.login("a")
        response = self.client.get("/chat/api/auth/session")
        self.assertEqual(response.json()["userInfo"]["platformUserId"], "account-a")
        self.login("b")
        response = self.client.get("/chat/api/conversations", headers={"X-Portal-User": "account-a"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get("/chat/api/auth/session").json()["userInfo"]["platformUserId"], "account-b")

    def test_writes_require_marker_and_same_origin(self):
        self.login("a")
        for headers in ({}, {"Origin": "https://evil.example", "X-Living-Stream-Request": "1"}):
            self.assertEqual(self.client.post("/chat/api/conversations", json={}, headers=headers).status_code, 403)
        self.assertEqual(self.client.post("/chat/api/conversations", json={}, headers=self.write).status_code, 200)

    def test_owner_comes_from_cookie_and_cross_account_access_is_denied(self):
        self.login("a")
        created = self.client.post("/chat/api/conversations", json={"userId": "account-b", "title": "private"}, headers=self.write).json()
        self.assertEqual(created["userId"], "account-a")
        dialog_id = created["id"]
        self.login("b")
        self.assertEqual(self.client.get("/chat/api/conversations").json()["total"], 0)
        self.assertEqual(self.client.get(f"/chat/api/conversations/{dialog_id}/messages").status_code, 403)
        self.assertEqual(self.client.post("/chat/api/export", json={"dialog_id": dialog_id}, headers=self.write).status_code, 403)
        self.assertEqual(self.client.delete(f"/chat/api/conversations/{dialog_id}", headers=self.write).status_code, 403)

    def test_outage_is_503_and_legacy_platform_login_is_disabled(self):
        self.login("outage")
        self.assertEqual(self.client.get("/chat/api/auth/session").status_code, 503)
        self.login("a")
        self.assertEqual(self.client.post("/chat/api/auth/test-token", json={"userId": "account-b"}, headers=self.write).status_code, 404)


if __name__ == "__main__":
    unittest.main()
