from django.test import RequestFactory, SimpleTestCase, override_settings

from app.throttling import _client_ip


class ClientIpTests(SimpleTestCase):
    """X-Forwarded-For soxtalashtirilganda throttle aylanib o'tilmasligi kerak."""

    def _req(self, xff=None, remote="10.0.0.9"):
        extra = {"REMOTE_ADDR": remote}
        if xff is not None:
            extra["HTTP_X_FORWARDED_FOR"] = xff
        return RequestFactory().get("/", **extra)

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_spoofed_first_hop_is_ignored(self):
        # Mijoz "1.2.3.4" yozdi; proksi haqiqiy IP (203.0.113.7) ni oxiriga qo'shdi.
        req = self._req("1.2.3.4, 203.0.113.7")
        self.assertEqual(_client_ip(req), "203.0.113.7")

    @override_settings(TRUSTED_PROXY_COUNT=2)
    def test_two_proxies(self):
        req = self._req("1.2.3.4, 203.0.113.7, 172.16.0.1")
        self.assertEqual(_client_ip(req), "203.0.113.7")

    @override_settings(TRUSTED_PROXY_COUNT=0)
    def test_header_ignored_when_no_proxy(self):
        req = self._req("1.2.3.4", remote="198.51.100.5")
        self.assertEqual(_client_ip(req), "198.51.100.5")

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_no_header_falls_back_to_remote_addr(self):
        self.assertEqual(_client_ip(self._req()), "10.0.0.9")
