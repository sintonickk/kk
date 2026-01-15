import json
import platform
import socket
import subprocess
import time
from datetime import datetime

try:
    import psutil  # type: ignore
except Exception:
    psutil = None  # type: ignore


def _cpu_info():
    usage = None
    count = None
    try:
        if psutil:
            usage = float(psutil.cpu_percent(interval=0.2))
            count = int(psutil.cpu_count(logical=True) or 0)
    except Exception:
        usage = None
    return {"percent": usage, "cores_logical": count}


def _memory_info():
    total = used = percent = None
    try:
        if psutil:
            mem = psutil.virtual_memory()
            total = int(mem.total)
            used = int(mem.used)
            percent = float(mem.percent)
    except Exception:
        pass
    return {"total": total, "used": used, "percent": percent}


def _parse_nvidia_smi():
    gpus = []
    try:
        # utilization.gpu in %, memory.total/used in MiB, name, index
        cmd = [
            "nvidia-smi",
            "--query-gpu=index,name,utilization.gpu,memory.total,memory.used",
            "--format=csv,noheader,nounits",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        if proc.returncode != 0:
            return []
        for line in proc.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue
            idx, name, util, mem_total, mem_used = parts[:5]
            try:
                idx_i = int(idx)
            except Exception:
                idx_i = None
            try:
                util_f = float(util)
            except Exception:
                util_f = None
            try:
                mt = float(mem_total)
                mu = float(mem_used)
                mp = (mu / mt * 100.0) if (mt and mt > 0) else None
            except Exception:
                mt = mu = mp = None
            gpus.append(
                {
                    "index": idx_i,
                    "name": name,
                    "util_percent": util_f,
                    "memory_total_mib": mt,
                    "memory_used_mib": mu,
                    "memory_percent": mp,
                }
            )
    except Exception:
        return []
    return gpus


essential_keys = (
    "system",
    "node",
    "release",
    "version",
    "machine",
    "processor",
)


def get_system_info():
    ts = datetime.now().isoformat()
    info = {}
    try:
        uname = platform.uname()
        info.update({k: getattr(uname, k, None) for k in essential_keys})
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = None
    try:
        ip = socket.gethostbyname(hostname) if hostname else None
    except Exception:
        ip = None

    data = {
        "timestamp": ts,
        "host": {"hostname": hostname, "ip": ip},
        "cpu": _cpu_info(),
        "memory": _memory_info(),
        "gpus": _parse_nvidia_smi(),
        "platform": info,
    }
    return data


if __name__ == "__main__":
    # simple probe loop for quick testing
    for _ in range(1):
        print(json.dumps(get_system_info(), ensure_ascii=False, indent=2))
        time.sleep(1)
