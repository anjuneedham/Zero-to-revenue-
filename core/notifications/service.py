"""Owner alerts with priority (spec sections 25-26). CRITICAL/HIGH/MEDIUM go to WhatsApp when
configured; LOW is stored for the dashboard only (no spam). Dedupe keys stop repeats."""

import os

from core.notifications.notify import notify
from integrations.notifications.twilio_whatsapp import RecordOnly, TwilioWhatsApp

PUSH = {"CRITICAL", "HIGH", "MEDIUM"}


def backend():
    return TwilioWhatsApp() if TwilioWhatsApp.configured() else RecordOnly()


def alert(conn, priority: str, dedupe_key: str, title: str, body: str, backend_override=None) -> bool:
    b = backend_override or (backend() if priority in PUSH else RecordOnly())
    return notify(conn, b, os.environ.get("WHATSAPP_TO", "owner"), priority, dedupe_key, title, body,
                  channel=getattr(b, "channel", "dashboard"))
