
import platform
import re
import subprocess
import ipaddress

def ping_device(ip: str) -> dict:
    """Check whether an IPv4 device rsponds to ICMP ping."""

    # Validate the IP adress before passing it to the system.
    try:
        address = ipaddress.IPv4Address(ip)
    except ipaddress.AddressValueError:
        return {
            "ip": ip,
            "status": "invalid",
            "latency_ms": None,
            "error": "Invalid IPv4 address",
        }

    ip = str(address)
    is_windows = platform.system() == "Windows"

    command = (
        ["ping", "-n", "1", "-w", "2000", ip]
        if is_windows
        else ["ping", "-c", "1", "-W", "2", ip]
    )

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            errors="replace",
        )

        output = result.stdout

        if result.returncode != 0:
            return {
                "ip": ip,
                "status": "unreachable",
                "latency_ms": None,
            }

        match = re.search(
            r"(?:time|temps|tiempo)\s*([=<])\s*(\d+(?:[.,]\d+)?)\s*m(?:s)?",
            output,
            re.IGNORECASE,
        )

        latency = (
            float(match.group(2).replace(",", "."))
            if match
            else None
        )

        latency_below_ms = match.group(1) == "<" if match else False
        return {
            "ip": ip,
            "status": "reachable",
            "latency_ms": latency,
            "latency_below_ms": latency_below_ms,
            "protocol": "ICMP",
        }

    except (subprocess.TimeoutExpired, OSError) as error:
        return {
            "ip": ip,
            "status": "error",
            "latency_ms": None,
            "error": str(error),
        }
        
        