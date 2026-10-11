from __future__ import annotations

from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_session
from app.models import Check, VocabularyList
from app.schemas.checks import CheckDetail, CheckResults, CheckSummary, StudentResult
from app.services.result_service import ResultService

SessionDep = Annotated[AsyncSession, Depends(get_session)]
ApiTokenHeader = Annotated[str | None, Header(alias="X-API-Token")]


async def require_api_token(x_api_token: ApiTokenHeader = None) -> None:
    if not settings.api_token:
        return
    if x_api_token is None or not compare_digest(x_api_token, settings.api_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )


router = APIRouter(
    prefix="/api/v1",
    tags=["checks"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/checks", response_model=list[CheckSummary])
async def list_checks(session: SessionDep) -> list[Check]:
    result = await session.execute(select(Check).order_by(Check.created_at.desc()))
    return list(result.scalars())


@router.get("/checks/{check_id}", response_model=CheckDetail)
async def get_check(check_id: int, session: SessionDep) -> CheckDetail:
    result = await session.execute(
        select(Check)
        .where(Check.id == check_id)
        .options(selectinload(Check.vocabulary_list).selectinload(VocabularyList.items))
    )
    check = result.scalar_one_or_none()
    if check is None:
        raise HTTPException(status_code=404, detail="Check not found")
    return CheckDetail(
        id=check.id,
        title=check.title,
        time_limit_seconds=check.time_limit_seconds,
        status=check.status.value,
        started_at=check.started_at,
        vocabulary_list_id=check.vocabulary_list_id,
        total_words=len(check.vocabulary_list.items),
    )


@router.get("/checks/{check_id}/results", response_model=CheckResults)
async def get_check_results(check_id: int, session: SessionDep) -> CheckResults:
    exists = await session.scalar(select(func.count(Check.id)).where(Check.id == check_id))
    if not exists:
        raise HTTPException(status_code=404, detail="Check not found")
    return await ResultService(session).get_check_results(check_id)


@router.get("/users/{user_id}/results", response_model=list[StudentResult])
async def get_user_results(user_id: int, session: SessionDep) -> list[StudentResult]:
    return await ResultService(session).get_user_results(user_id)
