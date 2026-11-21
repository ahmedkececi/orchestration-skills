"""Zero-dependency integrity tests for skill files, progressive disclosure, and Markdown links."""

from pathlib import Path
import re
import sys
import unicodedata
import unittest
from urllib.parse import unquote


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
SCRIPTS_DIR = SKILLS_DIR / "update-orchestration-skills" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import resolve_lanes  # noqa: E402

EXPECTED_SKILLS = (
    "add-provider-orchestration-skills",
    "astra-orchestration",
    "fable-orchestration",
    "neon-orchestration",
    "opus-orchestration",
    "sol-orchestration",
    "update-orchestration-skills",
)

COORDINATOR_PRESETS = (
    "astra-orchestration",
    "sol-orchestration",
    "neon-orchestration",
    "fable-orchestration",
    "opus-orchestration",
)

REQUIRED_COORDINATOR_REFERENCES = (
    "references/delegation-and-verification.md",
    "references/quota-and-failover.md",
    "references/cli-lanes-and-ledger.md",
)

MAX_COORDINATOR_SKILL_LINES = 450
MAX_DESCRIPTION_CHARS = 1024

TOP_LEVEL_DOCS = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "examples" / "first-run.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "CHANGELOG.md",
)

INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\n]+)\)")
FENCE_OPEN_RE = re.compile(r"^\s*(`{3,}|~{3,})")
ATX_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}[ \t]+(.+?)\s*#*\s*$")
MD_INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)\n]+\)")
HTML_TAG_RE = re.compile(r"<[^>]+>")
HTML_ANCHOR_RE = re.compile(r"""<a\b[^>]*\b(?:id|name)=["']([^"']+)["']""", re.IGNORECASE)

V120_INVARIANT_PATTERNS = (
    ("five_hour_pct", re.compile(r"five_hour_pct")),
    ("observed_at", re.compile(r"observed_at")),
    ("BLOCKER", re.compile(r"\bBLOCKER\b")),
    ("Timeout / Hung", re.compile(r"timeout\s*/\s*hung", re.IGNORECASE)),
    ("Compaction", re.compile(r"\bcompaction\b", re.IGNORECASE)),
    ("Test Integrity", re.compile(r"test\s+integrity", re.IGNORECASE)),
    ("External Action", re.compile(r"external\s+action", re.IGNORECASE)),
    ("git push", re.compile(r"git\s+push", re.IGNORECASE)),
    ("resolve_lanes.py", re.compile(r"resolve_lanes\.py")),
    ("scope_drift", re.compile(r"scope_drift")),
    ("first_pass_ok", re.compile(r"first_pass_ok")),
)


