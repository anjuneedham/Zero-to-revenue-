import base64
import os
import unittest
from email import message_from_bytes
from unittest import mock

from integrations import gmail


class FakeGoogle:
    def __init__(self, token="tok_abc", send_response=None, fail_send=False):
        self.token, self.send_response, self.fail_send, self.calls = token, send_response, fail_send, []

    def __call__(self, method, url, *, token=None, data=None, form=False):
        self.calls.append((method, url, token, data, form))
        if url == gmail.TOKEN_URL:
            return {"access_token": self.token}
        if url == gmail.SEND_URL:
            if self.fail_send:
                return {}
            return self.send_response or {"id": "msg_1", "threadId": "thr_1"}
        raise AssertionError("unexpected url " + url)


ENV = {"GMAIL_CLIENT_ID": "cid", "GMAIL_CLIENT_SECRET": "secret",
       "GMAIL_REFRESH_TOKEN": "refresh", "GMAIL_SENDER_EMAIL": "me@yardscaledigital.com"}


class CredentialsTest(unittest.TestCase):
    def test_requires_all_four_env_vars(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(gmail.GmailError):
                gmail.get_access_token(FakeGoogle())
        with mock.patch.dict(os.environ, {**ENV, "GMAIL_SENDER_EMAIL": ""}, clear=True):
            with self.assertRaises(gmail.GmailError):
                gmail.send_email("x@x.com", "s", "b")


class SendEmailTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, ENV, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_authenticates_then_sends_and_returns_ids(self):
        fake = FakeGoogle()
        r = gmail.send_email("client@example.com", "Hello", "Body text", request=fake)
        self.assertEqual(r, {"message_id": "msg_1", "thread_id": "thr_1"})
        self.assertEqual(fake.calls[0][:2], ("POST", gmail.TOKEN_URL))
        self.assertEqual(fake.calls[1][:3], ("POST", gmail.SEND_URL, "tok_abc"))

    def test_sends_from_the_configured_sender_to_the_right_recipient_with_the_right_subject(self):
        fake = FakeGoogle()
        gmail.send_email("client@example.com", "A subject line", "The body", request=fake)
        raw_json = fake.calls[1][3]
        import json
        raw = json.loads(raw_json)["raw"]
        padded = raw + "=" * (-len(raw) % 4)
        msg = message_from_bytes(base64.urlsafe_b64decode(padded))
        self.assertEqual(msg["To"], "client@example.com")
        self.assertEqual(msg["From"], "me@yardscaledigital.com")
        self.assertEqual(msg["Subject"], "A subject line")
        self.assertEqual(msg.get_payload(decode=True).decode().strip(), "The body")

    def test_missing_message_id_raises(self):
        with self.assertRaises(gmail.GmailError):
            gmail.send_email("x@x.com", "s", "b", request=FakeGoogle(fail_send=True))

    def test_missing_access_token_raises(self):
        with self.assertRaises(gmail.GmailError):
            gmail.send_email("x@x.com", "s", "b", request=FakeGoogle(token=None))


if __name__ == "__main__":
    unittest.main()
