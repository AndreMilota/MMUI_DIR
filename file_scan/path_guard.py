"""
PathGuard: A class for managing file/directory access permissions based on
disk IDs and path patterns with wildcard support.

Default behavior is to BLOCK everything. You must explicitly allow paths.
"""

import fnmatch
from dataclasses import dataclass, field
from enum import Enum


class Permission(Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass
class PathGuard:
    """
    Guards file/directory access with a whitelist-first approach.

    By default, all paths are BLOCKED. You must explicitly allow paths.
    Rules are evaluated in order, with later rules overriding earlier ones.

    Typical usage:
        1. allow() - open up paths for access
        2. deny() - block specific portions of allowed paths
        3. allow() - re-open specific portions of denied paths (optional)

    Rules are specified by disk_id (e.g., serial number) and path patterns.
    Paths can use forward or back slashes and support wildcards:
        * - matches any characters within a single path segment
        ** - matches any characters across multiple path segments (recursive)

    Example patterns:
        "photos/vacation/*" - all files directly in vacation folder
        "photos/**/*.mp3" - all mp3 files anywhere under photos
        "documents" - the documents directory itself and all contents
    """

    _rules: list[tuple[str, str, Permission]] = field(default_factory=list)

    def _normalize_path(self, path: str) -> str:
        """Normalize path to use forward slashes and remove trailing slashes."""
        return path.replace("\\", "/").rstrip("/")

    def _segment_matches(self, pattern_segment: str, path_segment: str) -> bool:
        """Match a single path segment against a pattern segment using fnmatch."""
        return fnmatch.fnmatch(path_segment, pattern_segment)

    def _path_matches(self, pattern: str, path: str) -> bool:
        """
        Check if a path matches a pattern.

        Handles ** for recursive matching and * for single-segment matching.
        A pattern matches if:
        - It matches the path segment by segment
        - The path is under the pattern (pattern is a parent directory)
        """
        pattern = self._normalize_path(pattern)
        path = self._normalize_path(path)

        pattern_segments = pattern.split("/") if pattern else []
        path_segments = path.split("/") if path else []

        return self._match_segments(pattern_segments, path_segments)

    def _match_segments(self, pattern_segments: list[str], path_segments: list[str]) -> bool:
        """
        Match path segments against pattern segments.
        * matches any characters within a single segment.
        ** matches zero or more complete segments.
        """
        if not pattern_segments:
            # Empty pattern matches empty path, or acts as parent of any path
            return True

        if not path_segments:
            # Path is empty but pattern is not - check if pattern is all **
            return all(seg == "**" for seg in pattern_segments)

        first_pattern = pattern_segments[0]

        if first_pattern == "**":
            # ** can match zero or more segments
            remaining_pattern = pattern_segments[1:]

            # Try matching ** against 0, 1, 2, ... segments
            for i in range(len(path_segments) + 1):
                if self._match_segments(remaining_pattern, path_segments[i:]):
                    return True
            return False

        # Regular segment (may contain * or ?)
        if not path_segments:
            return False

        if self._segment_matches(first_pattern, path_segments[0]):
            return self._match_segments(pattern_segments[1:], path_segments[1:])

        return False

    def allow(self, disk_id: str, path: str) -> None:
        """
        Allow access to a path pattern for a specific disk.

        Args:
            disk_id: Identifier for the disk (e.g., serial number)
            path: Path pattern to allow. Can use / or \\ as separators.
                  Supports * (single segment) and ** (recursive) wildcards.
        """
        normalized = self._normalize_path(path)
        self._rules.append((disk_id, normalized, Permission.ALLOW))

    def deny(self, disk_id: str, path: str) -> None:
        """
        Deny access to a path pattern for a specific disk.

        Use this to block portions of previously allowed paths.

        Args:
            disk_id: Identifier for the disk (e.g., serial number)
            path: Path pattern to deny. Can use / or \\ as separators.
                  Supports * (single segment) and ** (recursive) wildcards.
        """
        normalized = self._normalize_path(path)
        self._rules.append((disk_id, normalized, Permission.DENY))

    def ok(self, disk_id: str, path: str) -> bool:
        """
        Check if access to a path is allowed.

        Rules are evaluated in order. The last matching rule determines access.
        If no rules match, access is DENIED (default closed).

        Returns False if:
        - No rules match the path (default deny)
        - The last matching rule is a deny rule
        - The path contains wildcards and there's ambiguity

        Args:
            disk_id: Identifier for the disk (e.g., serial number)
            path: Path to check. Can use / or \\ as separators.
                  If wildcards are used and any potential match could be
                  denied, returns False (conservative).

        Returns:
            True if access is allowed, False otherwise.
        """
        normalized = self._normalize_path(path)

        # Check if the query path has wildcards - if so, we need to be conservative
        has_wildcards = any(c in normalized for c in "*?[")

        # Find the last matching rule
        last_permission = None

        for rule_disk_id, rule_pattern, permission in self._rules:
            if rule_disk_id != disk_id:
                continue

            if self._path_matches(rule_pattern, normalized):
                last_permission = permission

            # If query has wildcards, check if the pattern could overlap
            if has_wildcards and self._patterns_could_overlap(rule_pattern, normalized):
                # For wildcard queries, if any deny rule could apply, be conservative
                if permission == Permission.DENY:
                    return False

        # Default deny if no rules matched
        if last_permission is None:
            return False

        return last_permission == Permission.ALLOW

    def _patterns_could_overlap(self, pattern1: str, pattern2: str) -> bool:
        """
        Check if two patterns could potentially match the same path.
        This is used for conservative checking when wildcards are involved.
        """
        # Simple heuristic: check if non-wildcard prefixes match
        def get_prefix(p: str) -> str:
            for i, c in enumerate(p):
                if c in "*?[":
                    return p[:i]
            return p

        prefix1 = get_prefix(pattern1)
        prefix2 = get_prefix(pattern2)

        # If one prefix starts with the other, they could overlap
        if prefix1.startswith(prefix2) or prefix2.startswith(prefix1):
            return True

        return False
