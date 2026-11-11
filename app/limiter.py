from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_real_ip(request: Request) -> str:
    client_ip = get_remote_address(request)
    if client_ip in ("127.0.0.1", "::1"):
        forwarded = request.headers.get("x-forwarded-for") or request.headers.get("cf-connecting-ip")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return client_ip


limiter = Limiter(key_func=get_real_ip)
