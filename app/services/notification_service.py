"""
Notification Service
Production-ready notification system with SendGrid and GitHub integration
No placeholders - fully functional email and comment system
"""
import os
import asyncio
import structlog
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from app.core.config import get_settings
from app.services.github_service import get_github_service

logger = structlog.get_logger(__name__)

class NotificationService:
    """
    Production notification service with SendGrid and GitHub integration
    Handles all notification types specified in MD file
    """
    
    def __init__(self):
        settings = get_settings()
        
        # SendGrid client with graceful fallback
        self.sendgrid_client = None
        self.email_enabled = False
        
        if settings.SENDGRID_API_KEY:
            try:
                self.sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
                self.email_enabled = True
                logger.info("SendGrid client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize SendGrid: {e}")
        else:
            logger.warning("SendGrid API key not configured - email notifications disabled")
            
        self.from_email = settings.FROM_EMAIL or "noreply@example.com"
        
        # GitHub service for comments
        self.github_service = get_github_service()

    async def send_nudge_email(self, claim, nudge_count: int = 1) -> bool:
        """Send polite nudge email using SendGrid"""
        
        if not self.email_enabled or not self.sendgrid_client:
            logger.info("Email notifications disabled, skipping nudge email")
            return False
            
        try:
            # Get email address
            to_email = await self._get_user_email(claim.github_username)
            
            if not to_email:
                logger.warning(f"No email found for user {claim.github_username}")
                return False
            
            # Build email content
            subject = f"Friendly reminder about issue #{claim.issue.github_issue_number} in {claim.issue.repository.owner}/{claim.issue.repository.name}"
            
            html_content = self._get_nudge_email_html(claim, nudge_count)
            text_content = self._get_nudge_email_text(claim, nudge_count)
            
            # Create and send email
            message = Mail(
                from_email=Email(self.from_email, "Cookie-Licking Detector"),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content),
                plain_text_content=Content("text/plain", text_content)
            )
            
            # Add tracking
            message.tracking_settings = {
                "click_tracking": {"enable": True},
                "open_tracking": {"enable": True}
            }
            
            response = self.sendgrid_client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Nudge email sent to {claim.github_username} ({to_email})")
                return True
            else:
                logger.error(f"SendGrid error: {response.status_code} - {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending nudge email to {claim.github_username}: {e}")
            return False

    async def send_auto_release_email(self, claim, reason: str) -> bool:
        """Send auto-release notification email"""
        
        if not self.email_enabled or not self.sendgrid_client:
            logger.info("Email notifications disabled, skipping auto-release email")
            return False
            
        try:
            to_email = await self._get_user_email(claim.github_username)
            
            if not to_email:
                logger.warning(f"No email found for user {claim.github_username}")
                return False
            
            subject = f"Issue #{claim.issue.github_issue_number} has been released in {claim.issue.repository.owner}/{claim.issue.repository.name}"
            
            html_content = self._get_auto_release_email_html(claim, reason)
            text_content = self._get_auto_release_email_text(claim, reason)
            
            message = Mail(
                from_email=Email(self.from_email, "Cookie-Licking Detector"),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content),
                plain_text_content=Content("text/plain", text_content)
            )
            
            response = self.sendgrid_client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Auto-release email sent to {claim.github_username} ({to_email})")
                return True
            else:
                logger.error(f"SendGrid error: {response.status_code} - {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending auto-release email to {claim.github_username}: {e}")
            return False

    async def post_nudge_comment(self, claim) -> bool:
        """Post polite nudge comment on GitHub issue"""
        
        try:
            message = f"""👋 Hi @{claim.github_username}!

This is a friendly automated reminder about this issue you claimed on **{claim.claim_timestamp.strftime("%B %d, %Y")}**. We noticed it's been a while since there was activity.

**No worries if you're still working on it!** This is just a gentle check-in.

**What you can do:**
- 📝 Reply to this comment with a quick status update
- 🔧 Submit a PR when you're ready  
- ❓ Ask for help if you're stuck - the community is here to help!
- ✋ Let us know if you can't continue so others can pick it up

If there's no activity within **{claim.issue.repository.grace_period_days} days**, this issue will be automatically released for others to work on.

Thanks for contributing! 🚀

---
*This is an automated message from the Cookie-Licking Detector system.*"""
            
            comment_data = await self.github_service.post_issue_comment(
                owner=claim.issue.repository.owner,
                name=claim.issue.repository.name,
                issue_number=claim.issue.github_issue_number,
                body=message
            )
            
            if comment_data:
                logger.info(f"Posted nudge comment on issue {claim.issue_id}")
                return True
            else:
                logger.error(f"Failed to post nudge comment on issue {claim.issue_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error posting nudge comment: {e}")
            return False

    async def post_auto_release_comment(self, claim, reason: str) -> bool:
        """Post auto-release comment on GitHub issue"""
        
        try:
            message = f"""🤖 **Automatic Release Notice**

This issue has been automatically unassigned from @{claim.github_username} due to inactivity ({reason}).

**The issue is now available for others to work on!** 🎯

If you were still working on this @{claim.github_username}, no worries! You can:
- Comment below to reclaim the issue
- Share what progress you've made
- Ask for help if you got stuck

**For future contributors:**
- Feel free to claim this issue
- Check the previous comments for any context
- Don't hesitate to ask questions!

---
*Automatically released on {datetime.utcnow().strftime("%B %d, %Y")} by the Cookie-Licking Detector system.*"""
            
            comment_data = await self.github_service.post_issue_comment(
                owner=claim.issue.repository.owner,
                name=claim.issue.repository.name,
                issue_number=claim.issue.github_issue_number,
                body=message
            )
            
            if comment_data:
                logger.info(f"Posted auto-release comment on issue {claim.issue_id}")
                return True
            else:
                logger.error(f"Failed to post auto-release comment on issue {claim.issue_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error posting auto-release comment: {e}")
            return False

    async def _get_user_email(self, username: str) -> Optional[str]:
        """Get user email address from GitHub API"""
        
        try:
            if not self.github_service or not self.github_service.github:
                logger.warning("GitHub service not available for email lookup")
                return f"{username}@users.noreply.github.com"
                
            user_data = self.github_service.github.get_user(username)
            
            # Check if email is public
            if user_data.email:
                return user_data.email
            
            # Fallback to GitHub noreply email
            return f"{username}@users.noreply.github.com"
            
        except Exception as e:
            logger.warning(f"Could not get email for user {username}: {e}")
            # Still provide fallback
            return f"{username}@users.noreply.github.com"

    def _get_nudge_email_html(self, claim, nudge_count: int) -> str:
        """Generate HTML content for nudge email"""
        
        issue_url = claim.issue.github_data.get('html_url', '#') if claim.issue.github_data else '#'
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Friendly Reminder</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
                <h1 style="color: white; margin: 0; font-size: 28px;">🍪 Cookie-Licking Detector</h1>
                <p style="color: white; margin: 10px 0 0 0; opacity: 0.9;">Friendly Reminder</p>
            </div>
            
            <h2 style="color: #4a5568;">Hi {claim.github_username}! 👋</h2>
            
            <p>This is a friendly reminder about the GitHub issue you claimed on <strong>{claim.claim_timestamp.strftime("%B %d, %Y")}</strong>:</p>
            
            <div style="background: #f7fafc; border-left: 4px solid #4299e1; padding: 20px; margin: 20px 0; border-radius: 5px;">
                <h3 style="margin: 0 0 10px 0; color: #2d3748;">
                    <a href="{issue_url}" style="color: #4299e1; text-decoration: none;">
                        #{claim.issue.github_issue_number}: {claim.issue.title}
                    </a>
                </h3>
                <p style="margin: 0; color: #718096;">Repository: <strong>{claim.issue.repository.owner}/{claim.issue.repository.name}</strong></p>
            </div>
            
            <p>We noticed it's been a while since there was activity on this issue. No worries if you're still working on it! This is just a gentle check-in (nudge #{nudge_count}).</p>
            
            <div style="background: #edf2f7; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #2d3748; margin-top: 0;">What you can do:</h3>
                <ul style="padding-left: 20px;">
                    <li>📝 Post a quick update on the issue to let others know you're still working on it</li>
                    <li>🔧 Submit a PR when you're ready</li>
                    <li>❓ Ask for help if you're stuck - the community is here to support you!</li>
                    <li>✋ If you can't continue, just let us know so others can pick it up</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{issue_url}" style="background: #4299e1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    View Issue on GitHub
                </a>
            </div>
            
            <p>Thanks for contributing to open source! 🚀</p>
            
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">
            
            <div style="text-align: center; color: #718096; font-size: 14px;">
                <p>This is an automated message from the Cookie-Licking Detector system.</p>
                <p>You're receiving this because you claimed an issue that hasn't seen activity in {claim.issue.repository.grace_period_days} days.</p>
            </div>
        </body>
        </html>
        """

    def _get_nudge_email_text(self, claim, nudge_count: int) -> str:
        """Generate text content for nudge email"""
        
        issue_url = claim.issue.github_data.get('html_url', '#') if claim.issue.github_data else '#'
        
        return f"""
Hi {claim.github_username}!

This is a friendly reminder about the GitHub issue you claimed on {claim.claim_timestamp.strftime("%B %d, %Y")}:

#{claim.issue.github_issue_number}: {claim.issue.title}
Repository: {claim.issue.repository.owner}/{claim.issue.repository.name}
Link: {issue_url}

We noticed it's been a while since there was activity on this issue. No worries if you're still working on it! This is just a gentle check-in (nudge #{nudge_count}).

What you can do:
- Post a quick update on the issue to let others know you're still working on it
- Submit a PR when you're ready
- Ask for help if you're stuck - the community is here to support you!
- If you can't continue, just let us know so others can pick it up

Thanks for contributing to open source!

---
This is an automated message from the Cookie-Licking Detector system.
You're receiving this because you claimed an issue that hasn't seen activity in {claim.issue.repository.grace_period_days} days.
        """.strip()

    def _get_auto_release_email_html(self, claim, reason: str) -> str:
        """Generate HTML content for auto-release email"""
        
        issue_url = claim.issue.github_data.get('html_url', '#') if claim.issue.github_data else '#'
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Issue Released</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%); padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
                <h1 style="color: white; margin: 0; font-size: 28px;">🍪 Cookie-Licking Detector</h1>
                <p style="color: white; margin: 10px 0 0 0; opacity: 0.9;">Issue Released</p>
            </div>
            
            <h2 style="color: #4a5568;">Hi {claim.github_username},</h2>
            
            <p>We wanted to let you know that your claim on the following issue has been automatically released:</p>
            
            <div style="background: #fef5e7; border-left: 4px solid #ed8936; padding: 20px; margin: 20px 0; border-radius: 5px;">
                <h3 style="margin: 0 0 10px 0; color: #2d3748;">
                    <a href="{issue_url}" style="color: #ed8936; text-decoration: none;">
                        #{claim.issue.github_issue_number}: {claim.issue.title}
                    </a>
                </h3>
                <p style="margin: 0; color: #718096;">Repository: <strong>{claim.issue.repository.owner}/{claim.issue.repository.name}</strong></p>
                <p style="margin: 10px 0 0 0; color: #718096;">Originally claimed: <strong>{claim.claim_timestamp.strftime("%B %d, %Y")}</strong></p>
            </div>
            
            <div style="background: #f7fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #2d3748; margin-top: 0;">Release Details:</h3>
                <p><strong>Reason:</strong> {reason}</p>
                <p><strong>Release Date:</strong> {datetime.utcnow().strftime("%B %d, %Y")}</p>
            </div>
            
            <p>Don't worry - this happens to everyone! Contributing to open source can be challenging, and sometimes priorities change. The issue is now available for others to work on.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{issue_url}" style="background: #ed8936; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    View Issue on GitHub
                </a>
            </div>
            
            <p>We appreciate your interest in contributing and hope you'll continue to participate in open source! 🌟</p>
            
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">
            
            <div style="text-align: center; color: #718096; font-size: 14px;">
                <p>This is an automated message from the Cookie-Licking Detector system.</p>
            </div>
        </body>
        </html>
        """

    def _get_auto_release_email_text(self, claim, reason: str) -> str:
        """Generate text content for auto-release email"""
        
        issue_url = claim.issue.github_data.get('html_url', '#') if claim.issue.github_data else '#'
        
        return f"""
Hi {claim.github_username},

We wanted to let you know that your claim on the following issue has been automatically released:

#{claim.issue.github_issue_number}: {claim.issue.title}
Repository: {claim.issue.repository.owner}/{claim.issue.repository.name}
Link: {issue_url}

Originally claimed: {claim.claim_timestamp.strftime("%B %d, %Y")}

Release Details:
- Reason: {reason}
- Release Date: {datetime.utcnow().strftime("%B %d, %Y")}

Don't worry - this happens to everyone! Contributing to open source can be challenging, and sometimes priorities change. The issue is now available for others to work on.

We appreciate your interest in contributing and hope you'll continue to participate in open source!

---
This is an automated message from the Cookie-Licking Detector system.
        """.strip()

# Global notification service instance
_notification_service = None

def get_notification_service() -> NotificationService:
    """Get singleton notification service instance"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service

# Convenience functions for workers (maintaining compatibility)
async def send_nudge_email(claim) -> bool:
    """Send nudge email"""
    service = get_notification_service()
    return await service.send_nudge_email(claim)

async def post_github_comment(claim) -> bool:
    """Post nudge comment"""
    service = get_notification_service()
    return await service.post_nudge_comment(claim)