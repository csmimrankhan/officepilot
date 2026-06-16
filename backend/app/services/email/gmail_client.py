"""Gmail API client wrapper.

Defines a small ``GmailClient`` interface used by the sync orchestrator and
two implementations:

* :class:`RealGmailClient`  — uses google-api-python-client.
* :class:`FakeGmailClient`  — in-memory fake used in tests and offline dev.

The real client is only instantiated when OAuth credentials are configured
and ``OFFICEPILOT_GMAIL_ALLOW_REAL`` is true. Otherwise every call to
:func:`get_gmail_client` returns the fake. The fake is also useful for
local development without a real Google account.

We use only ``gmail.readonly`` and never mutate messages: no send, no
delete, no modify, no mark-as-read, no archive, no label writes.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional, Protocol

from ...config import Settings

logger = logging.getLogger(__name__)


GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]


# --------------------------------------------------------------------- data


@dataclass
class AttachmentRef:
    attachment_id: str
    filename: str
    mime_type: str
    size: int


@dataclass
class MessageSummary:
    id: str
    thread_id: str
    sender: str
    subject: str
    snippet: str
    received_at: datetime
    body: str = ""
    attachments: list[AttachmentRef] = field(default_factory=list)


class GmailClientError(Exception):
    pass


# --------------------------------------------------------------------- protocol


class GmailClient(Protocol):
    def search_invoice_candidates(
        self, *, days_back: int, max_results: int
    ) -> list[MessageSummary]: ...

    def get_message(self, message_id: str) -> MessageSummary: ...

    def download_attachment(
        self, message_id: str, attachment_id: str
    ) -> bytes: ...


# --------------------------------------------------------------------- fake


class FakeGmailClient:
    """In-memory fake that satisfies the GmailClient protocol."""

    def __init__(self) -> None:
        self._messages: dict[str, MessageSummary] = {}
        self._attachments: dict[tuple[str, str], bytes] = {}
        self._search_calls = 0
        self._download_calls = 0

    def add_message(self, msg: MessageSummary, attachments: dict[str, bytes] | None = None) -> None:
        self._messages[msg.id] = msg
        for att_id, data in (attachments or {}).items():
            self._attachments[(msg.id, att_id)] = data

    def search_invoice_candidates(
        self, *, days_back: int, max_results: int
    ) -> list[MessageSummary]:
        self._search_calls += 1
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        out: list[MessageSummary] = []
        for m in self._messages.values():
            if m.received_at.replace(tzinfo=None) >= cutoff:
                out.append(m)
            if len(out) >= max_results:
                break
        return out

    def get_message(self, message_id: str) -> MessageSummary:
        if message_id not in self._messages:
            raise GmailClientError(f"Unknown message {message_id!r}")
        return self._messages[message_id]

    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        self._download_calls += 1
        key = (message_id, attachment_id)
        if key not in self._attachments:
            raise GmailClientError(
                f"No attachment {attachment_id!r} on message {message_id!r}"
            )
        return self._attachments[key]


# --------------------------------------------------------------------- real


class RealGmailClient:
    """Real Gmail API client. Read-only — never mutates messages."""

    def __init__(self, credentials) -> None:
        try:
            from googleapiclient.discovery import build  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise GmailClientError(
                "google-api-python-client is required for the real Gmail client"
            ) from exc
        self._creds = credentials
        self._service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        self._user = "me"

    @classmethod
    def from_credentials(cls, creds) -> "RealGmailClient":
        return cls(creds)

    def search_invoice_candidates(
        self, *, days_back: int, max_results: int
    ) -> list[MessageSummary]:
        after = (datetime.now(timezone.utc) - timedelta(days=days_back))
        # Use received_after via Gmail search: newer_than:Nd
        query = f"has:attachment newer_than:{int(days_back)}d"
        out: list[MessageSummary] = []
        page_token: Optional[str] = None
        while True:
            kwargs = {
                "userId": self._user,
                "q": query,
                "maxResults": min(500, max_results),
            }
            if page_token:
                kwargs["pageToken"] = page_token
            resp = self._service.users().messages().list(**kwargs).execute()
            for m in resp.get("messages", []):
                try:
                    summary = self.get_message(m["id"])
                except GmailClientError:
                    continue
                out.append(summary)
                if len(out) >= max_results:
                    return out
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return out

    def get_message(self, message_id: str) -> MessageSummary:
        msg = (
            self._service.users()
            .messages()
            .get(userId=self._user, id=message_id, format="full")
            .execute()
        )
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        sender = headers.get("from", "")
        subject = headers.get("subject", "")
        snippet = msg.get("snippet", "")
        internal = int(msg.get("internalDate", "0")) / 1000.0
        received_at = datetime.fromtimestamp(internal, tz=timezone.utc) if internal else datetime.now(timezone.utc)
        body = self._extract_text(msg.get("payload", {}))
        attachments = self._list_attachments(msg.get("payload", {}), msg["id"])
        return MessageSummary(
            id=msg["id"],
            thread_id=msg.get("threadId", ""),
            sender=sender,
            subject=subject,
            snippet=snippet,
            received_at=received_at.astimezone(timezone.utc).replace(tzinfo=None),
            body=body,
            attachments=attachments,
        )

    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        att = (
            self._service.users()
            .messages()
            .attachments()
            .get(userId=self._user, messageId=message_id, id=attachment_id)
            .execute()
        )
        data = att.get("data", "")
        if not data:
            return b""
        return base64.urlsafe_b64decode(data.encode("ascii"))

    # --- internals ---------------------------------------------------------

    def _list_attachments(self, part: dict, message_id: str) -> list[AttachmentRef]:
        out: list[AttachmentRef] = []
        if part.get("filename") and part.get("body", {}).get("attachmentId"):
            out.append(
                AttachmentRef(
                    attachment_id=part["body"]["attachmentId"],
                    filename=part["filename"],
                    mime_type=part.get("mimeType", "application/octet-stream"),
                    size=int(part.get("body", {}).get("size", 0)),
                )
            )
        for child in part.get("parts", []) or []:
            out.extend(self._list_attachments(child, message_id))
        return out

    def _extract_text(self, part: dict) -> str:
        mime = part.get("mimeType", "")
        if mime == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
        for child in part.get("parts", []) or []:
            txt = self._extract_text(child)
            if txt:
                return txt
        return ""


# --------------------------------------------------------------------- factory


# Module-level fake client handle for tests / offline dev.
_FAKE_HANDLE: dict[str, FakeGmailClient] = {}


def install_fake_client(client: FakeGmailClient) -> None:
    """Inject a fake client. Used by tests and the ``--demo-data`` admin tool."""
    _FAKE_HANDLE["client"] = client


def get_fake_client() -> FakeGmailClient:
    return _FAKE_HANDLE.setdefault("client", FakeGmailClient())


def reset_fake_client() -> None:
    _FAKE_HANDLE.clear()


def get_gmail_client(settings: Settings, *, credentials=None) -> GmailClient:
    """Return a Gmail client. The fake is used when no credentials are present
    or real calls are disabled (``OFFICEPILOT_GMAIL_ALLOW_REAL=false``)."""
    if not settings.gmail_allow_real or credentials is None:
        return get_fake_client()
    if isinstance(credentials, FakeGmailClient):  # pragma: no cover - convenience
        return credentials
    return RealGmailClient.from_credentials(credentials)
