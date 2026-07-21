# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    VerifyOTPRequest,
)
from app.schemas.user import User
from app.services.auth_service import AuthService
from app.utils.dependencies import get_current_user
from app.utils.logging_context import bind_request_context

from ._helpers import run_enveloped

logger = logging.getLogger(__name__)

_limiter = Limiter(key_func=get_remote_address)

router = APIRouter(dependencies=[Depends(bind_request_context)])


@router.get("/me")
async def read_users_me(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    async def operation():
        return current_user

    return await run_enveloped(
        request,
        operation,
        code_map={401: "UNAUTHORIZED"},
        logger=logger,
        operation_name="auth me",
    )


@router.post("/signup")
@_limiter.limit("10/minute")
async def signup(
    request: Request,
    payload: SignupRequest,
):
    async def operation():
        return await AuthService.signup(
            payload.email,
            payload.password,
            payload.full_name,
            payload.institution,
        )

    return await run_enveloped(
        request,
        operation,
        code_map={422: "INVALID_SIGNUP_REQUEST"},
        logger=logger,
        operation_name="auth signup",
    )


@router.post("/login")
@_limiter.limit("10/minute")
async def login(
    request: Request,
    payload: LoginRequest,
):
    async def operation():
        return await AuthService.login(payload.email, payload.password)

    return await run_enveloped(
        request,
        operation,
        code_map={
            401: "AUTH_FAILED",
            422: "INVALID_LOGIN_REQUEST",
        },
        logger=logger,
        operation_name="auth login",
    )


@router.post("/forgot-password")
@_limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
):
    async def operation():
        return await AuthService.forgot_password(payload.email)

    return await run_enveloped(
        request,
        operation,
        code_map={422: "INVALID_FORGOT_PASSWORD_REQUEST"},
        logger=logger,
        operation_name="auth forgot password",
    )


@router.post("/verify-otp")
async def verify_otp(
    request: Request,
    payload: VerifyOTPRequest,
):
    async def operation():
        return await AuthService.verify_otp(payload.email, payload.otp)

    return await run_enveloped(
        request,
        operation,
        code_map={422: "INVALID_OTP_REQUEST"},
        logger=logger,
        operation_name="auth verify otp",
    )


@router.post("/reset-password")
@_limiter.limit("5/minute")
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
):
    async def operation():
        return await AuthService.reset_password(payload.email, payload.otp, payload.new_password)

    return await run_enveloped(
        request,
        operation,
        code_map={422: "INVALID_RESET_PASSWORD_REQUEST"},
        logger=logger,
        operation_name="auth reset password",
    )
