"""
Typed Exceptions Hierarchy
===========================
Domain-specific exceptions for all modules in AutoApply AI.
Enables fine-grained error catching and graceful degradation.
"""


class AutoApplyException(Exception):
    """Base class for all domain exceptions in AutoApply AI."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


# -------------------------------------------------------------
# Resume Parser Exceptions
# -------------------------------------------------------------
class ResumeParseError(AutoApplyException):
    """Raised when resume parsing fails."""
    pass


class EmptyResumeError(ResumeParseError):
    """Raised when an uploaded resume file contains zero readable text."""
    pass


class UnsupportedFormatError(ResumeParseError):
    """Raised when an uploaded file format is not .pdf, .docx, or .txt."""
    pass


class ScannedImageResumeError(ResumeParseError):
    """Raised when a PDF contains only scanned images and no extractable text layer."""
    pass


class NonEnglishResumeError(ResumeParseError):
    """Raised when a resume is predominantly non-English and cannot be parsed."""
    pass


class CorruptResumeError(ResumeParseError):
    """Raised when a file cannot be unpacked or parsed due to corruption."""
    pass


# -------------------------------------------------------------
# Matcher Exceptions
# -------------------------------------------------------------
class MatchingError(AutoApplyException):
    """Raised when scoring or ranking fails."""
    pass


class InvalidEngineError(MatchingError):
    """Raised when an unsupported similarity engine is requested."""
    pass


# -------------------------------------------------------------
# Scraper Exceptions
# -------------------------------------------------------------
class JobScraperError(AutoApplyException):
    """Base exception for job board scraping failures."""
    pass


class RobotsDisallowedError(JobScraperError):
    """Raised when robots.txt or site policy disallows automated scraping."""
    pass


class RateLimitExceededError(JobScraperError):
    """Raised when a remote server returns HTTP 429 or rate limits."""
    pass


class JobBoardBlockedError(JobScraperError):
    """Raised when anti-bot or CAPTCHA blocks scraping."""
    pass


class ScraperParsingError(JobScraperError):
    """Raised when page markup changes and cannot be parsed."""
    pass


# -------------------------------------------------------------
# Browser Automation Exceptions
# -------------------------------------------------------------
class BrowserAutomationError(AutoApplyException):
    """Base exception for browser agent actions."""
    pass


class FormNotFoundError(BrowserAutomationError):
    """Raised when the application form cannot be located on the target page."""
    pass


class FieldMappingError(BrowserAutomationError):
    """Raised when a critical form field cannot be mapped to the profile."""
    pass


class CaptchaDetectedError(BrowserAutomationError):
    """Raised when a CAPTCHA or Cloudflare challenge is encountered."""
    pass


class HumanReviewRequiredError(BrowserAutomationError):
    """Raised when confidence is low or dry run mode mandates human intervention."""
    pass


# -------------------------------------------------------------
# Security & Storage Exceptions
# -------------------------------------------------------------
class SecurityError(AutoApplyException):
    """Base exception for cryptographic and secret handling errors."""
    pass


class MissingSecretKeyError(SecurityError):
    """Raised when the encryption secret key is missing or invalid."""
    pass


class StorageError(AutoApplyException):
    """Raised when database or file storage operations fail."""
    pass


# -------------------------------------------------------------
# Authentication & Authorization Exceptions
# -------------------------------------------------------------
class AuthenticationError(AutoApplyException):
    """Base exception for user authentication failures."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when email or password is incorrect."""
    pass


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT access or refresh token is invalid or expired."""
    pass


class UserAlreadyExistsError(AuthenticationError):
    """Raised when attempting to sign up with an existing email address."""
    pass


class UserNotFoundError(AuthenticationError):
    """Raised when a requested user account does not exist."""
    pass


class UnauthorizedAccessError(AutoApplyException):
    """Raised when a user attempts to access resources belonging to another user."""
    pass
