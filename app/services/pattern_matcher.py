"""
Comment Pattern Matching Engine
Implements multi-level pattern detection as specified in MD file:
- Direct Claims (95% confidence)
- Assignment Requests (90% confidence) 
- Questions (70% confidence)
- Progress Updates (for progress tracking)
- Context analysis (+10% for maintainer replies)
"""
import re
from typing import Dict, List, Optional
from enum import Enum
import structlog

logger = structlog.get_logger()

class PatternType(Enum):
    DIRECT_CLAIM = "direct_claim"
    ASSIGNMENT_REQUEST = "assignment_request"
    QUESTION = "question"
    PROGRESS_UPDATE = "progress_update"

class ClaimPatternMatcher:
    """
    Multi-level pattern matching with confidence scoring as specified in MD file
    """
    
    def __init__(self):
        # Pattern definitions with exact confidence scores from MD file
        self.patterns = {
            PatternType.DIRECT_CLAIM: {
                "confidence": 95,
                "patterns": [
                    # Most direct claim patterns
                    r"\bi\s+claim\s+(this|it|this\s+issue)\b",
                    r"\bclaiming\s+(this|it|this\s+issue)\b",
                    r"\bi\s+claimed\s+(this|it|this\s+issue)\b",
                    
                    # Strong commitment patterns
                    r"i'?ll\s+(take\s+this|work\s+on\s+this|handle\s+this|do\s+this|fix\s+this)",
                    r"i\s+can\s+(take\s+this|handle\s+this|work\s+on\s+this|fix\s+this)",
                    r"i\s+will\s+(take|work\s+on|handle|fix|do)\s+(this|it)",
                    r"i'm\s+(taking|working\s+on|handling)\s+(this|it)",
                    r"let\s+me\s+(take|handle|work\s+on|fix)\s+(this|it)",
                    r"i\s+got\s+this",
                    r"i'll\s+take\s+it",
                    r"i'm\s+on\s+(this|it)",
                    
                    # Additional strong claim patterns
                    r"\bdibs\s+on\s+(this|it)\b",
                    r"\bmine\b",
                    r"i\s+choose\s+(this|it)",
                    r"i\s+pick\s+(this|it)"
                ]
            },
            PatternType.ASSIGNMENT_REQUEST: {
                "confidence": 90,
                "patterns": [
                    r"(please\s+)?assign\s+(this\s+)?to\s+me",
                    r"can\s+you\s+assign\s+(this\s+)?to\s+me",
                    r"i\s+want\s+to\s+work\s+on\s+(this|it)",
                    r"i'd\s+like\s+to\s+(work\s+on|take)\s+(this|it)",
                    r"can\s+i\s+be\s+assigned\s+(this|to\s+this)",
                    r"assign\s+me\s+(please|to\s+this)",
                    r"i\s+volunteer\s+for\s+(this|it)",
                    r"put\s+me\s+down\s+for\s+(this|it)"
                ]
            },
            PatternType.QUESTION: {
                "confidence": 70,
                "patterns": [
                    # Basic questions
                    r"can\s+i\s+(work\s+on|take|do)\s+(this|it)\s*\?",
                    r"is\s+(this|it)\s+(available|free|open)\s*\?",
                    r"anyone\s+working\s+on\s+(this|it)\s*\?",
                    r"may\s+i\s+(take|work\s+on)\s+(this|it)\s*\?",
                    r"may\s+i\s+(take|work\s+on)\s+this\s+issue\s*\?",
                    r"is\s+(this|it)\s+up\s+for\s+grabs\s*\?",
                    r"can\s+i\s+help\s+with\s+(this|it)\s*\?",
                    r"mind\s+if\s+i\s+(take|work\s+on)\s+(this|it)\s*\?",
                    
                    # Hesitant/complex questions with filler words
                    r"can\s+i\s+(maybe|perhaps|possibly)?\s*(work\s+on|take|do)\s+(this|it|this\s+issue).*\?",
                    r"could\s+i\s+(maybe|perhaps|possibly|potentially)?\s*(work\s+on|take|help\s+with)\s+(this|it|this\s+issue).*\?",
                    r"would\s+it\s+be\s+(ok|okay|alright|fine)\s+if\s+i\s+(work\s+on|take)\s+(this|it).*\?",
                    r"is\s+it\s+(ok|okay|alright|fine)\s+if\s+i\s+(work\s+on|take)\s+(this|it).*\?",
                    r"do\s+you\s+mind\s+if\s+i\s+(work\s+on|take)\s+(this|it).*\?",
                    r"would\s+(anyone|someone)\s+mind\s+if\s+i\s+(work\s+on|take)\s+(this|it).*\?",
                    r"am\s+i\s+allowed\s+to\s+(work\s+on|take)\s+(this|it).*\?",
                    r"can\s+i\s+(maybe|perhaps|possibly).*\s+(work\s+on|take|help\s+with)\s+(this|it).*\?",
                    
                    # Questions with uncertainty markers
                    r".*\b(maybe|perhaps|possibly|potentially)\b.*can\s+i\s+(work\s+on|take)\s+(this|it).*\?",
                    r".*\b(maybe|perhaps|possibly|potentially)\b.*could\s+i\s+(work\s+on|take)\s+(this|it).*\?"
                ]
            },
            PatternType.PROGRESS_UPDATE: {
                "confidence": 0,  # Not for claim detection, but for progress tracking
                "patterns": [
                    r"(i'm\s+working|currently\s+working|i\s+started|i\s+began)\s+on\s+(this|it)",
                    r"made\s+(some\s+)?progress\s+on\s+(this|it)",
                    r"almost\s+(done|finished)\s+with\s+(this|it)",
                    r"(update|status):\s+.*(working|progress|done)",
                    r"will\s+have\s+(this|it)\s+(ready|done|finished)\s+(soon|by)",
                    r"(submitted|created)\s+(a\s+)?(pr|pull\s+request)",
                    r"(opened|created)\s+pull\s+request",
                    r"here's\s+my\s+(pr|pull\s+request)"
                ]
            }
        }
        
    def preprocess_comment(self, comment_text: str) -> str:
        """
        Preprocess comment as specified in MD file:
        - Extract text, remove code/URLs
        - Tokenize & normalize
        """
        if not comment_text:
            return ""
            
        # Remove code blocks
        comment_text = re.sub(r'```.*?```', '', comment_text, flags=re.DOTALL)
        comment_text = re.sub(r'`[^`]*`', '', comment_text)
        
        # Remove URLs
        comment_text = re.sub(r'https?://[^\s]+', '', comment_text)
        
        # Remove mentions and references
        comment_text = re.sub(r'@\w+', '', comment_text)
        comment_text = re.sub(r'#\d+', '', comment_text)
        
        # Normalize whitespace and convert to lowercase
        comment_text = ' '.join(comment_text.lower().split())
        
        return comment_text
    
    def detect_claim_patterns(self, comment_text: str) -> Dict:
        """
        Run detection patterns as specified in MD file flowchart
        Returns pattern matches with scores
        """
        preprocessed = self.preprocess_comment(comment_text)
        detected_patterns = []
        max_confidence = 0
        
        for pattern_type, pattern_data in self.patterns.items():
            confidence = pattern_data["confidence"]
            patterns = pattern_data["patterns"]
            
            for pattern in patterns:
                if re.search(pattern, preprocessed, re.IGNORECASE):
                    detected_patterns.append({
                        "type": pattern_type,
                        "confidence": confidence,
                        "pattern": pattern
                    })
                    max_confidence = max(max_confidence, confidence)
                    break  # Only count first match per pattern type
        
        return {
            "detected_patterns": detected_patterns,
            "max_confidence": max_confidence,
            "preprocessed_text": preprocessed
        }
    
    def analyze_context(self, comment: Dict, issue_data: Dict) -> Dict:
        """
        Context-aware analysis as specified in MD file:
        - Reply to maintainer gets +10% confidence boost
        - User assignment status validation
        """
        context_boost = 0
        context_metadata = {}
        
        # Check if reply to maintainer (+10% boost from MD file)
        if self._is_reply_to_maintainer(comment, issue_data):
            context_boost += 10
            context_metadata["reply_to_maintainer"] = True
            logger.info("Applied +10% boost for reply to maintainer")
        
        # Check user assignment status (boost confidence)
        if self._user_already_assigned(comment, issue_data):
            context_boost += 5
            context_metadata["user_assigned"] = True
            logger.info("Applied +5% boost for already assigned user")
        
        return {
            "context_boost": context_boost,
            "metadata": context_metadata
        }
    
    def _is_reply_to_maintainer(self, comment: Dict, issue_data: Dict) -> bool:
        """Check if comment is a reply to repository maintainer"""
        # Implementation depends on issue_data structure from Ecosyste.ms
        # This is a simplified version
        try:
            issue_author = issue_data.get("author", {}).get("login", "")
            repo_owner = issue_data.get("repository", {}).get("owner", "")
            
            # Consider issue author and repo owner as maintainers
            maintainers = {issue_author.lower(), repo_owner.lower()}
            
            # Check if this comment references a previous comment by maintainer
            # This would require more complex logic in real implementation
            return False  # Simplified for hackathon
        except:
            return False
    
    def _user_already_assigned(self, comment: Dict, issue_data: Dict) -> bool:
        """Check if user is already assigned to this issue"""
        try:
            comment_author = comment.get("user", {}).get("login", "").lower()
            assignees = [a.get("login", "").lower() for a in issue_data.get("assignees", [])]
            return comment_author in assignees
        except:
            return False
    
    def calculate_final_score(
        self, 
        base_confidence: int, 
        context_boost: int, 
        threshold: int = 70
    ) -> Dict:
        """
        Calculate final confidence score with context boost
        Default threshold of 70% to include questions as claims (configurable per repo)
        """
        final_score = min(100, base_confidence + context_boost)
        
        return {
            "base_confidence": base_confidence,
            "context_boost": context_boost,
            "final_score": final_score,
            "passes_threshold": final_score >= threshold,
            "threshold": threshold
        }
    
    def analyze_comment(
        self, 
        comment_text: str, 
        comment_data: Dict = None, 
        issue_data: Dict = None,
        threshold: int = 70
    ) -> Dict:
        """
        Complete comment analysis pipeline as specified in MD file
        """
        # Step 1: Pattern detection
        pattern_result = self.detect_claim_patterns(comment_text)
        
        # Step 2: Context analysis
        context_result = {"context_boost": 0, "metadata": {}}
        if comment_data and issue_data:
            context_result = self.analyze_context(comment_data, issue_data)
        
        # Step 3: Final score calculation
        final_result = self.calculate_final_score(
            pattern_result["max_confidence"],
            context_result["context_boost"],
            threshold
        )
        
        # Check for progress updates
        has_progress_update = any(
            p["type"] == PatternType.PROGRESS_UPDATE 
            for p in pattern_result["detected_patterns"]
        )
        
        # If this is a progress update, don't treat as new claim
        is_claim = final_result["passes_threshold"] and not has_progress_update
        
        # Special case: if we have both progress update and claim patterns,
        # prioritize the progress update (existing work, not new claim)
        if has_progress_update and final_result["passes_threshold"]:
            claim_patterns = [p for p in pattern_result["detected_patterns"] 
                            if p["type"] != PatternType.PROGRESS_UPDATE]
            if claim_patterns:
                # This is likely a progress update, not a new claim
                is_claim = False
        
        return {
            **pattern_result,
            **context_result,
            **final_result,
            "is_claim": is_claim,
            "is_progress_update": has_progress_update,
            "analysis_metadata": {
                "original_text": comment_text,
                "preprocessed_text": pattern_result["preprocessed_text"],
                "context_metadata": context_result["metadata"]
            }
        }

# Global instance
pattern_matcher = ClaimPatternMatcher()