def parse_frontmatter(text):
    """Parse simple YAML frontmatter from a Markdown file without third-party dependencies."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("Missing opening YAML frontmatter delimiter '---'")

    end_index = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break
    if end_index is None:
        raise ValueError("Missing closing YAML frontmatter delimiter '---'")

    data = {}
    i = 1
    while i < end_index:
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if ":" not in line:
            raise ValueError(f"Malformed frontmatter line {i + 1}: {line!r}")

        key, raw_val = line.split(":", 1)
        key = key.strip()
        val = raw_val.strip()

        if val in (">", ">-", ">+", "|", "|-", "|+"):
            is_folded = val.startswith(">")
            block_lines = []
            i += 1
            while i < end_index:
                next_line = lines[i]
                if next_line.startswith((" ", "\t")):
                    block_lines.append(next_line.strip())
                    i += 1
                elif not next_line.strip():
                    block_lines.append("")
                    i += 1
                else:
                    break
            while block_lines and block_lines[-1] == "":
                block_lines.pop()
            if is_folded:
                paragraphs = []
                current = []
                for bl in block_lines:
                    if bl == "":
                        if current:
                            paragraphs.append(" ".join(current))
                            current = []
                    else:
                        current.append(bl)
                if current:
                    paragraphs.append(" ".join(current))
                data[key] = "\n\n".join(paragraphs)
            else:
                data[key] = "\n".join(block_lines)
        else:
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1]
            data[key] = val
            i += 1

    return data


def strip_fenced_code_blocks(text):
    """Remove fenced code blocks from Markdown text while keeping other lines intact."""
    out = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    for line in text.splitlines():
        if not in_fence:
            match = FENCE_OPEN_RE.match(line)
            if match:
                token = match.group(1)
                in_fence = True
                fence_char = token[0]
                fence_len = len(token)
                continue
            out.append(line)
        else:
            stripped = line.strip()
            if (
                stripped
                and set(stripped) == {fence_char}
                and len(stripped) >= fence_len
            ):
                in_fence = False
                fence_char = ""
                fence_len = 0
    return "\n".join(out)


def slugify_github_heading(heading_text):
    """Generate a GitHub-Flavored Markdown heading anchor slug (Unicode-aware)."""
    cleaned = MD_INLINE_LINK_RE.sub(r"\1", heading_text)
    cleaned = HTML_TAG_RE.sub("", cleaned)
    cleaned = cleaned.replace("`", "").replace("*", "")
    cleaned = cleaned.strip().lower()

    out = []
    for ch in cleaned:
        if ch == " ":
            out.append("-")
        elif ch in ("-", "_"):
            out.append(ch)
        else:
            cat = unicodedata.category(ch)
            if cat and cat[0] in ("L", "M", "N"):
                out.append(ch)
    return "".join(out)


def extract_markdown_heading_anchors(text):
    """Return the set of valid GitHub heading and explicit HTML anchors in Markdown text."""
    stripped = strip_fenced_code_blocks(text)
    anchors = set()
    counts = {}

    for line in stripped.splitlines():
        for html_match in HTML_ANCHOR_RE.finditer(line):
            anchors.add(html_match.group(1).strip().lower())

        match = ATX_HEADING_RE.match(line)
        if not match:
            continue
        base = slugify_github_heading(match.group(1))
        if not base:
            continue
        seen = counts.get(base, 0)
        anchor = base if seen == 0 else f"{base}-{seen}"
        counts[base] = seen + 1
        anchors.add(anchor)

    return anchors


def extract_markdown_link_targets(text):
    """Return raw link targets from Markdown outside fenced and inline code."""
    cleaned = INLINE_CODE_RE.sub("", strip_fenced_code_blocks(text))
    targets = []
    for match in MD_LINK_RE.finditer(cleaned):
        raw = match.group(1).strip()
        if raw.startswith("<") and ">" in raw:
            raw = raw[1 : raw.index(">")]
        elif " " in raw:
            raw = raw.split()[0]
        if raw:
            targets.append(raw)
    return targets


class SkillIntegrityTests(unittest.TestCase):
    def test_all_skills_have_valid_frontmatter(self):
        discovered = sorted(p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md"))
        self.assertEqual(discovered, sorted(EXPECTED_SKILLS))

        for skill_name in discovered:
            skill_path = SKILLS_DIR / skill_name / "SKILL.md"
            with self.subTest(skill=skill_name):
                text = skill_path.read_text(encoding="utf-8")
                meta = parse_frontmatter(text)

                self.assertEqual(meta.get("name"), skill_name)
                description = meta.get("description", "").strip()
                self.assertTrue(description, "Frontmatter description must be non-empty")
                self.assertLessEqual(
                    len(description),
                    MAX_DESCRIPTION_CHARS,
                    f"Description length {len(description)} exceeds {MAX_DESCRIPTION_CHARS}",
                )
                self.assertRegex(
                    description,
                    r"\bUse\b",
                    "Frontmatter description must include a 'Use' trigger phrase",
                )

    def test_coordinator_presets_progressive_disclosure(self):
        for preset in COORDINATOR_PRESETS:
            preset_dir = SKILLS_DIR / preset
            skill_path = preset_dir / "SKILL.md"
            with self.subTest(preset=preset):
                self.assertTrue(skill_path.is_file(), f"Missing {skill_path}")
                text = skill_path.read_text(encoding="utf-8")
                line_count = len(text.splitlines())
                self.assertLessEqual(
                    line_count,
                    MAX_COORDINATOR_SKILL_LINES,
                    f"{preset}/SKILL.md has {line_count} lines (limit {MAX_COORDINATOR_SKILL_LINES})",
                )

                linked_targets = set(
                    unquote(t.split("#", 1)[0].split("?", 1)[0])
                    for t in extract_markdown_link_targets(text)
                )

                for rel_ref in REQUIRED_COORDINATOR_REFERENCES:
                    ref_path = preset_dir / rel_ref
                    self.assertTrue(
                        ref_path.is_file(),
                        f"Missing required reference file: {ref_path.relative_to(REPO_ROOT)}",
                    )
                    self.assertTrue(
                        ref_path.read_text(encoding="utf-8").strip(),
                        f"Reference file is empty: {ref_path.relative_to(REPO_ROOT)}",
                    )
                    self.assertIn(
                        rel_ref,
                        linked_targets,
                        f"{preset}/SKILL.md must link to {rel_ref}",
                    )

    def test_all_local_relative_markdown_links_resolve(self):
        md_files = sorted(SKILLS_DIR.rglob("*.md")) + list(TOP_LEVEL_DOCS)
        anchor_cache = {}

        def get_anchors(path):
            if path not in anchor_cache:
                anchor_cache[path] = extract_markdown_heading_anchors(
                    path.read_text(encoding="utf-8")
                )
            return anchor_cache[path]

        for md_path in md_files:
            self.assertTrue(md_path.is_file(), f"Expected Markdown file missing: {md_path}")
            text = md_path.read_text(encoding="utf-8")
            rel_md = md_path.relative_to(REPO_ROOT)

            for raw_target in extract_markdown_link_targets(text):
                if raw_target.startswith(("http://", "https://", "mailto:")):
                    continue

                path_and_query, _, raw_fragment = raw_target.partition("#")
                path_part = unquote(path_and_query.split("?", 1)[0])
                fragment = unquote(raw_fragment).strip().lower()

                with self.subTest(source=str(rel_md), target=raw_target):
                    if not path_part:
                        if not fragment:
                            continue
                        resolved = md_path.resolve()
                    else:
                        resolved = (md_path.parent / path_part).resolve()
                        self.assertTrue(
                            resolved.is_relative_to(REPO_ROOT),
                            f"Link {raw_target!r} in {rel_md} escapes repository root",
                        )
                        self.assertTrue(
                            resolved.exists(),
                            f"Broken relative link {raw_target!r} in {rel_md} -> {resolved}",
                        )

                    if fragment:
                        self.assertTrue(
                            resolved.is_file() and resolved.suffix.lower() == ".md",
                            f"Fragment link {raw_target!r} in {rel_md} does not target a Markdown file",
                        )
                        anchors = get_anchors(resolved)
                        self.assertIn(
                            fragment,
                            anchors,
                            f"Broken heading anchor #{fragment} in {rel_md} -> {resolved.relative_to(REPO_ROOT)} "
                            f"(available: {sorted(anchors)})",
                        )

    def test_workflow_templates_are_byte_identical(self):
        reference_preset = COORDINATOR_PRESETS[0]
        reference_path = SKILLS_DIR / reference_preset / "workflow-templates.md"
        self.assertTrue(reference_path.is_file(), f"Missing {reference_path}")
        reference_bytes = reference_path.read_bytes()
        self.assertTrue(reference_bytes, "workflow-templates.md must not be empty")

        for preset in COORDINATOR_PRESETS[1:]:
            template_path = SKILLS_DIR / preset / "workflow-templates.md"
            with self.subTest(preset=preset):
                self.assertTrue(template_path.is_file(), f"Missing {template_path}")
                self.assertEqual(
                    template_path.read_bytes(),
                    reference_bytes,
                    f"{preset}/workflow-templates.md differs from {reference_preset}/workflow-templates.md",
                )

    def test_coordinator_presets_v120_invariants(self):
        for preset in COORDINATOR_PRESETS:
            preset_dir = SKILLS_DIR / preset
            combined_parts = [(preset_dir / "SKILL.md").read_text(encoding="utf-8")]
            for rel_ref in REQUIRED_COORDINATOR_REFERENCES:
                combined_parts.append((preset_dir / rel_ref).read_text(encoding="utf-8"))
            combined_text = "\n".join(combined_parts)

            for label, pattern in V120_INVARIANT_PATTERNS:
                with self.subTest(preset=preset, invariant=label):
                    self.assertIsNotNone(
                        pattern.search(combined_text),
                        f"{preset} is missing v1.2.0 invariant {label!r}",
                    )

    def test_example_project_profiles_authorize_valid_lanes(self):
        state_path = REPO_ROOT / "examples" / "provider-state.json"
        now = resolve_lanes.parse_iso_utc("2026-11-21T16:00:00Z")
        role_checks = (
            ("coding", None),
            ("reasoning", None),
            ("review", "claude"),
            ("review", "openai"),
        )
        for preset in COORDINATOR_PRESETS:
            profile_path = SKILLS_DIR / preset / "project-profile.example.md"
            with self.subTest(preset=preset, check="schema"):
                self.assertTrue(profile_path.is_file(), f"Missing {profile_path}")
                lanes = resolve_lanes.parse_authorized_lanes(
                    profile_path.read_text(encoding="utf-8")
                )
                self.assertIsInstance(lanes, dict)
                self.assertTrue(lanes, f"{preset}/project-profile.example.md must authorize at least one lane")

            for role, author_family in role_checks:
                with self.subTest(preset=preset, role=role, author_family=author_family):
                    report = resolve_lanes.resolve_from_paths(
                        workspace=REPO_ROOT,
                        profile_path=profile_path,
                        state_path=state_path,
                        role=role,
                        author_family=author_family,
                        now=now,
                    )
                    self.assertFalse(report["advisory"])
                    self.assertEqual(report["warnings"], [], f"Unexpected warnings for {preset}/{role}: {report['warnings']}")
                    self.assertIsNotNone(report["recommended"], f"No recommended lane for {preset}/{role}")
                    if role == "review" and author_family is not None:
                        self.assertFalse(
                            report["recommended"]["same_family"],
                            f"{preset} review for author={author_family} should prefer a cross-family reviewer",
                        )


if __name__ == "__main__":
    unittest.main()
