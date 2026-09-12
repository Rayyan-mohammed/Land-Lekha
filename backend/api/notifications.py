"""Notification service: tells an operator/verifier when a document they care about
changes state (verified, rejected, flagged for review).

No real SMS/email/push provider is wired up in this prototype - there is nothing to send
to and no account to send from. What's here is a real, swappable interface: a backend is
chosen from environment variables at import time, and every backend implements the same
`send(to, subject, body)` call, so plugging in a real provider later is a one-file change,
not a redesign.

Backends:
- ConsoleBackend (default): logs the notification. Always available, always safe.
- SMTPBackend: sends real email if LL_SMTP_HOST is set.
- WebhookBackend: POSTs a JSON payload if LL_NOTIFY_WEBHOOK_URL is set (e.g. Slack
  incoming webhook, or a custom SMS/push gateway that accepts JSON).

Multiple backends can be active at once (e.g. console + webhook); each delivery failure
is caught and logged so a broken notification channel never fails the request that
triggered it.
"""
from __future__ import annotations

import json
import logging
import os
import smtplib
import urllib.request
from dataclasses import dataclass
from email.message import EmailMessage

logger = logging.getLogger("landlekha.notifications")


@dataclass
class Notification:
    to_email: str | None
    to_name: str
    subject: str
    body: str
    event: str
    meta: dict


class NotificationBackend:
    name = "base"

    def send(self, note: Notification) -> bool:
        raise NotImplementedError


class ConsoleBackend(NotificationBackend):
    name = "console"

    def send(self, note: Notification) -> bool:
        logger.info("[notify:%s] to=%s subject=%s meta=%s", note.event, note.to_name, note.subject, note.meta)
        return True


class SMTPBackend(NotificationBackend):
    name = "smtp"

    def __init__(self):
        self.host = os.getenv("LL_SMTP_HOST", "")
        self.port = int(os.getenv("LL_SMTP_PORT", "587"))
        self.user = os.getenv("LL_SMTP_USER", "")
        self.password = os.getenv("LL_SMTP_PASSWORD", "")
        self.from_addr = os.getenv("LL_SMTP_FROM", self.user or "noreply@landlekha.local")
        self.use_tls = os.getenv("LL_SMTP_TLS", "1") != "0"

    def send(self, note: Notification) -> bool:
        if not note.to_email:
            return False
        msg = EmailMessage()
        msg["Subject"] = note.subject
        msg["From"] = self.from_addr
        msg["To"] = note.to_email
        msg.set_content(note.body)
        with smtplib.SMTP(self.host, self.port, timeout=10) as server:
            if self.use_tls:
                server.starttls()
            if self.user:
                server.login(self.user, self.password)
            server.send_message(msg)
        return True


class WebhookBackend(NotificationBackend):
    name = "webhook"

    def __init__(self):
        self.url = os.getenv("LL_NOTIFY_WEBHOOK_URL", "")

    def send(self, note: Notification) -> bool:
        if not self.url:
            return False
        payload = json.dumps({"event": note.event, "to": note.to_name, "subject": note.subject,
                              "body": note.body, "meta": note.meta}).encode("utf-8")
        req = urllib.request.Request(self.url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300


def _active_backends() -> list[NotificationBackend]:
    backends: list[NotificationBackend] = [ConsoleBackend()]
    if os.getenv("LL_SMTP_HOST"):
        backends.append(SMTPBackend())
    if os.getenv("LL_NOTIFY_WEBHOOK_URL"):
        backends.append(WebhookBackend())
    return backends


class NotificationService:
    """Fan-outs one notification to every configured backend. Never raises: a delivery
    failure is logged, not propagated, so notifications can't break the calling request."""

    def __init__(self, backends: list[NotificationBackend] | None = None):
        self.backends = backends if backends is not None else _active_backends()

    def notify(self, *, to_email: str | None, to_name: str, subject: str, body: str,
              event: str, meta: dict | None = None) -> dict:
        note = Notification(to_email, to_name, subject, body, event, meta or {})
        results = {}
        for backend in self.backends:
            try:
                results[backend.name] = backend.send(note)
            except Exception as exc:  # noqa: BLE001 - a broken channel must not break the caller
                logger.warning("notification backend %s failed: %s", backend.name, exc)
                results[backend.name] = False
        return results


service = NotificationService()


def notify_document_reviewed(*, uploader_email: str | None, uploader_name: str, document_id: int,
                             status: str, reviewer_name: str, note: str | None = None) -> dict:
    subject = f"Document #{document_id} {status}"
    body = (f"Document #{document_id} was {status} by {reviewer_name}."
           + (f"\n\nNote: {note}" if note else ""))
    return service.notify(to_email=uploader_email, to_name=uploader_name, subject=subject, body=body,
                          event="document.reviewed", meta={"document_id": document_id, "status": status})


def notify_document_flagged(*, uploader_email: str | None, uploader_name: str, document_id: int,
                            reasons: list[str]) -> dict:
    subject = f"Document #{document_id} needs human review"
    body = f"Document #{document_id} was flagged for review:\n- " + "\n- ".join(reasons)
    return service.notify(to_email=uploader_email, to_name=uploader_name, subject=subject, body=body,
                          event="document.flagged", meta={"document_id": document_id, "reasons": reasons})
