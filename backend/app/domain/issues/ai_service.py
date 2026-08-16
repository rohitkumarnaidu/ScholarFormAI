# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import json
import logging
from typing import Dict, Any, Optional

import litellm
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.issue import Issue
from app.models.issue_settings import IssueSettings

logger = logging.getLogger(__name__)


class IssueAIService:
    @staticmethod
    def get_settings(db: Session) -> IssueSettings:
        # Fetch the first settings object or return default
        result = db.execute(select(IssueSettings).limit(1))
        settings = result.scalar_one_or_none()
        if not settings:
            settings = IssueSettings()
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    @staticmethod
    async def categorize_issue(db: Session, title: str, description: str) -> Dict[str, Any]:
        """
        Uses the fast triage model to categorize the issue.
        """
        settings = IssueAIService.get_settings(db)
        model = settings.triage_model or "gpt-4o-mini"

        prompt = f"""
        Analyze the following issue report and provide a JSON response with:
        - category: one of [bug, feature_request, feedback, performance, security, crash, question, other]
        - priority: one of [low, medium, high, critical]
        - is_spam: boolean
        
        Title: {title}
        Description: {description}
        """

        try:
            response = await litellm.acompletion(
                model=model, messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"Error in triage LLM call: {e}")
            return {"category": "other", "priority": "medium", "is_spam": False}

    @staticmethod
    async def generate_suggested_fix(
        db: Session, title: str, description: str, system_info: Optional[Dict] = None
    ) -> str:
        """
        Uses the complex reasoning model to analyze and suggest a fix.
        """
        settings = IssueAIService.get_settings(db)
        model = settings.reasoning_model or "claude-3-5-sonnet"

        prompt = f"""
        You are an expert software engineer. Analyze the following issue report and provide a highly technical, actionable suggested fix or root cause analysis.
        
        Title: {title}
        Description: {description}
        System Info: {json.dumps(system_info) if system_info else "None"}
        """

        try:
            response = await litellm.acompletion(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a senior developer analyzing bug reports."},
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in reasoning LLM call: {e}")
            return "AI failed to generate a suggested fix due to model error or configuration issue."
