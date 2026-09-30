"""
author: anrf
date:9/11/2026
desc:
"""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from anrf0911.app.schemas.user import CurrentUser
from anrf0911.common.config import *


class AuthService:
    def get_current_user(self, authorization:str | None) -> CurrentUser:
        if not authorization or not authorization.lower().startswith('bearer '):
            raise HTTPException(status_code=401, detail='没有Bearer')

        settings = get_settings()
        token = authorization.split(" ", 1)[1]
        try:
            payload = jwt.decode(token,settings.jwt_secret,algorithms=[settings.jwt_algorithm],options={'require':['exp','user_id','role']})
            user = CurrentUser(user_id=payload['user_id'],role=payload['role'])

        except Exception as e:
            raise HTTPException(status_code=401, detail=str(e))

        return user

    def get_authorized_user(self,authorization:str,*roles) -> CurrentUser:
        user =  self.get_current_user(authorization)
        if user.role not in roles:
            raise HTTPException(status_code=403,detail='当前角色无权访问')

        return user

    def encode_access_token(self,user:CurrentUser,expires_minutes:int = 30):
        settings = get_settings()
        payload = {
            'user_id':user.user_id,
            'role':user.role,
            'exp':datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
        }
        return jwt.encode(payload,settings.jwt_secret,algorithm=settings.jwt_algorithm)


