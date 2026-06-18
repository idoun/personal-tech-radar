from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = 'HS256'


def get_current_session_user_id(request: Request) -> int:
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='로그인이 필요합니다.')
    if not settings.auth_secret_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='인증 설정이 비어 있습니다.')

    try:
        payload = jwt.decode(token, settings.auth_secret_key, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='세션이 만료되었거나 유효하지 않습니다.')

    subject = payload.get('sub')
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='유효하지 않은 세션입니다.')

    try:
        return int(subject)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='유효하지 않은 세션입니다.')


def require_authenticated_user(_user_id: int = Depends(get_current_session_user_id)) -> int:
    return _user_id
