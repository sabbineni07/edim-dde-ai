"""Directory-backed prompt and skill providers (markdown files).

Business purpose:
  Load agent prompts/skills from a content root (typically YAML ``content_dir``)
  without embedding large text in the definition file.

Public API:
  - ``DirectoryContentProvider`` — ``get_prompt`` / ``list_skills``
"""

from __future__ import annotations

from pathlib import Path

from edim_dde_ai.content.protocols import Skill


def _parse_skill_markdown(key: str, text: str) -> Skill:
    """Parse ``skills/{key}.md``: optional ``# Title`` first line, rest is body."""
    lines = text.splitlines()
    title = key
    body_start = 0
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip() or key
        body_start = 1
        if body_start < len(lines) and lines[body_start].strip() == "":
            body_start += 1
    content = "\n".join(lines[body_start:]).strip()
    return Skill(key=key, title=title, content=content)


class DirectoryContentProvider:
    """Load prompts/skills from a content root directory.

    Layout::

        prompts/{chain}.{role}.md   # e.g. chat.system.md
        skills/{key}.md             # optional first line ``# Title``

    If ``agent_id`` is set, ``get_prompt`` / ``list_skills`` only serve that id.

    Args:
        root: Content directory path.
        agent_id: Optional scope; when set, other agent_ids return empty/None.
    """

    def __init__(self, root: str | Path, agent_id: str | None = None) -> None:
        self.root = Path(root)
        self.agent_id = agent_id

    def _prompts_dir(self) -> Path:
        return self.root / "prompts"

    def _skills_dir(self) -> Path:
        return self.root / "skills"

    def get_prompt(self, agent_id: str, chain: str, role: str) -> str | None:
        """Read ``prompts/{chain}.{role}.md`` or return ``None`` if missing/scoped out."""
        if self.agent_id is not None and agent_id != self.agent_id:
            return None
        path = self._prompts_dir() / f"{chain}.{role}.md"
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def list_skills(self, agent_id: str, *, chain: str | None = None) -> list[Skill]:
        """List ``skills/*.md`` (``chain`` reserved; currently unused)."""
        del chain
        if self.agent_id is not None and agent_id != self.agent_id:
            return []
        skills_dir = self._skills_dir()
        if not skills_dir.is_dir():
            return []
        skills: list[Skill] = []
        for path in sorted(skills_dir.glob("*.md")):
            key = path.stem
            text = path.read_text(encoding="utf-8")
            skills.append(_parse_skill_markdown(key, text))
        return skills
