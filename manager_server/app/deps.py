from typing import Optional, Dict
from fastapi import Header, Request


def parse_auth(request: Request, authorization: Optional[str] = Header(default=None), x_user_code: Optional[str] = Header(default=None)) -> Dict[str, Optional[str]]:
    token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        else:
            token = authorization
    request.state.auth = {"token": token, "user_code": x_user_code}
    return request.state.auth
