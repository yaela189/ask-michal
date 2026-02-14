# -*- coding: utf-8 -*-
import httpx

from client.auth import load_token


class MichalClient:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/")
        self.token = load_token()

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def ask(self, question: str) -> dict:
        response = httpx.post(
            f"{self.server_url}/api/ask",
            json={"question": question},
            headers=self._headers(),
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()

    def get_quota(self) -> dict:
        response = httpx.get(
            f"{self.server_url}/api/quota",
            headers=self._headers(),
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()

    def list_users(self) -> list[dict]:
        response = httpx.get(
            f"{self.server_url}/admin/users",
            headers=self._headers(),
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()

    def rate(self, query_id: int, rating: int, comment: str | None = None) -> dict:
        payload = {"query_id": query_id, "rating": rating}
        if comment:
            payload["comment"] = comment
        response = httpx.post(
            f"{self.server_url}/api/rate",
            json=payload,
            headers=self._headers(),
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()

    def reload_quota(self, user_id: int, amount: int) -> dict:
        response = httpx.post(
            f"{self.server_url}/admin/users/{user_id}/reload",
            json={"amount": amount},
            headers=self._headers(),
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()
