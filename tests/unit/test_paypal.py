import os
import unittest
from unittest import mock

from integrations import paypal


class FakePayPal:
    """Records every call so tests can prove the right endpoints, methods and auth were used."""

    def __init__(self, token="tok_abc", order=None, order_after_capture=None):
        self.token, self.order, self.order_after_capture, self.calls = token, order or {}, order_after_capture, []

    def __call__(self, method, path, *, token=None, data=None, basic=None):
        self.calls.append((method, path, token, basic))
        if path == "/v1/oauth2/token":
            return {"access_token": self.token}
        if path.endswith("/capture"):
            return self.order_after_capture or self.order
        if path.startswith("/v2/checkout/orders/"):
            return self.order
        if path == "/v2/checkout/orders":
            return {"id": "ORDER123", "status": "CREATED",
                    "links": [{"rel": "approve", "href": "https://paypal.example/approve/ORDER123"}]}
        raise AssertionError("unexpected path " + path)


class ModeAndCredsTest(unittest.TestCase):
    def test_defaults_to_sandbox_and_requires_credentials(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(paypal.mode(), "sandbox")
            with self.assertRaises(paypal.PayPalError):
                paypal.get_access_token(FakePayPal())

    def test_live_mode_only_when_explicitly_set(self):
        with mock.patch.dict(os.environ, {"PAYPAL_MODE": "live"}, clear=True):
            self.assertEqual(paypal.mode(), "live")
        with mock.patch.dict(os.environ, {"PAYPAL_MODE": "anything-else"}, clear=True):
            self.assertEqual(paypal.mode(), "sandbox")


class CreatePaymentRequestTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"PAYPAL_CLIENT_ID": "cid", "PAYPAL_CLIENT_SECRET": "secret"}, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_authenticates_then_creates_an_order_and_returns_the_approval_link(self):
        fake = FakePayPal()
        r = paypal.create_payment_request("49.99", "USD", "BuildFlow subscription", "pay_123", request=fake)
        self.assertEqual(r, {"order_id": "ORDER123", "approval_link": "https://paypal.example/approve/ORDER123", "status": "CREATED"})
        self.assertEqual(fake.calls[0], ("POST", "/v1/oauth2/token", None, ("cid", "secret")))
        self.assertEqual(fake.calls[1][:3], ("POST", "/v2/checkout/orders", "tok_abc"))

    def test_missing_order_id_in_response_raises(self):
        fake = FakePayPal()
        fake.order = {}

        def broken(method, path, **kw):
            if path == "/v1/oauth2/token":
                return {"access_token": "t"}
            return {"status": "CREATED"}  # no "id"
        with self.assertRaises(paypal.PayPalError):
            paypal.create_payment_request("10", "USD", "x", "pay_1", request=broken)


class GetAndCaptureOrderTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"PAYPAL_CLIENT_ID": "cid", "PAYPAL_CLIENT_SECRET": "secret"}, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_get_order_is_read_only(self):
        fake = FakePayPal(order={"id": "ORDER123", "status": "COMPLETED"})
        r = paypal.get_order("ORDER123", request=fake)
        self.assertEqual(r["status"], "COMPLETED")
        self.assertEqual([c[:2] for c in fake.calls], [("POST", "/v1/oauth2/token"), ("GET", "/v2/checkout/orders/ORDER123")])

    def test_capture_order_posts_to_the_capture_endpoint(self):
        fake = FakePayPal(order_after_capture={"id": "ORDER123", "status": "COMPLETED"})
        r = paypal.capture_order("ORDER123", request=fake)
        self.assertEqual(r["status"], "COMPLETED")
        self.assertEqual(fake.calls[1][:2], ("POST", "/v2/checkout/orders/ORDER123/capture"))


if __name__ == "__main__":
    unittest.main()
