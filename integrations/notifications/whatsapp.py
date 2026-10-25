"""WhatsApp notifications (owner only).

Two backends behind one interface:
  * MockWhatsApp   - records messages in memory (MODE: MOCK). Default.
  * CloudWhatsApp  - Meta WhatsApp Business Cloud API. Needs a business account,
    an approved message template for owner-initiated messages (free-form text
    only works inside the 24h customer-service window) and a token supplied via
    environment variables. Not wired up until the owner approves the cost/setup
    (spec section 39).
Never put secrets, keys or seed phrases in a message.
"""

import json
import os
import urllib.request


class MockWhatsApp:
    mode = "MOCK"

    def __init__(self):
        self.sent = []

    def send(self, to: str, title: str, body: str) -> None:
        self.sent.append((to, title, body))


class CloudWhatsApp:
    mode = "READ_ONLY"  # outbound text to the owner only; no inbound command handling

    def __init__(self, token=None, phone_number_id=None, template=None):
        self.token = token or os.environ["WHATSAPP_TOKEN"]
        self.phone_number_id = phone_number_id or os.environ["WHATSAPP_PHONE_NUMBER_ID"]
        self.template = template or os.environ.get("WHATSAPP_TEMPLATE", "")

    def send(self, to: str, title: str, body: str) -> None:
        payload = {"messaging_product": "whatsapp", "to": to, "type": "template",
                   "template": {"name": self.template, "language": {"code": "en"},
                                "components": [{"type": "body", "parameters": [
                                    {"type": "text", "text": f"{title}: {body}"[:900]}]}]}}
        req = urllib.request.Request(
            f"https://graph.facebook.com/v21.0/{self.phone_number_id}/messages",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15)  # nosec - fixed https URL
