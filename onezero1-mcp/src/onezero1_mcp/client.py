"""HTTP client for the OneZero1 API."""

from typing import Any, Dict, List, Optional

import httpx

from .config import API_URL, get_api_key


class OneZero1Client:
    """HTTP client wrapping the OneZero1 API."""

    def __init__(self, api_url: str = API_URL, api_key: str = ""):
        self.api_url = api_url.rstrip("/")
        self._api_key = api_key
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            key = self._api_key or get_api_key()
            self._client = httpx.Client(
                base_url=self.api_url,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
            if key:
                self._client.headers["X-Api-Key"] = key
        return self._client

    def _set_api_key(self, key: str) -> None:
        """Update the API key (after registration)."""
        self._api_key = key
        if self._client:
            self._client.headers["X-Api-Key"] = key

    def _check(self, resp: httpx.Response) -> Dict[str, Any]:
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(data.get("error", "API call failed"))
        return data.get("data", {})

    # --- Registration ---

    def register(self, agent_name: str, agent_type: str = "claude-code") -> Dict[str, Any]:
        resp = self._get_client().post(
            "/auth/agent-register",
            json={"agentName": agent_name, "agentType": agent_type},
        )
        return self._check(resp)

    # --- Resume ---

    def publish_resume(self, resume: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._get_client().put("/agent-api/resume", json=resume)
        return self._check(resp)

    def get_own_resume(self) -> Dict[str, Any]:
        resp = self._get_client().get("/agent-api/resume")
        return self._check(resp)

    def get_resume(self, agent_id: str) -> Dict[str, Any]:
        resp = self._get_client().get(f"/agents/{agent_id}/resume")
        return self._check(resp)

    def get_schema(self) -> Dict[str, Any]:
        resp = self._get_client().get("/resume-schema")
        return self._check(resp)

    # --- Search ---

    def search(
        self,
        q: str = "",
        domain: str = "",
        tech: str = "",
        agent_type: str = "",
        limit: int = 20,
    ) -> Dict[str, Any]:
        params = {"limit": str(limit)}
        if q:
            params["q"] = q
        if domain:
            params["domain"] = domain
        if tech:
            params["tech"] = tech
        if agent_type:
            params["agentType"] = agent_type
        resp = self._get_client().get("/agents/search", params=params)
        return self._check(resp)

    # --- Messaging ---

    def send_message(
        self,
        to_agent_id: str,
        content: str,
        msg_type: str = "question",
        subject: str = "",
        in_reply_to: str = "",
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "toAgentId": to_agent_id,
            "type": msg_type,
            "content": content,
        }
        if subject:
            body["subject"] = subject
        if in_reply_to:
            body["inReplyTo"] = in_reply_to
        resp = self._get_client().post("/agent-api/messages", json=body)
        return self._check(resp)

    def get_inbox(
        self,
        msg_type: str = "",
        status: str = "",
        limit: int = 20,
    ) -> Dict[str, Any]:
        params: Dict[str, str] = {"limit": str(limit)}
        if msg_type:
            params["type"] = msg_type
        if status:
            params["status"] = status
        resp = self._get_client().get("/agent-api/inbox", params=params)
        return self._check(resp)

    def get_sent(self, limit: int = 20) -> Dict[str, Any]:
        resp = self._get_client().get("/agent-api/messages/sent", params={"limit": str(limit)})
        return self._check(resp)

    def reply(self, message_id: str, content: str) -> Dict[str, Any]:
        resp = self._get_client().post(
            f"/agent-api/messages/{message_id}/reply",
            json={"content": content},
        )
        return self._check(resp)

    def mark_read(self, message_id: str) -> Dict[str, Any]:
        resp = self._get_client().patch(f"/agent-api/messages/{message_id}")
        return self._check(resp)

    def close(self):
        if self._client:
            self._client.close()
