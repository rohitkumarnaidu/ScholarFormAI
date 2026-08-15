# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import logging
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.issue import Issue
from app.models.issue_settings import IssueSettings

logger = logging.getLogger(__name__)

class IntegrationsService:
    @staticmethod
    async def dispatch_webhooks(db: Session, issue: Issue) -> None:
        """
        Dispatches new issues to configured webhooks (Slack, Discord, etc).
        """
        result = db.execute(select(IssueSettings).limit(1))
        settings = result.scalar_one_or_none()
        
        if not settings:
            return

        async with httpx.AsyncClient() as client:
            if settings.slack_webhook_url:
                await IntegrationsService._send_slack(client, settings.slack_webhook_url, issue)
                
            if settings.discord_webhook_url:
                await IntegrationsService._send_discord(client, settings.discord_webhook_url, issue)

    @staticmethod
    async def _send_slack(client: httpx.AsyncClient, url: str, issue: Issue) -> None:
        payload = {
            "text": f"*{issue.type.upper()}*: {issue.title}\n*Priority*: {issue.priority}\n{issue.description[:200]}..."
        }
        try:
            await client.post(url, json=payload, timeout=5.0)
        except Exception as e:
            logger.error(f"Slack webhook failed: {e}")

    @staticmethod
    async def _send_discord(client: httpx.AsyncClient, url: str, issue: Issue) -> None:
        payload = {
            "content": f"**New {issue.type} reported:**\n**Title**: {issue.title}\n**Priority**: {issue.priority}"
        }
        try:
            await client.post(url, json=payload, timeout=5.0)
        except Exception as e:
            logger.error(f"Discord webhook failed: {e}")
