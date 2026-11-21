# Model measurements

This file brings the historical benchmark scores and workload profile averages together. The bundled snapshot covers November 15 and 19, 2026 and is attributed to [Artificial Analysis](https://artificialanalysis.ai/leaderboards/models) for Intelligence Index v5.0.1 and its component tests. It provides historical context. Use a fresh, comparable cohort for current routing.

## Historical profile rubric

The archive scaled each component against a fixed November 15 reference, then took a weighted mean. Briefcase Elo used a 900-point offset. A later model may exceed an old reference. Input modality, provider access and subscription state are separate eligibility checks.

| Profile | Components and weights |
| --- | --- |
| Coding | FrontierCode 2.0 (0.4), Terminal-Bench 4.0 (0.4), AutomationBench (0.2) |
| Reasoning | CritPt v2 Hard (0.35), HLE-Diamond (0.35), Terminal-Bench-Science (0.3) |
| Accuracy | Omniscience accuracy (0.4), non-hallucination rate (0.6) |
| Knowledge work | AA-Briefcase (0.5), GDP.pdf (0.25), AutomationBench (0.25) |

Seconds per task include end-to-end benchmark time. USD per task applies to the measured API workload and does not describe subscription burn. A dash means the archive has no measurement. An asterisk denotes an estimated task time.

## Historical scores · November 15, 2026

The table contains Intelligence Index (II), profile scores, raw test percentages, Briefcase Elo and task time and price.

| Model (effort) | Provider / client | II | Coding | Reasoning | Accuracy | Knowledge work | FC2 | TB4 | TBS | CritPt | HLE-D | Omni acc | Non-hallucination | Briefcase | AutoB | GDP.pdf | s/task | USD/task |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Fable 5.2 (Max) | Anthropic / claude | 64.6 | 97 | 100 | 66 | 91 | 49 | 60 | 73 | 77 | 80 | 79 | 41 | 1785 | 76 | 24 | 2659 | 26.54 |
| Fable 5.2 (Xhigh) | Anthropic / claude | 62.2 | 97 | 94 | 64 | 86 | 48 | 62 | 68 | 74 | 76 | 78 | 40 | 1737 | 74 | 21 | 1627 | 14.83 |
| Fable 5.2 (High) | Anthropic / claude | 61.8 | 96 | 94 | 65 | 82 | 49 | 60 | 70 | 73 | 74 | 77 | 42 | 1677 | 71 | 22 | 952 | 9.08 |
| Opus 5.5 (Max) | Anthropic / claude+agy | 59.1 | 93 | 85 | 64 | 92 | 46 | 60 | 59 | 68 | 68 | 66 | 50 | 1801 | 70 | 26 | 1514 | 10.04 |
| Opus 5.5 (Xhigh) | Anthropic / claude+agy | 57.4 | 90 | 84 | 55 | 88 | 44 | 60 | 62 | 68 | 64 | 66 | 35 | 1761 | 65 | 27 | 932 | 6.05 |
| GPT-6 Astra (Max) | OpenAI / codex | 56.9 | 89 | 86 | 63 | 82 | 42 | 59 | 63 | 71 | 64 | 62 | 50 | 1569 | 68 | 31 | 1368 | 6.24 |
| Fable 5.2 (Medium) | Anthropic / claude | 56.4 | 86 | 82 | 65 | 80 | 41 | 55 | 60 | 62 | 66 | 77 | 42 | 1622 | 69 | 24 | 447 | 3.80 |
| GPT-6 Astra (Xhigh) | OpenAI / codex | 55.3 | 89 | 82 | 66 | 81 | 41 | 60 | 55 | 71 | 62 | 61 | 55 | 1543 | 67 | 32 | 698 | 3.66 |
| GPT-6 Astra (High) | OpenAI / codex | 54.8 | 84 | 83 | 67 | 78 | 40 | 54 | 60 | 72 | 59 | 61 | 57 | 1503 | 67 | 31 | 564 | 3.24 |
| GPT-6.1 Sol (Max) | OpenAI / codex | 54.6 | 85 | 81 | 61 | 80 | 41 | 56 | 58 | 70 | 59 | 62 | 48 | 1555 | 65 | 31 | 1396 | 1.27 |
| Sonnet 5.5 (Max) | Anthropic / claude+agy | 54.5 | 92 | 72 | 62 | 93 | 42 | 64 | 53 | 59 | 53 | 51 | 57 | 1816 | 72 | 26 | 2015 | 10.02 |
| Gemini 4 Hydrogen (Xhigh) | Google / agy | 53.9 | 85 | 76 | 83 | 82 | 39 | 54 | 50 | 66 | 59 | 50 | 92 | 1568 | 76 | 28 | 880 | 3.16 |
| GPT-6.1 Sol (Xhigh) | OpenAI / codex | 52.5 | 83 | 77 | 63 | 79 | 39 | 54 | 50 | 70 | 56 | 61 | 52 | 1504 | 67 | 32 | 619 | 0.76 |
| Opus 5.5 (High) | Anthropic / claude+agy | 51.8 | 81 | 72 | 55 | 85 | 36 | 57 | 49 | 60 | 56 | 65 | 36 | 1682 | 63 | 29 | 566 | 3.46 |
| GPT-6 Astra (Medium) | OpenAI / codex | 51.6 | 78 | 78 | 65 | 75 | 37 | 49 | 53 | 72 | 53 | 60 | 55 | 1462 | 65 | 30 | 449 | 2.73 |
| GPT-6.1 Terra (Max) | OpenAI / codex | 51.3 | 85 | 75 | 65 | 69 | 42 | 56 | 58 | 68 | 47 | 48 | 65 | 1401 | 60 | 29 | 859 | 0.96 |
| Gemini 4 Hydrogen (High) | Google / agy | 50.8 | 83 | 69 | 82 | 79 | 36 | 54 | 41 | 62 | 55 | 48 | 91 | 1497 | 74 | 30 | 500 | 1.87 |
| Gemini 4 Argon (High) | Google / agy | 50.4 | 77 | 70 | 84 | 74 | 26 | 57 | 53 | 53 | 57 | 48 | 96 | 1485 | 78 | 22 | 1779 | 4.97 |
| GPT-6.1 Sol (High) | OpenAI / codex | 50.3 | 79 | 73 | 62 | 76 | 37 | 52 | 46 | 69 | 52 | 60 | 51 | 1469 | 64 | 32 | 470 | 0.59 |
| Sonnet 5.5 (Xhigh) | Anthropic / claude+agy | 49.9 | 82 | 67 | 50 | 86 | 36 | 57 | 52 | 57 | 44 | 51 | 38 | 1740 | 66 | 25 | 861 | 4.09 |
| Opus 5.5 (Medium) | Anthropic / claude+agy | 48.2 | 76 | 65 | 53 | 78 | 33 | 53 | 43 | 54 | 51 | 64 | 33 | 1617 | 61 | 26 | 414 | 2.45 |
| Gemini 4 Argon (Medium) | Google / agy | 47.6 | 75 | 63 | 78 | 75 | 25 | 55 | 49 | 54 | 43 | 49 | 85 | 1467 | 76 | 26 | 1802 | 4.31 |
| GPT-6.1 Sol (Medium) | OpenAI / codex | 46.3 | 73 | 66 | 63 | 68 | 33 | 48 | 37 | 67 | 46 | 60 | 52 | 1361 | 63 | 30 | 274 | 0.36 |
| GPT-6.1 Terra (Xhigh) | OpenAI / codex | 45.3 | 75 | 63 | 64 | 63 | 37 | 46 | 42 | 61 | 42 | 48 | 63 | 1334 | 60 | 27 | 390 | 0.40 |
| GPT-6 Astra (Low) | OpenAI / codex | 43.3 | 63 | 64 | 65 | 62 | 26 | 42 | 37 | 63 | 45 | 59 | 56 | 1256 | 59 | 30 | 225 | 1.42 |
| GPT-6.1 Terra (High) | OpenAI / codex | 42.4 | 72 | 57 | 63 | 60 | 37 | 42 | 33 | 62 | 35 | 47 | 63 | 1265 | 58 | 28 | 258 | 0.26 |
| Sonnet 5.5 (High) | Anthropic / claude+agy | 41.5 | 64 | 52 | 48 | 78 | 26 | 44 | 34 | 52 | 34 | 50 | 36 | 1634 | 59 | 25 | 405 | 1.64 |
| Gemini 4 Hydrogen (Medium) | Google / agy | 41.2 | 63 | 55 | 79 | 70 | 32 | 29 | 15 | 61 | 48 | 48 | 88 | 1296 | 72 | 33 | 227 | 0.80 |
| GPT-6.1 Terra (Medium) | OpenAI / codex | 38.2 | 63 | 50 | 62 | 56 | 35 | 32 | 25 | 56 | 31 | 47 | 60 | 1191 | 58 | 28 | 172 | 0.17 |
| Haiku 5.5 (Max) | Anthropic / claude | 36.5 | 58 | 41 | 59 | 64 | 35 | 33 | 20 | 44 | 30 | 35 | 66 | 1573 | 35 | 21 | 889 | 0.41 |
| GPT-6.1 Sol (Low) | OpenAI / codex | 34.8 | 49 | 50 | 61 | 49 | 20 | 31 | 11 | 63 | 38 | 59 | 50 | 1115 | 53 | 27 | 121 | 0.16 |
| Opus 5.5 (Low) | Anthropic / claude+agy | 34.8 | 46 | 45 | 53 | 57 | 16 | 31 | 24 | 36 | 42 | 63 | 34 | 1278 | 53 | 26 | 182 | 0.98 |
| Haiku 5.5 (Xhigh) | Anthropic / claude | 34.6 | 52 | 42 | 55 | 59 | 30 | 29 | 18 | 48 | 29 | 34 | 61 | 1523 | 36 | 18 | 589 | 0.25 |
| DeepSeek V4.1 Flash 1017 (Max) | DeepSeek | 32.6 | 62 | 28 | 43 | 71 | 28 | 34 | 13 | 25 | 25 | 40 | 36 | 1570 | 67 | 17 | 832 | 0.60 |
| GLM-5.3 (Max) | Zhipu | 31.7 | 60 | 27 | 55 | 61 | 22 | 42 | 10 | 34 | 18 | 32 | 61 | 1501 | 62 | 11 | 1500 | 5.01 |
| Gemini 3.8 Flash (High) | Google / agy | 30.8 | 43 | 40 | 54 | 52 | 19 | 20 | 10 | 47 | 33 | 51 | 45 | 1204 | 60 | 21 | 876 | 7.77 |
| Sonnet 5.5 (Medium) | Anthropic / claude+agy | 30.8 | 42 | 32 | 54 | 62 | 11 | 30 | 16 | 34 | 24 | 46 | 50 | 1437 | 55 | 20 | 234 | 0.78 |
| Gemini 3.8 Flash (Medium) | Google / agy | 30.1 | 42 | 38 | 55 | 52 | 16 | 20 | 10 | 45 | 29 | 50 | 49 | 1183 | 61 | 23 | 745 | 6.26 |
| Haiku 5.5 (High) | Anthropic / claude | 29.9 | 41 | 35 | 54 | 53 | 23 | 22 | 10 | 45 | 24 | 32 | 61 | 1441 | 34 | 17 | 392 | 0.16 |
| DeepSeek V4.1 Flash 1017 (High) | DeepSeek | 28.6 | 49 | 26 | 44 | 61 | 17 | 29 | 10 | 28 | 21 | 39 | 39 | 1416 | 68 | 14 | 653 | 0.46 |
| Qwen3.8-Flash-Next | Alibaba | 28.6 | 52 | 21 | 45 | 67 | 27 | 25 | 7 | 25 | 16 | 24 | 53 | 1572 | 56 | 16 | 2027 | 0.57 |
| GPT-6 Luna (Max) | OpenAI / codex | 27.9 | 42 | 33 | 33 | 58 | 25 | 13 | 9 | 43 | 22 | 40 | 21 | 1337 | 53 | 23 | 730 | 0.15 |
| Gemini 4 Hydrogen (Low) | Google / agy | 26.9 | 27 | 37 | 74 | 44 | 9 | 7 | 2 | 48 | 32 | 46 | 81 | 947 | 61 | 28 | 84 | 0.29 |
| Sonnet 5.5 (Low) | Anthropic / claude+agy | 25.6 | 32 | 25 | 56 | 48 | 7 | 21 | 10 | 26 | 21 | 46 | 52 | 1268 | 49 | 16 | 155 | 0.51 |
| Haiku 5.5 (Medium) | Anthropic / claude | 24.6 | 30 | 24 | 53 | 46 | 16 | 15 | 7 | 31 | 17 | 32 | 60 | 1366 | 29 | 15 | 242 | 0.09 |
| GPT-6 Luna (Xhigh) | OpenAI / codex | 23.5 | 32 | 27 | 30 | 48 | 18 | 8 | 5 | 37 | 19 | 39 | 16 | 1235 | 48 | 19 | 447 | 0.10 |
| GPT-6 Luna (High) | OpenAI / codex | 21.4 | 30 | 22 | 29 | 45 | 19 | 5 | 3 | 31 | 16 | 39 | 15 | 1186 | 48 | 18 | 348 | 0.07 |
| GPT-6 Luna (Medium) | OpenAI / codex | 18.5 | 22 | 20 | 29 | 34 | 13 | 3 | 1 | 28 | 15 | 39 | 15 | 1096 | 40 | 14 | 215 | 0.04 |

## Historical scores · November 19, 2026

### Gemini 4 Neon raw tests

| Model (effort) | Provider / client | II | FC2 | TB4 | TBS | CritPt | HLE-D | Omni acc | Non-hallucination | Briefcase | AutoB | GDP.pdf | s/task | USD/task |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Gemini 4 Neon (Low) | Google / agy | 44.1 | 26.9 | 32.8 | 27.1 | — | 54.2 | — | — | 1297 | 76.0 | 31.4 | ~222 (3.7 min) | 0.75 |
| Gemini 4 Neon (Medium) | Google / agy | 55.0 | 36.9 | 54.5 | 54.8 | 61.5 | 63.6 | — | — | 1518 | 77.8 | 32.8 | ~498 (8.3 min) | 1.90 |
| Gemini 4 Neon (High) | Google / agy | 60.0 | 43.3 | 61.6 | 65.7 | 59.0 | 68.4 | 59.4 | 86.1 | 1632 | **79.2** | **33.4** | ~888 (14.8 min) | 3.74 |
| Gemini 4 Neon (Xhigh) | Google / agy | 61.4 | 44.4 | 63.6 | 70.0 | 60.5 | 71.3 | 60.5 | 85.6 | 1699 | **79.3** | 28.0 | ~1290 (21.5 min) | 6.44 |

### GPT-6.2 Astra and Sol raw tests

| Model (effort) | II | FC2 | TB4 | TBS | CritPt | HLE-D | Omni acc | Non-hallucination | Briefcase | AutoB | GDP.pdf | s/task | USD/task |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GPT-6.2 Astra (Low) | 45.7 | 32.7 | 51.0 | 51.0 | 61.0 | 47.7 | 60.6 | 44.2 | 1039 | 68.6 | 28.0 | 108–114 | 0.66 |
| GPT-6.2 Astra (Medium) | 57.0 | 46.6 | 58.6 | 74.8 | 67.5 | 56.0 | 64.2 | 45.9 | 1408 | 72.8 | 28.4 | 264 | 1.62 |
| GPT-6.2 Astra (High) | 60.1 | 47.1 | 60.1 | 75.2 | 71.5 | 65.9 | 66.3 | 41.9 | 1570 | 76.0 | 28.6 | 348–366 | 2.07 |
| GPT-6.2 Astra (Xhigh) | 61.6 | 49.0 | 64.1 | 78.6 | 70.5 | 67.3 | 67.2 | 42.3 | 1594 | 76.1 | 28.0 | 438–450 | 2.52 |
| GPT-6.2 Astra (Max) | 62.1 | 45.4 | 64.1 | 78.1 | 71.5 | 72.2 | 68.6 | 40.9 | 1643 | 77.2 | 29.8 | 834 | 4.00 |
| GPT-6.2 Sol (Low) | 40.6 | 31.4 | 37.9 | 37.1 | 58.0 | 34.5 | 54.6 | 34.2 | 1230 | 63.2 | 28.6 | 90–96 | 0.18 |
| GPT-6.2 Sol (Medium) | 52.7 | 41.4 | 56.1 | 60.5 | 64.0 | 50.7 | 59.2 | 38.9 | 1495 | 70.3 | 29.2 | 186 | 0.41 |
| GPT-6.2 Sol (High) | 54.9 | 40.2 | 58.6 | 67.6 | 61.5 | 58.3 | 61.4 | 40.0 | 1541 | 69.9 | 28.8 | 258* | 0.56 |
| GPT-6.2 Sol (Xhigh) | 55.7 | 42.8 | 56.1 | 66.7 | 62.5 | 61.8 | 60.7 | 43.8 | 1580 | 70.6 | 28.4 | 306* | 0.65 |
| GPT-6.2 Sol (Max) | 57.3 | 44.4 | 60.1 | 67.6 | 62.5 | 64.0 | 61.6 | 44.6 | 1612 | 71.3 | 30.0 | 522 | 1.01 |

### Task profiles on the November 15 reference

| Model (effort) | II | Coding | Reasoning | Accuracy | Knowledge work |
| --- | ---: | ---: | ---: | ---: | ---: |
| Gemini 4 Neon (Low) | 44.1 | 62 | — | — | 70 |
| Gemini 4 Neon (Medium) | 55.0 | 84 | 78 | — | 84 |
| Gemini 4 Neon (High) | 60.0 | 94 | 84 | 84 | 91 |
| Gemini 4 Neon (Xhigh) | 61.4 | 96 | 87 | 84 | 90 |
| GPT-6.2 Astra (Low) | 45.7 | 76 | 70 | 58 | 51 |
| GPT-6.2 Astra (Medium) | 57.0 | 93 | 86 | 61 | 73 |
| GPT-6.2 Astra (High) | 60.1 | 95 | 92 | 60 | 83 |
| GPT-6.2 Astra (Xhigh) | 61.6 | 100 | 94 | 60 | 83 |
| GPT-6.2 Astra (Max) | 62.1 | 97 | 96 | 60 | 88 |
| GPT-6.2 Sol (Low) | 40.6 | 66 | 57 | 49 | 60 |
| GPT-6.2 Sol (Medium) | 52.7 | 87 | 76 | 54 | 77 |
| GPT-6.2 Sol (High) | 54.9 | 87 | 81 | 56 | 79 |
| GPT-6.2 Sol (Xhigh) | 55.7 | 88 | 83 | 58 | 81 |
| GPT-6.2 Sol (Max) | 57.3 | 92 | 84 | 59 | 84 |

### Change relative to earlier GPT variants

| Transition (effort) | Δ II | Δ Coding | Δ Reasoning | Δ Accuracy | Δ Knowledge work |
| --- | ---: | ---: | ---: | ---: | ---: |
| GPT-6 Astra → 6.2 Astra (Max) | +5.2 | +8 | +10 | −3 | +6 |
| GPT-6 Astra → 6.2 Astra (Xhigh) | +6.3 | +11 | +12 | −6 | +2 |
| GPT-6 Astra → 6.2 Astra (High) | +5.3 | +11 | +9 | −7 | +5 |
| GPT-6 Astra → 6.2 Astra (Medium) | +5.4 | +15 | +8 | −4 | −2 |
| GPT-6 Astra → 6.2 Astra (Low) | +2.4 | +13 | +6 | −7 | −11 |
| GPT-6.1 Sol → 6.2 Sol (Max) | +2.7 | +7 | +3 | −2 | +4 |
| GPT-6.1 Sol → 6.2 Sol (Xhigh) | +3.2 | +5 | +6 | −5 | +2 |
| GPT-6.1 Sol → 6.2 Sol (High) | +4.6 | +8 | +8 | −6 | +3 |
| GPT-6.1 Sol → 6.2 Sol (Medium) | +6.4 | +14 | +10 | −9 | +9 |
| GPT-6.1 Sol → 6.2 Sol (Low) | +5.8 | +17 | +7 | −12 | +11 |

## Historical multi-source profile averages · November 19, 2026

Each cell shows mean, number of entries, range and change from the AA value. The archived methodology normalized external results against a matching reference model, then averaged available values. It excluded overlapping tests and some vendor results. Some effort labels were assigned by the historical method when a source did not state the effort. Treat those comparisons as provisional. Refreshes keep unreported effort separate.

The historical source set includes [Terminal-Bench](https://www.tbench.ai/), [LiveBench](https://livebench.ai/), [Arena](https://arena.ai/), [Vals AI](https://www.vals.ai/), [ARC Prize](https://arcprize.org/leaderboard), [MathArena](https://matharena.ai/), [SimpleQA Verified](https://www.kaggle.com/benchmarks/deepmind/simpleqa-verified), [FACTS](https://www.kaggle.com/benchmarks/google/facts) and [OpenLM](https://openlm.ai/). Some archived entries were sourced through secondary compilations. Look up the exact primary result and effort before treating an archived comparison as current.

The Fable entries describe Fable only. This snapshot has no independently measured Mythos row.

| Model / effort | Coding | Reasoning | Accuracy | Knowledge work |
| --- | ---: | ---: | ---: | ---: |
| opus-5.5/high | 81.00 (n=3, 81.00–81.00, 0.00) | 72.00 (n=4, 72.00–72.00, 0.00) | 55.00 (n=4, 55.00–55.00, 0.00) | 85.00 (n=5, 85.00–85.00, 0.00) |
| opus-5.5/medium | 76.00 (n=1, 76.00–76.00, 0.00, AA only) | 65.00 (n=1, 65.00–65.00, 0.00, AA only) | 53.00 (n=1, 53.00–53.00, 0.00, AA only) | 78.00 (n=1, 78.00–78.00, 0.00, AA only) |
| sonnet-5.5/high | 72.89 (n=3, 64.00–82.88, +8.89) | 61.77 (n=2, 52.00–71.53, +9.77) | 46.17 (n=3, 35.42–55.09, −1.83) | 77.79 (n=4, 62.98–85.86, −0.21) |
| haiku-5.5/high | 57.37 (n=2, 41.00–73.75, +16.37) | 49.67 (n=2, 35.00–64.35, +14.67) | 52.12 (n=2, 50.24–54.00, −1.88) | 53.00 (n=1, 53.00–53.00, 0.00, AA only) |
| gpt-6.2-astra/high | 95.00 (n=1, 95.00–95.00, 0.00, AA only) | 92.00 (n=1, 92.00–92.00, 0.00, AA only) | 60.00 (n=1, 60.00–60.00, 0.00, AA only) | 83.00 (n=1, 83.00–83.00, 0.00, AA only) |
| gpt-6.2-astra/medium | 89.23 (n=2, 85.46–93.00, −3.77) | 78.77 (n=2, 71.53–86.00, −7.23) | 61.00 (n=1, 61.00–61.00, 0.00, AA only) | 82.61 (n=3, 73.00–89.02, +9.61) |
| gpt-6.2-sol/high | 82.42 (n=2, 77.84–87.00, −4.58) | 75.88 (n=2, 70.75–81.00, −5.12) | 56.00 (n=1, 56.00–56.00, 0.00, AA only) | 81.65 (n=3, 79.00–85.85, +2.65) |
| gpt-6.2-sol/medium | 87.00 (n=1, 87.00–87.00, 0.00, AA only) | 76.00 (n=1, 76.00–76.00, 0.00, AA only) | 54.00 (n=1, 54.00–54.00, 0.00, AA only) | 77.00 (n=1, 77.00–77.00, 0.00, AA only) |
| neon/high | 88.53 (n=3, 84.06–94.00, −5.47) | 84.00 (n=1, 84.00–84.00, 0.00, AA only) | 84.00 (n=1, 84.00–84.00, 0.00, AA only) | 91.95 (n=4, 85.88–97.39, +0.95) |
| neon/medium | 84.00 (n=1, 84.00–84.00, 0.00, AA only) | 78.00 (n=1, 78.00–78.00, 0.00, AA only) | — (n=0) | 84.00 (n=1, 84.00–84.00, 0.00, AA only) |
| hydrogen/high | 78.57 (n=3, 73.00–83.00, −4.43) | 69.09 (n=2, 69.00–69.19, +0.09) | 82.00 (n=1, 82.00–82.00, 0.00, AA only) | 81.04 (n=4, 77.17–88.07, +2.04) |
| hydrogen/medium | 63.00 (n=1, 63.00–63.00, 0.00, AA only) | 55.00 (n=1, 55.00–55.00, 0.00, AA only) | 79.00 (n=1, 79.00–79.00, 0.00, AA only) | 70.00 (n=1, 70.00–70.00, 0.00, AA only) |
| argon/medium | 79.05 (n=3, 75.00–82.45, +4.05) | 69.24 (n=3, 63.00–74.26, +6.24) | 71.64 (n=3, 67.65–78.00, −6.36) | 82.59 (n=2, 75.00–90.19, +7.59) |
| fable-5.2/medium | 85.06 (n=2, 84.12–86.00, −0.94) | 77.19 (n=2, 72.39–82.00, −4.81) | 65.00 (n=1, 65.00–65.00, 0.00, AA only) | 84.35 (n=3, 80.00–86.63, +4.35) |
| gpt-6.1-terra/medium | 72.98 (n=2, 63.00–82.95, +9.98) | 59.63 (n=2, 50.00–69.27, +9.63) | 61.55 (n=4, 43.65–74.21, −0.45) | 56.00 (n=1, 56.00–56.00, 0.00, AA only) |
| gpt-6-luna/high | 30.00 (n=1, 30.00–30.00, 0.00, AA only) | 22.00 (n=1, 22.00–22.00, 0.00, AA only) | 41.20 (n=2, 29.00–53.41, +12.20) | 45.00 (n=1, 45.00–45.00, 0.00, AA only) |
| deepseek-flash/max | 58.21 (n=2, 54.41–62.00, −3.79) | 28.00 (n=1, 28.00–28.00, 0.00, AA only) | 37.69 (n=2, 32.38–43.00, −5.31) | 71.00 (n=1, 71.00–71.00, 0.00, AA only) |

## Historical routing reference

This is the compact reference behind the original failover ladders. It mixes
the archived multi-source profile averages (rounded) with matching snapshots
for rows available from a single source. Estimated times have an asterisk.
This table records the original routing baseline. Fresh comparisons should
use matching model variants, effort, task profiles and benchmark cohorts.

| Model (effort) | Provider / client | Index | Coding | Reasoning | Accuracy | Knowledge work | s/task |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Fable 5.2 `medium` | Anthropic / Claude | 56.4 | 85 | 77 | 65 | 84 | 447 |
| Opus 5.5 `medium` | Anthropic / Claude | 48.2 | 76 | 65 | 53 | 78 | 414 |
| Opus 5.5 `high` | Anthropic / Claude | 51.8 | 81 | 72 | 55 | 85 | 566 |
| Sonnet 5.5 `high` | Anthropic / Claude | 41.5 | 73 | 62 | 46 | 78 | 405 |
| Haiku 5.5 `high` | Anthropic / Claude | 29.9 | 57 | 50 | 52 | 53 | 392 |
| gpt-6.2-astra `high` | OpenAI / Codex | 60.1 | 95 | 92 | 60 | 83 | ~357 |
| gpt-6.2-astra `medium` | OpenAI / Codex | 57.0 | 89 | 79 | 61 | 83 | 264 |
| gpt-6.2-sol `xhigh` | OpenAI / Codex | 55.7 | 88 | 83 | 58 | 81 | 306* |
| gpt-6.2-sol `high` | OpenAI / Codex | 54.9 | 82 | 76 | 56 | 82 | 258* |
| gpt-6.2-sol `medium` | OpenAI / Codex | 52.7 | 87 | 76 | 54 | 77 | 186 |
| gpt-6.1-terra `medium` | OpenAI / Codex | 38.2 | 73 | 60 | 62 | 56 | 172 |
| gpt-6-luna `high` | OpenAI / Codex | 21.4 | 30 | 22 | 41 | 45 | 348 |
| gemini-4-hydrogen `high` | Google / agy | 50.8 | 79 | 69 | 82 | 81 | 500 |
| gemini-4-hydrogen `medium` | Google / agy | 41.2 | 63 | 55 | 79 | 70 | 227 |
| gemini-4-neon `high` | Google / agy | 60.0 | 89 | 84 | 84 | 92 | ~888 |
| gemini-4-neon `medium` | Google / agy | 55.0 | 84 | 78 | – | 84 | ~498 |
| gemini-4-neon `xhigh` | Google / agy | 61.4 | 96 | 87 | 84 | 90 | ~1290 |
| gemini-4-argon `medium` | Google / agy | 47.6 | 79 | 69 | 72 | 83 | 1802 |
| gemini-3.8-flash `high` | Google / agy | 30.8 | 43 | 40 | 54 | 52 | 876 |
| deepseek-flash (V4.1 Flash, highest effort; scored as "1017") | DeepSeek | 32.6 | 58 | 28 | 38 | 71 | 832 |
