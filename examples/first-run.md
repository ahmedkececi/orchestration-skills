# Try Ultimate Orchestration Skills

This walkthrough has two parts. Run the actual measurement helper against an example bundle without signing in, then read a sample handoff at a quota limit. The models, scores and quota readings in this example are fixtures. They do not rank real providers.

## Preview model data offline

With Git and Python 3.9 or newer:

```sh
git clone https://github.com/ahmedkececi/ultimate-orchestration-skills.git
cd ultimate-orchestration-skills
python3 -B skills/update-orchestration-skills/scripts/refresh.py \
  --workspace . --input examples/measurements.json --preview
```

Find **Benchmark coverage by model and effort** in the output. It shows the included scores and the missing results for each variant. This is a local import using sample data. The live refresh skill also supports checking public catalogs, model selection and source verification. [Refresh skill](../skills/update-orchestration-skills/)

| Model | Effort | FrontierCode | Terminal-Bench 4.0 | GDP.pdf |
| --- | --- | ---: | ---: | --- |
| `demo-primary` | `medium` | 72% | 61% | - |
| `demo-backup` | `medium` | 75% | 63% | - |

The command prints Markdown. To inspect a saved copy, redirect the output to a file in a scratch directory you control. The preview does not create a workspace snapshot.

## Follow a quota handoff

**Example task:** Update three files to render timestamps consistently. The project lets two independent model pools see the repository and run the relevant checks. The manager owns the plan and final review. A third authorized model family can independently review the result.

1. **Before the limit:** Worker A owns the first file. The manager records the goal, writable paths, expected behavior and acceptance checks in the checkpoint. Each remaining unit has an owner or is marked pending.
2. **At the configured move threshold:** Suppose Pool A is at 85% usage. The next unit can go to Worker B after checking its data permissions, tools, quality profile and separate quota headroom. In the sample benchmark table above, both coding scores are available on the same test cohort. There is no PDF result to use for decisions about document work.
3. **After the handoff:** Worker B reads the checkpoint, finishes its assigned files and returns the diff and checks it ran. A fresh reviewer from another authorized model family receives the diff and acceptance criteria. The manager uses that evidence to decide whether the task is done.

A checkpoint excerpt might look like this:

```text
Goal: Render UTC timestamps consistently on three report pages.
Accepted decision: Reuse the existing UTC formatter.
Unit 1: Completed by Worker A. Verify its diff during the final check.
Units 2–3: Worker B owns the remaining report pages only.
Quota: Pool A reached its configured move threshold. Pool B has capacity.
Next check: Compare all three pages against the same UTC timestamp fixture.
Independent review: Pending on an authorized third model family.
```

Use the [workflow templates](../skills/sol-orchestration/workflow-templates.md) to write your own brief and handoff. The prespecified quota thresholds and fallback candidates live in the [coordinator presets](../README.md#choose-a-coordinator). The sample describes a decision the coordinator makes using its configured runners and observed quota.

## Türkçe kısa başlangıç

Yukarıdaki [çevrimdışı komutu](#preview-model-data-offline) Git ve Python 3.9+ ile çalıştırabilirsin. İki örnek modelin benchmark tablosunu yazdırır. Skoru olmayan testler `-` görünür. Değerler gösterim amaçlıdır.

[Kota devri örneğinde](#follow-a-quota-handoff) ajan, ilk havuz taşıma eşiğine gelince kalan işi yetkili ikinci havuza verir. Devir kaydı hangi dosyaların kaldığını ve yeni ajanın ilk neyi kontrol edeceğini gösterir.
