"""Generate narrowly scoped OpenWrt dnsmasq overrides for stock G3 migration.

Output only: never edits the router, changes DHCP, or triggers OTA.
"""
import argparse
import ipaddress

DOMAINS = (
    "newlifemulti.daikin-china.com.cn",
    "newlifemulti-cdh.daikin-china.com.cn",
    "newlifemulti-cdh-core.daikin-china.com.cn",
)


def dnsmasq_lines(host):
    address = ipaddress.IPv4Address(host)
    if address.is_multicast or address.is_unspecified or address.is_loopback or address.is_link_local:
        raise ValueError("Host must be a reachable LAN IPv4 address")
    return tuple(f"address=/{domain}/{address}" for domain in DOMAINS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="Windows migration service LAN IPv4")
    args = parser.parse_args()
    try:
        lines = dnsmasq_lines(args.host)
    except ipaddress.AddressValueError as exc:
        parser.error(str(exc))
    except ValueError as exc:
        parser.error(str(exc))
    print("# G3 migration ONLY; undo after migration.")
    print("# Configure ONLY the target G3 DHCP client to use OpenWrt as DNS.")
    print("# Other LAN clients may also resolve these names while overrides are active.")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
