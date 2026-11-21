import unittest

from scripts.g3_openwrt_dns import DOMAINS, dnsmasq_lines


class G3OpenWrtDNSTests(unittest.TestCase):
    def test_exact_upstream_hosts(self):
        self.assertEqual(len(DOMAINS), 3)
        self.assertEqual(dnsmasq_lines("192.168.1.10"), tuple(
            f"address=/{domain}/192.168.1.10" for domain in DOMAINS
        ))

    def test_reject_unusable_addresses(self):
        for address in ("127.0.0.1", "0.0.0.0", "224.0.0.1", "169.254.1.1", "not-an-ip", "::1"):
            with self.subTest(address=address), self.assertRaises(ValueError):
                dnsmasq_lines(address)


if __name__ == "__main__":
    unittest.main()
