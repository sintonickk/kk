import socket
import psutil
from typing import List

def get_all_external_ips(test_connect: bool = False, timeout: float = 0.5) -> List[str]:
    ips = []
    try:
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        for ifname, if_addrs in addrs.items():
            st = stats.get(ifname)
            if not st or not getattr(st, "isup", False):
                continue
            lname = str(ifname).lower()
            if lname.startswith(("lo", "docker", "veth", "br-", "virbr", "l4tbr")):
                continue
            for a in if_addrs:
                if a.family == socket.AF_INET:
                    ip = a.address
                    if not ip or ip.startswith("127."):
                        continue
                    if test_connect:
                        try:
                            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                            s.settimeout(timeout)
                            s.bind((ip, 0))
                            s.connect(("8.8.8.8", 80))
                            s.close()
                            ips.append(ip)
                        except Exception:
                            pass
                    else:
                        ips.append(ip)
        seen = set()
        ordered = []
        for ip in ips:
            if ip not in seen:
                seen.add(ip)
                ordered.append(ip)
        return ordered
    except Exception:
        return []

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        if ip and not ip.startswith("127."):
            return ip
        lst = get_all_external_ips()
        if lst:
            return lst[0]
        return ip or "127.0.0.1"
    except Exception:
        lst = get_all_external_ips()
        if lst:
            return lst[0]
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"
