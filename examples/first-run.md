# Try Ultimate Orchestration Skills

This walkthrough has three parts. Run the measurement helper against an example bundle, resolve authorized lanes deterministically from a sample quota state without signing in, then read a sample handoff at a quota limit. The models, scores and quota readings in this example are fixtures. They do not rank real providers.

## Preview model data offline

With Git and Python 3.9 or newer:

```sh
git clone https://github.com/ahmedkececi/ultimate-orchestration-skills.git
cd ultimate-orchestration-skills
python3 -B skills/update-orchestration-skills/scripts/refresh.py \
  --workspace . --input examples/measurements.json --preview \
  | awk '/^## Live workspace measurements/{show=1} /^<!-- observations:start -->/{exit} show'
```

The full `--preview` output prints the bundled historical snapshot first (lines 1–192), the live workspace tables next, and the serialized JSON observations at the bottom. The `awk` filter above isolates **Live workspace measurements**; omit the pipe to inspect the entire document or redirect it to a file in a scratch directory you control. The preview never modifies your workspace.

Under **Benchmark coverage by model and effort**, you will see the exact coverage matrix rendered by the helper (models sorted alphabetically, cohort in parentheses, and `-` for every unverified benchmark column):

| Model | Effort | Checked on | FC2 | TB4 | TBS | CritPt | HLE-D | Omni acc | Non-hallucination | Briefcase | AutoB | GDP.pdf |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `demo-backup` | medium | - | 75% (`demo-fixture`) | 63% (`demo-fixture`) | - | - | - | - | - | - | - | - |
| `demo-primary` | medium | - | 72% (`demo-fixture`) | 61% (`demo-fixture`) | - | - | - | - | - | - | - | - |

This is a local import using sample data. The live refresh skill also supports checking public catalogs, model selection and source verification. [Refresh skill](../skills/update-orchestration-skills/)

## Resolve lanes deterministically offline

Use `resolve_lanes.py` with the Astra sample profile to rank permitted workers
against the bundled benchmark snapshot and a fixed quota reading. The
`--now` value makes the fixture's age reproducible.

```sh
python3 -B skills/update-orchestration-skills/scripts/resolve_lanes.py \
  --workspace . --profile skills/astra-orchestration/project-profile.example.md \
  --role coding --state examples/provider-state.json --now 2026-11-21T16:00:00Z

python3 -B skills/update-orchestration-skills/scripts/resolve_lanes.py \
  --workspace . --profile skills/astra-orchestration/project-profile.example.md \
  --role review --author-family openai \
  --state examples/provider-state.json --now 2026-11-21T16:00:00Z
```

What the output demonstrates:

- **Coding:** Astra manages this example project. The profile's authorization
  block allows the specified Opus, Sonnet and Sol efforts as workers (with
  `gpt-6.2-sol` `xhigh` reserved for `--role reasoning`). For `--role coding`,
  `gpt-6.2-sol` (`high`, score `82`) and `claude-opus-5-5` (`high`, score `81`)
  are within the ±3-point equivalence band (`equivalent`), and because Codex is
  at `87%` weekly usage (above the `85%` move threshold -> `deprioritized`),
  `resolve_lanes.py` recommends healthy `claude-opus-5-5 (high)` (`42%`
  headroom) first.
- **Cross-family review:** Opus is authorized for review outside the
  author's OpenAI family. The authorized Sol reviewer is flagged
  `same-family`.
- In a real project, save the authorization block in
  `.orchestration/project-profile.md` and omit `--profile`. Use
  `--restricted-data` to require a lane approved for that data and
  `--providers` to narrow the pool list. Without an authorization block
  the ranking is advisory and the recommendation is empty.

## Follow a quota handoff

**Example task:** Update three files to render timestamps consistently. The project lets two independent model pools see the repository and run the relevant checks. The manager owns the plan and final review. A third authorized model family can independently review the result.

