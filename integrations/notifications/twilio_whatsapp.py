"""WhatsApp via Twilio (owner only). Credentials come from the environment, never from code.
Sandbox numbers work for free testing; production senders need Twilio/Meta approval."""

import base64
import os
import urllib.parse
import urllib.request


class TwilioWhatsApp:
    mode = "HUMAN_APPROVED"
    channel = "whatsapp"

    def __init__(self):
        self.sid = os.environ["TWILIO_ACCOUNT_SID"]
        self.token = os.environ["TWILIO_AUTH_TOKEN"]
        self.sender = os.environ["TWILIO_WHATSAPP_FROM"]  # e.g. whatsapp:+14155238886 (sandbox)

    @staticmethod
    def configured() -> bool:
        return all(os.environ.get(k) for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM", "WHATSAPP_TO"))

    def send(self, to: str, title: str, body: str) -> None:
        to = to if to.startswith("whatsapp:") else "whatsapp:" + to
        sender = self.sender if self.sender.startswith("whatsapp:") else "whatsapp:" + self.sender
        data = urllib.parse.urlencode({"From": sender, "To": to, "Body": f"{title}\n{body}"[:1500]}).encode()
        req = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{urllib.parse.quote(self.sid)}/Messages.json", data=data,
            headers={"Authorization": "Basic " + base64.b64encode(f"{self.sid}:{self.token}".encode()).decode()})
        with urllib.request.urlopen(req, timeout=15) as r:  # nosec - fixed https host
            if r.status >= 300:
                raise RuntimeError(f"twilio status {r.status}")


class RecordOnly:
    """Used until Twilio is configured: the notification is stored and shown on the dashboard only."""
    mode = "MOCK"
    channel = "dashboard"

    def send(self, to, title, body):
        return None
