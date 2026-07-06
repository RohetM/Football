"""Security validation utilities for input requests.

Contains functions to sanitize strings, enforce maximum sizes, and reject
potential prompt injection and SQL injection patterns.
"""

import re


def sanitize_text(text: str) -> str:
    """Strip HTML tags and trim whitespace from input text.

    Args:
        text: The raw input string.

    Returns:
        str: The sanitized clean text.
    """
    if not text:
        return ""
    # Strip HTML tags
    clean = re.sub(r"<[^>]*>", "", text)
    # Trim leading/trailing whitespace
    return clean.strip()


def validate_input_length(text: str, max_length: int = 500) -> bool:
    """Verify the length of the input text does not exceed the limit.

    Args:
        text: Input string to validate.
        max_length: Maximum allowed length.

    Returns:
        bool: True if length is valid, False otherwise.
    """
    return len(text) <= max_length


def detect_sql_injection(text: str) -> bool:
    """Identify common SQL injection signatures in string.

    Args:
        text: The input text.

    Returns:
        bool: True if SQL injection pattern is detected, False otherwise.
    """
    # Look for common SQL keywords and character sequences
    sql_patterns = [
        r"(?i)\bUNION\b\s+ALL\b\s+SELECT\b",
        r"(?i)\bUNION\b\s+SELECT\b",
        r"(?i)\bSELECT\b.*\bFROM\b",
        r"(?i)\bINSERT\b\s+INTO\b",
        r"(?i)\bDROP\b\s+TABLE\b",
        r"(?i)\bDELETE\b\s+FROM\b",
        r"'\s*OR\s*'\d+'\s*=\s*'\d+",
        r"'\s*OR\s*1\s*=\s*1",
        r"--",
        r"\/\*",
    ]
    for pattern in sql_patterns:
        if re.search(pattern, text):
            return True
    return False


def detect_prompt_injection(text: str) -> bool:
    """Identify signatures of LLM prompt injection attempts.

    Args:
        text: The input text.

    Returns:
        bool: True if prompt injection pattern is detected, False otherwise.
    """
    injection_patterns = [
        r"(?i)\bignore\b.*\bprevious\b.*\binstructions\b",
        r"(?i)\bignore\b.*\babove\b.*\binstructions\b",
        r"(?i)\bsystem\b.*\bprompt\b",
        r"(?i)\byou\b.*\bare\b.*\ban\b.*\bAI\b.*\b(designed|built|acting)\b",
        r"(?i)\bforget\b.*\beverything\b.*\bbefore\b",
        r"(?i)\bdo\b.*\bnot\b.*\b(follow|adhere)\b.*\binstructions\b",
        r"(?i)\bnew\b.*\binstruction\b",
    ]
    for pattern in injection_patterns:
        if re.search(pattern, text):
            return True
    return False


def validate_query(text: str | None, max_length: int = 500) -> tuple[bool, str, str]:
    """Perform comprehensive validation on a user query.

    Args:
        text: Query string.
        max_length: Maximum allowed characters.

    Returns:
        tuple[bool, str, str]: (is_valid, sanitized_text, error_message)
    """
    if not text or not text.strip():
        return False, "", "Query cannot be empty"

    sanitized = sanitize_text(text)

    if not validate_input_length(sanitized, max_length):
        return (
            False,
            sanitized,
            f"Query exceeds maximum length of {max_length} characters",
        )

    if detect_sql_injection(sanitized):
        return False, sanitized, "Query contains forbidden characters or SQL commands"

    if detect_prompt_injection(sanitized):
        return False, sanitized, "Query contains commands to bypass safety guidelines"

    return True, sanitized, ""
