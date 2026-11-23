"""Zero-dependency integrity tests for skill files, progressive disclosure, and Markdown links."""

from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile
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
    ("First-run bootstrap", re.compile(r"first-run\s+bootstrap", re.IGNORECASE)),
    ("claude auth status", re.compile(r"claude\s+auth\s+status")),
    ("codex login status", re.compile(r"codex\s+login\s+status")),
    ("agy auth login", re.compile(r"agy\s+auth\s+login")),
    ("resolve_lanes.py", re.compile(r"resolve_lanes\.py")),
    ("scope_drift", re.compile(r"scope_drift")),
    ("first_pass_ok", re.compile(r"first_pass_ok")),
    ("--unit-size", re.compile(r"--unit-size")),
    ("--record-burn", re.compile(r"--record-burn")),
    ("projected-overflow", re.compile(r"projected-overflow")),
    ("90% move threshold", re.compile(r"90\s*%")),
    ("95% stop threshold", re.compile(r"95\s*%")),
)

LEGACY_WEEKLY_85_RE = re.compile(r"(?:\b85\s*%|%85\b)")


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
                        f"{preset} is missing invariant {label!r}",
                    )

            for rel_doc in (
                "SKILL.md",
                "references/quota-and-failover.md",
                "references/cli-lanes-and-ledger.md",
                "project-profile.example.md",
            ):
                doc_text = (preset_dir / rel_doc).read_text(encoding="utf-8")
                with self.subTest(preset=preset, doc=rel_doc, invariant="no-legacy-85pct"):
                    self.assertIsNone(
                        LEGACY_WEEKLY_85_RE.search(doc_text),
                        f"{preset}/{rel_doc} still contains a legacy 85% threshold reference",
                    )

    def test_example_project_profiles_authorize_valid_lanes(self):
        state_path = REPO_ROOT / "examples" / "provider-state.json"
        now = resolve_lanes.parse_iso_utc("2026-11-21T16:00:00Z")
        role_checks = (
            ("coding", None),
            ("reasoning", None),
            ("accuracy", None),
            ("knowledge", None),
            ("review", "claude"),
            ("review", "openai"),
            ("review", "google"),
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

    def test_claude_plugin_manifests_and_icon(self):
        plugin_dir = REPO_ROOT / ".claude-plugin"
        plugin_path = plugin_dir / "plugin.json"
        marketplace_path = plugin_dir / "marketplace.json"
        icon_path = plugin_dir / "icon.png"

        self.assertTrue(plugin_path.is_file(), f"Missing {plugin_path}")
        self.assertTrue(marketplace_path.is_file(), f"Missing {marketplace_path}")

        plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))

        self.assertIsInstance(plugin, dict)
        self.assertIsInstance(marketplace, dict)

        plugin_name = plugin.get("name")
        plugin_version = plugin.get("version")
        self.assertIsInstance(plugin_name, str)
        self.assertTrue(plugin_name.strip(), "plugin.json name must be non-empty")
        self.assertIsInstance(plugin_version, str)
        self.assertTrue(plugin_version.strip(), "plugin.json version must be non-empty")

        self.assertEqual(
            marketplace.get("name"),
            plugin_name,
            "marketplace.json name must match plugin.json name",
        )
        self.assertEqual(
            marketplace.get("metadata", {}).get("version"),
            plugin_version,
            "marketplace.json metadata.version must match plugin.json version",
        )

        plugins = marketplace.get("plugins")
        self.assertIsInstance(plugins, list)
        self.assertTrue(plugins, "marketplace.json plugins list must not be empty")

        matching_plugins = [p for p in plugins if isinstance(p, dict) and p.get("name") == plugin_name]
        self.assertTrue(
            matching_plugins,
            f"marketplace.json must include a plugin entry named {plugin_name!r}",
        )
        for entry in matching_plugins:
            self.assertEqual(
                entry.get("version"),
                plugin_version,
                "marketplace.json plugin entry version must match plugin.json version",
            )

        for idx, entry in enumerate(plugins):
            with self.subTest(plugin_index=idx, plugin_name=entry.get("name")):
                skills = entry.get("skills")
                self.assertIsInstance(skills, list)
                self.assertTrue(skills, "marketplace.json plugin entry must list at least one skill")
                for rel_skill in skills:
                    self.assertIsInstance(rel_skill, str)
                    resolved = (REPO_ROOT / rel_skill).resolve()
                    self.assertTrue(
                        resolved.is_relative_to(REPO_ROOT),
                        f"Skill path {rel_skill!r} escapes repository root",
                    )
                    self.assertTrue(
                        resolved.is_dir(),
                        f"Skill directory listed in marketplace.json does not exist: {rel_skill}",
                    )
                    self.assertTrue(
                        (resolved / "SKILL.md").is_file(),
                        f"Skill directory listed in marketplace.json is missing SKILL.md: {rel_skill}",
                    )

        self.assertTrue(icon_path.is_file(), f"Missing {icon_path}")
        icon_bytes = icon_path.read_bytes()
        self.assertTrue(
            icon_bytes.startswith(b"\x89PNG\r\n\x1a\n"),
            ".claude-plugin/icon.png must start with valid PNG magic bytes",
        )
        self.assertLess(
            len(icon_bytes),
            2 * 1024 * 1024,
            f".claude-plugin/icon.png is too large ({len(icon_bytes)} bytes, limit 2 MB)",
        )

    def test_install_sh_syntax_flags_and_end_to_end(self):
        install_sh = REPO_ROOT / "install.sh"
        self.assertTrue(install_sh.is_file(), f"Missing {install_sh}")

        syntax = subprocess.run(
            ["sh", "-n", str(install_sh)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            syntax.returncode,
            0,
            f"sh -n install.sh failed: {syntax.stderr}",
        )

        help_res = subprocess.run(
            ["sh", str(install_sh), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(help_res.returncode, 0, f"install.sh --help failed: {help_res.stderr}")
        self.assertIn("Usage:", help_res.stdout)
        self.assertIn("--client", help_res.stdout)
        self.assertIn("--dry-run", help_res.stdout)

        dry_res = subprocess.run(
            ["sh", str(install_sh), "--dry-run"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(dry_res.returncode, 0, f"install.sh --dry-run failed: {dry_res.stderr}")
        self.assertIn("Dry run", dry_res.stdout)
        self.assertIn("sol-orchestration", dry_res.stdout)
        self.assertIn("astra-orchestration", dry_res.stdout)
        self.assertIn("update-orchestration-skills", dry_res.stdout)

        for bad_ref in ("../bad", "main;rm", ""):
            with self.subTest(bad_ref=bad_ref):
                bad_res = subprocess.run(
                    ["sh", str(install_sh), "--ref", bad_ref, "--dry-run"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(
                    bad_res.returncode,
                    0,
                    f"install.sh must reject unsafe --ref {bad_ref!r}",
                )
                self.assertIn("invalid --ref", bad_res.stderr)

        with tempfile.TemporaryDirectory() as tmp_dir:
            target_dir = Path(tmp_dir) / "skills-out"
            e2e = subprocess.run(
                [
                    "sh",
                    str(install_sh),
                    "--source",
                    str(REPO_ROOT),
                    "--client",
                    "antigravity",
                    "--with-provider",
                    "--dir",
                    str(target_dir),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                e2e.returncode,
                0,
                f"install.sh end-to-end install failed: {e2e.stderr}",
            )

            expected_installed = sorted(
                (
                    "neon-orchestration",
                    "update-orchestration-skills",
                    "add-provider-orchestration-skills",
                )
            )
            actual_installed = sorted(p.name for p in target_dir.iterdir() if p.is_dir())
            self.assertEqual(actual_installed, expected_installed)

            for skill in expected_installed:
                self.assertTrue(
                    (target_dir / skill / "SKILL.md").is_file(),
                    f"Installed skill {skill} is missing SKILL.md",
                )

            for rel_ref in REQUIRED_COORDINATOR_REFERENCES:
                self.assertTrue(
                    (target_dir / "neon-orchestration" / rel_ref).is_file(),
                    f"Installed neon-orchestration is missing {rel_ref}",
                )

            self.assertTrue(
                (target_dir / "update-orchestration-skills" / "scripts" / "resolve_lanes.py").is_file(),
                "Installed update-orchestration-skills is missing scripts/resolve_lanes.py",
            )

    def test_install_sh_backs_up_existing_skill_folders(self):
        install_sh = REPO_ROOT / "install.sh"
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "proj" / ".claude" / "skills"
            args = ["sh", str(install_sh), "--preset", "opus", "--dir", str(skills), "--source", str(REPO_ROOT)]
            first = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertNotIn("Backed up", first.stdout)
            planted = skills / "opus-orchestration" / "project-local-notes.md"
            planted.write_text("keep me", encoding="utf-8")

            dry = subprocess.run(args + ["--dry-run"], capture_output=True, text=True)
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertIn("Would back up", dry.stdout)
            self.assertIn("project-local-notes.md", dry.stdout)
            self.assertTrue(planted.is_file(), "--dry-run must not move anything")
            self.assertFalse((Path(tmp) / "proj" / ".claude" / "skill-backups").exists())

            real = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(real.returncode, 0, real.stderr)
            self.assertIn("Backed up", real.stdout)
            self.assertIn("project-local file not in upstream: project-local-notes.md", real.stdout)
            backups = sorted((Path(tmp) / "proj" / ".claude" / "skill-backups").glob("opus-orchestration-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / "project-local-notes.md").read_text(encoding="utf-8"), "keep me")
            self.assertFalse((skills / "opus-orchestration" / "project-local-notes.md").exists())
            self.assertTrue((skills / "opus-orchestration" / "SKILL.md").is_file())
            self.assertFalse(
                any(p.name.startswith("skill-backups") for p in skills.iterdir()),
                "backups must live outside the skills directory",
            )

    def test_docs_simulator_and_demo_gif(self):
        docs_index = REPO_ROOT / "docs" / "index.html"
        self.assertTrue(docs_index.is_file(), f"Missing {docs_index}")
        html = docs_index.read_text(encoding="utf-8")
        self.assertTrue(html.strip(), "docs/index.html must not be empty")
        self.assertIn("<html", html.lower(), "docs/index.html must contain an <html> element")
        self.assertIn('href="icon.png"', html, "docs/index.html must reference canonical icon.png favicon")
        self.assertIn('src="icon.png"', html, "docs/index.html must render canonical icon.png brand logo")

        plugin_icon = REPO_ROOT / ".claude-plugin" / "icon.png"
        docs_icon = REPO_ROOT / "docs" / "icon.png"
        self.assertTrue(docs_icon.is_file(), f"Missing {docs_icon}")
        self.assertEqual(
            docs_icon.read_bytes(),
            plugin_icon.read_bytes(),
            "docs/icon.png must stay byte-identical to .claude-plugin/icon.png",
        )

        demo_gif = REPO_ROOT / "assets" / "demo.gif"
        self.assertTrue(demo_gif.is_file(), f"Missing {demo_gif}")
        gif_bytes = demo_gif.read_bytes()
        self.assertTrue(
            gif_bytes.startswith((b"GIF89a", b"GIF87a")),
            "assets/demo.gif must start with valid GIF magic bytes (GIF89a or GIF87a)",
        )
        self.assertLess(
            len(gif_bytes),
            1024 * 1024,
            f"assets/demo.gif is too large ({len(gif_bytes)} bytes, limit 1 MB)",
        )


if __name__ == "__main__":
    unittest.main()
