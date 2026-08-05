"""Deterministic Message Router for Engineering Collaboration (ACR-007 Phase C2).

Resolves recipient descriptors into target AgentSession IDs.
Supports:
- Specific Session (e.g. "session:sess-backend-001" or "sess-backend-001")
- Role (e.g. "role:backend_developer" or "role:Lead Architect")
- Department (e.g. "dept:engineering" or "department:qa")
- Broadcast (e.g. "broadcast" or "*")
- System (e.g. "system")

Pure deterministic logic. No AI execution, no runtime scheduling, no state mutation.
"""

from __future__ import annotations

from typing import Sequence

from runtime.agent.models import AgentSession
from .models import RecipientType


class MessageRouter:
    """Deterministic routing engine for resolving recipient descriptors into target session IDs."""

    def classify_descriptor(self, descriptor: str) -> RecipientType:
        """Classify a recipient descriptor string into a canonical RecipientType."""
        raw = descriptor.strip().lower()
        if raw in ("broadcast", "*", "all"):
            return RecipientType.BROADCAST
        if raw in ("system", "sys"):
            return RecipientType.SYSTEM
        if raw.startswith("role:"):
            return RecipientType.ROLE
        if raw.startswith("dept:") or raw.startswith("department:"):
            return RecipientType.DEPARTMENT
        if raw.startswith("session:") or raw.startswith("sess-") or raw.startswith("sess_"):
            return RecipientType.SPECIFIC_SESSION
        return RecipientType.SPECIFIC_SESSION

    def resolve_recipients(
        self,
        recipient_descriptors: Sequence[str] | str,
        active_sessions: Sequence[AgentSession] | Sequence[str],
        sender_session_id: str | None = None,
    ) -> list[str]:
        """Resolve recipient descriptors into a sorted, deduplicated list of target AgentSession IDs.

        Parameters
        ----------
        recipient_descriptors:
            Descriptor string (e.g. "role:backend_developer") or list of descriptors.
        active_sessions:
            List of active AgentSession objects or active session ID strings.
        sender_session_id:
            Optional sender session ID to exclude from broadcasts (default: keep sender if explicit).

        Returns
        -------
        list[str]
            Sorted list of resolved target AgentSession IDs.
        """
        if isinstance(recipient_descriptors, str):
            descriptors = [recipient_descriptors]
        else:
            descriptors = list(recipient_descriptors)

        resolved_ids: set[str] = set()

        # Build lookup maps for active sessions if objects are provided
        session_ids: set[str] = set()
        role_map: dict[str, set[str]] = {}
        dept_map: dict[str, set[str]] = {}

        for item in active_sessions:
            if isinstance(item, AgentSession):
                sid = item.session_id
                session_ids.add(sid)
                
                # Map role ID and role title
                role_id = item.role_id.strip().lower()
                role_title = item.role_title.strip().lower()
                role_map.setdefault(role_id, set()).add(sid)
                role_map.setdefault(role_title, set()).add(sid)

                # Map department from metadata if present
                dept = item.metadata.get("department", "").strip().lower()
                if dept:
                    dept_map.setdefault(dept, set()).add(sid)
            else:
                sid = str(item)
                session_ids.add(sid)

        for descriptor in descriptors:
            kind = self.classify_descriptor(descriptor)
            raw = descriptor.strip()

            if kind == RecipientType.BROADCAST:
                # Add all active sessions
                for sid in session_ids:
                    if sender_session_id and len(session_ids) > 1 and sid == sender_session_id:
                        continue
                    resolved_ids.add(sid)

            elif kind == RecipientType.SYSTEM:
                resolved_ids.add("system")

            elif kind == RecipientType.ROLE:
                target_role = raw.split(":", 1)[1].strip().lower()
                if target_role in role_map:
                    resolved_ids.update(role_map[target_role])
                else:
                    # Fuzzy match on role title/id substring
                    for r_key, s_set in role_map.items():
                        if target_role in r_key or r_key in target_role:
                            resolved_ids.update(s_set)

            elif kind == RecipientType.DEPARTMENT:
                target_dept = raw.split(":", 1)[1].strip().lower()
                if target_dept in dept_map:
                    resolved_ids.update(dept_map[target_dept])

            elif kind == RecipientType.SPECIFIC_SESSION:
                target_sid = raw.split(":", 1)[1].strip() if raw.startswith("session:") else raw
                resolved_ids.add(target_sid)

        return sorted(resolved_ids)
