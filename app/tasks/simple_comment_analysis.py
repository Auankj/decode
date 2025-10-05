"""
Simplified comment analysis Celery task for testing
"""

from typing import Dict, Any
from app.core.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)

@celery_app.task(bind=True, max_retries=3)
def simple_analyze_comment_task(self, comment_data: Dict[str, Any]):
    """
    Simple version that just does pattern matching without complex DB ops
    """
    try:
        from app.services.pattern_matcher import ClaimPatternMatcher
        
        logger.info(f"Simple analysis for comment {comment_data.get('comment_id')}")
        
        # Analyze the comment using pattern matcher
        matcher = ClaimPatternMatcher()
        comment_body = comment_data.get('comment_body', '')
        comment_user = comment_data.get('comment_user', {})
        issue_data = comment_data.get('issue_data', {})
        
        analysis_result = matcher.analyze_comment(
            comment_text=comment_body,
            comment_data=comment_user,
            issue_data=issue_data
        )
        
        # Log the result
        if analysis_result.get('is_claim', False):
            logger.info(f"✅ CLAIM DETECTED: {analysis_result.get('final_score')}% confidence")
        else:
            logger.info(f"❌ No claim detected: {analysis_result.get('final_score')}% confidence")
        
        return {
            "status": "analyzed",
            "comment_id": comment_data.get("comment_id"),
            "is_claim": analysis_result.get('is_claim', False),
            "confidence_score": analysis_result.get('final_score', 0),
            "patterns_detected": len(analysis_result.get('detected_patterns', []))
        }
        
    except Exception as exc:
        logger.error(f"Simple analysis failed: {exc}")
        return {
            "status": "failed", 
            "error": str(exc),
            "comment_id": comment_data.get("comment_id")
        }