1. **Before the limit:** Worker A owns the first file. The manager records the goal, writable paths, expected behavior and acceptance checks in `.orchestration/orchestration-checkpoint.md`. Each remaining unit has an owner or is marked pending.
2. **At the configured move threshold:** Suppose Pool A's weekly pool reaches 85% usage (the default weekly move threshold; five-hour windows move later at 90% because they reset within hours). The next unit moves to Worker B after checking its data permissions, tools, quality profile and separate quota headroom. In the sample benchmark table above, both coding scores (`FC2` and `TB4`) are available on the same `demo-fixture` cohort, while `GDP.pdf` is `-` (unknown — not usable for document-work decisions).
3. **After the handoff:** Worker B reads `.orchestration/orchestration-checkpoint.md`, finishes its assigned files and returns the 4-line contract (`STATUS` / `RESULT` / `EVIDENCE` / `NOT DONE`). A fresh reviewer from another authorized model family receives the diff and acceptance criteria. The manager uses that evidence to decide whether the task is done.

A checkpoint excerpt in `.orchestration/orchestration-checkpoint.md` follows the [workflow templates](../skills/sol-orchestration/workflow-templates.md#handoff-and-routing-record) format:

```markdown
Goal and current baseline: Render UTC timestamps consistently across 3 report pages on branch `fix/utc-timestamps` (commit `a1b2c3d`).
Accepted decisions and unresolved decisions: Accepted — reuse `src/utils/formatUtc.ts`. Unresolved — none.

| Unit | Owner or lane | Depends on | State | Path or evidence | Next check |
| --- | --- | --- | --- | --- | --- |
| Unit 1 (summary page) | Worker A (Pool A) | — | done | `src/pages/summary.ts`; `npm test -- summary` passed | Verify diff in final check |
| Units 2–3 (detail & export pages) | Worker B (Pool B) | Unit 1 | in_progress | `src/pages/detail.ts`, `src/pages/export.ts` | Compare all 3 pages against UTC fixture |

| Pool | Current status | Reset time with timezone | Fallback |
| --- | --- | --- | --- |
| Pool A | weekly 85% (at move threshold) | 2026-11-24 00:00 UTC | Pool B |
| Pool B | weekly 28% / 5h 15% (healthy) | 2026-11-24 00:00 UTC | Local review |

Manager verification already run: Confirmed Unit 1 diff stays inside `src/pages/summary.ts` and fixture test passes.
Independent review status: Pending on an authorized third model family after Units 2–3 return.
Exact next action and completion condition: Wait for Worker B's 4-line return (`STATUS`/`RESULT`/`EVIDENCE`/`NOT DONE`), run cross-family review across all 3 pages, then accept.
```

Use the [workflow templates](../skills/sol-orchestration/workflow-templates.md) to write your own brief and handoff. The prespecified quota thresholds and fallback candidates live in the [coordinator presets](../README.md#choose-a-coordinator). The sample describes a decision the coordinator makes using its configured runners and observed quota.

## Türkçe kısa başlangıç

Yukarıdaki [çevrimdışı komutu](#preview-model-data-offline) Git ve Python 3.9+ ile çalıştırabilirsin. `awk` filtresi yalnızca canlı çalışma alanı tablolarını gösterir; boru (`|`) kısmını kaldırırsan üstte tarihsel arşiv, altta JSON gözlemleriyle birlikte tam çıktıyı görebilirsin. Doğrulanmamış testler `-` görünür; değerler gösterim amaçlıdır.

[Kota devri örneğinde](#follow-a-quota-handoff) ilk havuz haftalık taşıma eşiğine (%85) ulaşınca kalan iş yetkili ikinci havuza aktarılır. [Çevrimdışı hat çözümleme](#resolve-lanes-deterministically-offline) bölümündeki `resolve_lanes.py` komutları bu eşik ve çapraz aile inceleme sıralamasını örnek `provider-state.json` üzerinde doğrudan gösterir: `--role coding` için `gpt-6.2-sol` (`high`, skor `82`) ile `claude-opus-5-5` (`high`, skor `81`) ±3 puanlık eşdeğerlik bandında (`equivalent`) yer alır ve Codex haftalık `%87` kullanımla (`%85` taşıma eşiğinin üzerinde -> `deprioritized`) olduğu için `resolve_lanes.py` ilk sırada sağlıklı `claude-opus-5-5 (high)` (`%42` kalan kota) hattını önerir. `.orchestration/orchestration-checkpoint.md` içindeki devir kaydı hangi dosyaların kaldığını, havuzların durumunu ve yeni ajanın ilk neyi kontrol edeceğini gösterir.
