# Artificial Analysis skorları (2026-11-19)

Intelligence Index v5.0.1 verileri için kaynak ve atıf [Artificial Analysis](https://artificialanalysis.ai/).

## Ölçek ve sınırlar

[2026-11-15 ölçeği ve profil ağırlıkları](aa-skorlar-2026-11-15.md) korunmuştur. Neon, AutoB (eski en iyi 78, Xhigh 79.3) ve GDP.pdf (eski en iyi 33, High 33.4) tavanlarını geçer. GPT-6.2 Astra, TBS'de (eski en iyi 73, Xhigh 78.6) ve TB4'te (eski en iyi 64, Max ve Xhigh 64.1) eski en iyiyi geçer. Profil puanı 100'ü aşabilir. Ölçek ileride yenilenecektir.

- Neon Low ve Medium için Omniscience doğruluğu ve uydurmama oranı bulunamadığı için Doğruluk profilleri boş bırakıldı. Neon Low için CritPt de doğrulanamadığından Muhakeme profili boş bırakıldı.
- Sol High ve Xhigh süreleri (258 ve 306 sn/görev, `*`) kingy.ai modellemesidir. Doğrudan AA süreleri bulunamadı ve bu süreler doğrulanmadı.
- AA ücretsiz API doğrulaması üç Intelligence Index değerini kapsadı. Neon Low II 44.1, Neon Medium II 54.9 ve GPT-6.2 Sol Xhigh II 55.7. Ham test ve profil tablolarında araştırma raporundaki Neon Medium II 55.0 aynen korunmuştur. Diğer değerler arama özetlerinden derlendi.

## Ham testler · Gemini 4 Neon

Yüzdelik test sütunları ham skoru, Briefcase Elo'yu gösterir. Yaklaşık süreler dakika değerlerinden çevrilmiştir.

| Model (effort) | Şirket / istemci | II | FC2 | TB4 | TBS | CritPt | HLE-D | Omni acc | Uydurmama | Briefcase | AutoB | GDP.pdf | sn/görev | $/görev |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemini 4 Neon (Low) | Google / agy | 44.1 | 26.9 | 32.8 | 27.1 | — | 54.2 | — | — | 1297 | 76.0 | 31.4 | ~222 (3.7 dk) | 0.75 |
| Gemini 4 Neon (Medium) | Google / agy | 55.0 | 36.9 | 54.5 | 54.8 | 61.5 | 63.6 | — | — | 1518 | 77.8 | 32.8 | ~498 (8.3 dk) | 1.90 |
| Gemini 4 Neon (High) | Google / agy | 60.0 | 43.3 | 61.6 | 65.7 | 59.0 | 68.4 | 59.4 | 86.1 | 1632 | **79.2** | **33.4** | ~888 (14.8 dk) | 3.74 |
| Gemini 4 Neon (Xhigh) | Google / agy | 61.4 | 44.4 | 63.6 | 70.0 | 60.5 | 71.3 | 60.5 | 85.6 | 1699 | **79.3** | 28.0 | ~1290 (21.5 dk) | 6.44 |

## Ham testler · GPT-6.2 Astra ve Sol

| Model (effort) | II | FC2 | TB4 | TBS | CritPt | HLE-D | Omni acc | Uydurmama | Briefcase | AutoB | GDP.pdf | sn/görev | $/görev |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
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

## Profil puanları · 2026-11-15 ölçeği

| Model (effort) | II | Kod | Muh. | Doğr. | Bilgi |
|---|---:|---:|---:|---:|---:|
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

## Önceki GPT sürümleriyle fark

| Geçiş (effort) | Δ II | Δ Kod | Δ Muh. | Δ Doğr. | Δ Bilgi |
|---|---:|---:|---:|---:|---:|
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

## Antigravity ve kota

Araştırma raporuna göre **Orchestrator (Neon)** kipinde Neon planlayıcı, Hydrogen yürütücüdür. Başsız çağrı `agy -p "…" --model "Orchestrator (Neon)"` biçimindedir. `--effort` ve `/effort` bu kipe uygulanmaz. Google AI Pro ve Ultra'da hesaplama tabanlı kota 5 saatlik kayan pencere ile haftalık üst sınırı birlikte kullanır. [Google duyurusu](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-neon/)
