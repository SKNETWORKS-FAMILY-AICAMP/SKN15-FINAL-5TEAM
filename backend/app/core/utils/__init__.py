"""
Core Utilities
공통 유틸리티 모듈
"""
from .fuzzy_matcher import FuzzyMatcher, FuzzyMatchResult
from .spellcheck import SpellChecker, SpellCheckResult
from .image_manager import ImageManager
from .email_sender import EmailSender, EmailConfig

__all__ = [
    "FuzzyMatcher",
    "FuzzyMatchResult",
    "SpellChecker",
    "SpellCheckResult",
    "ImageManager",
    "EmailSender",
    "EmailConfig",
]
