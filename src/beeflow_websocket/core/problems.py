"""Problem Details helpers for Beeflow WebSocket communication."""

INVALID_MESSAGE_PROBLEM = "invalid-message"
UNKNOWN_ACTION_PROBLEM = "unknown-action"
DEFAULT_PROBLEM_TYPE = "about:blank"


def build_problem_type(problem_type_base_url: str | None, problem_slug: str) -> str:
    """Return a Problem Details type URI for a configured application problem page."""
    if problem_type_base_url is None:
        return DEFAULT_PROBLEM_TYPE

    normalised_base_url = problem_type_base_url.strip().rstrip("/")
    if normalised_base_url == "":
        return DEFAULT_PROBLEM_TYPE

    return f"{normalised_base_url}/{problem_slug.lstrip('/')}"
