"""Post review comments to GitHub pull requests via the REST API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nopush.providers.base import ProviderError

if TYPE_CHECKING:
    from nopush.review.models import ReviewResult


class PRCommenter:
    """Posts NoPush review comments to a GitHub pull request.

    Uses the GitHub REST API v3. Requires a personal access token with
    ``repo`` scope.

    .. note::
        This is an optional feature — stub for Phase 1.
    """

    def __init__(self, token: str) -> None:
        if not token:
            msg = (
                "GitHub token is required for PR comments. "
                "Set GITHUB_TOKEN or add github_token to your config."
            )
            raise ProviderError(msg)
        self._token = token

    def post_review(self, pr_url: str, result: ReviewResult) -> None:
        """Post review comments to the specified pull request.

        Parameters
        ----------
        pr_url:
            Full URL of the GitHub pull request.
        result:
            The review result containing comments to post.

        .. note::
            Full implementation coming in Step 8.
        """
        raise NotImplementedError("GitHub PR commenting is not yet implemented (Step 8).")
