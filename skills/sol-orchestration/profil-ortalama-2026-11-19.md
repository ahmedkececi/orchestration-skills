# A6 Çok kaynaklı profil ortalamaları · 2026-11-19

## Yöntem

1. İki AA anlık görüntüsündeki profil puanları ve iki araştırma raporunun AA dışı ölçümleri kullanıldı. Boş ölçümler boş bırakıldı. [Artificial Analysis](https://artificialanalysis.ai/)
2. Satıcı değerlendirmeleri ve AA ile örtüşen testler dışlandı. Terminal-Bench 4.1 ayrı sürüm olarak dahil edildi.
3. Açık effort kendi satırına eşlendi. Belirtilmemiş effort, modelin varsayılan şeridine eşlendi. Hesap seçili model ve effort satırlarını kapsıyor.
4. Düşük oranlar 100 − x, Elo değerleri Elo − 900 ile dönüştürüldü. Kaynak puanı, çapanın aynı profildeki AA puanı × dönüştürülmüş değer / dönüştürülmüş çapa değeri. Opus 5.5 öncelikli. Birden fazla kullanılabilir Opus effort’u varsa varsayılan effort, ardından kaynak sırası kullanıldı. Yedek sıra hydrogen/high, gpt-6.2-sol/high, sonnet-5.5/high.
5. Her profilde mevcut AA ve AA dışı puanların eşit ağırlıklı ortalaması alındı. Hücrelerde n, minimum–maksimum ve ortalama eksi AA puanı verildi. Yalnız AA puanı olan hücreler işaretlendi.
6. Tablolar ve sayımlar Node betiğinden üretildi. Sıralama yuvarlanmamış değerlerle ve her iki puanı bulunan satırlarla yapıldı. Eşit puanlar aynı sırayı paylaşıyor.

## Kullanılan kaynaklar

| Kaynak | Test | Profil | Tür | Çapa | Ölçülen modeller | Girdi | Ortalamaya giren | Kaynak URL’si ve varsa dışlama nedeni |
|---|---|---|---|---|---|---:|---:|---|
| Terminal-Bench | Terminal-Bench 4.1 | Kod | Bağımsız | opus-5.5/max | fable-5.2, opus-5.5, sonnet-5.5, haiku-5.5, gpt-6.2-astra, gpt-6.2-sol, gpt-6.1-terra, hydrogen, argon, deepseek-flash | 10 | 2 | [Kaynak](https://www.tbench.ai/) |
| LiveBench 2.0 | LiveBench 2.0 Coding Suite | Kod | Bağımsız | opus-5.5/high | fable-5.2, opus-5.5, sonnet-5.5, haiku-5.5, gpt-6.2-astra, gpt-6.2-sol, gpt-6.1-terra, hydrogen, argon | 9 | 8 | [Kaynak](https://livebench.ai/) |
| Arena AI | Code Arena: WebDev Leaderboard | Kod | Bağımsız | opus-5.5/max | fable-5.2, opus-5.5, sonnet-5.5, gpt-6.2-astra, gpt-6.2-sol, neon | 6 | 1 | [Kaynak](https://arena.ai/) |
| Vals AI | Vibe Code Bench v1.1 | Kod | Bağımsız | opus-5.5/high | fable-5.2, opus-5.5, sonnet-5.5, neon, argon | 5 | 5 | [Kaynak](https://www.vals.ai/) |
| LiveBench 2.0 | LiveBench 2.0 Reasoning Suite | Muhakeme | Bağımsız | opus-5.5/high | fable-5.2, opus-5.5, sonnet-5.5, haiku-5.5, gpt-6.2-astra, gpt-6.2-sol, gpt-6.1-terra, hydrogen, argon | 9 | 8 | [Kaynak](https://livebench.ai/) |
| ARC Prize | ARC-AGI-2 (Semi-Private Evaluation) | Muhakeme | Bağımsız | opus-5.5/high | fable-5.2, opus-5.5, sonnet-5.5, haiku-5.5, gpt-6.2-astra, argon | 6 | 3 | [Kaynak](https://arcprize.org/leaderboard) |
| MathArena | MathArena Overall Expected Performance (AIME/HMMT ve yarışma matematiği) | Muhakeme | Bağımsız | opus-5.5/high | fable-5.2, opus-5.5, gpt-6.2-astra, gpt-6.2-sol | 4 | 1 | [Kaynak](https://matharena.ai/) |
| Google DeepMind / Kaggle (cleus.ai, aiiq.org) | SimpleQA Verified (1.000 soruluk araçsız kısa olgusal doğruluk testi) | Doğruluk | Bağımsız | opus-5.5/high | opus-5.5, sonnet-5.5, gpt-6.1-terra, argon, deepseek-flash | 5 | 4 | [Kaynak](https://www.kaggle.com/benchmarks/deepmind/simpleqa-verified) |
| Google DeepMind / Kaggle (benchlm.ai, aiiq.org, aib.vote) | FACTS Grounding v2 (Kaggle benchmark v2, task revision 4) | Doğruluk | Bağımsız | opus-5.5/high | opus-5.5, sonnet-5.5, haiku-5.5, gpt-6.1-terra, argon | 5 | 5 | [Kaynak](https://www.kaggle.com/benchmarks/google/facts) |
| Google DeepMind / Kaggle (benchleader.com) | FACTS Parametric (FACTS Benchmark Suite alt tablosu) | Doğruluk | Bağımsız | opus-5.5/high | opus-5.5, gpt-6.1-terra, gpt-6-luna, argon | 4 | 4 | [Kaynak](https://www.kaggle.com/benchmarks/google/facts) |
| Arena.ai | Arena.ai Agent Arena · Work Index | Bilgi işi | Bağımsız | opus-5.5/high | fable-5.2, opus-5.5, sonnet-5.5, gpt-6.2-astra, gpt-6.2-sol, neon, hydrogen, argon | 9 | 3 | [Kaynak](https://arena.ai) |
| Vals.ai | Vals Index v2.2 (Finans, Hukuk, Vergi ve Kodlama bileşik GSYİH-ağırlıklı ajan endeksi) | Bilgi işi | Bağımsız | opus-5.5/high | fable-5.2, opus-5.5, sonnet-5.5, gpt-6.2-astra, gpt-6.2-sol, neon, argon | 7 | 5 | [Kaynak](https://vals.ai) |
| LiveBench 2.0 | LiveBench 2.0 · Data Analysis alt paketi | Bilgi işi | Bağımsız | opus-5.5/high | fable-5.2, opus-5.5, sonnet-5.5, gpt-6.2-astra, gpt-6.2-sol, hydrogen, argon | 7 | 6 | [Kaynak](https://livebench.ai) |
| Arena.ai | Arena.ai Agent Arena · Task Outcome Index | Bilgi işi | Bağımsız | opus-5.5/max | fable-5.2, opus-5.5, gpt-6.2-astra, gpt-6.2-sol, neon, hydrogen, argon | 7 | 2 | [Kaynak](https://arena.ai) |
| OpenLM.ai | OpenLM.ai Chatbot Arena · Overall Text Elo | Bilgi işi | Bağımsız | opus-5.5/high | fable-5.2, opus-5.5, sonnet-5.5, gpt-6.2-astra | 4 | 4 | [Kaynak](https://openlm.ai) |

## Dışlanan kaynaklar

| Kaynak | Test | Profil | Tür | Çapa | Ölçülen modeller | Girdi | Ortalamaya giren | Kaynak URL’si ve varsa dışlama nedeni |
|---|---|---|---|---|---|---:|---:|---|
| Humanity's Last Exam | HLE-Diamond (1.000 soruluk seçkin alt küme, dış araçsız) | Muhakeme | Bağımsız | — | fable-5.2, opus-5.5, sonnet-5.5, gpt-6.2-astra, gpt-6.2-sol, argon | 6 | 0 | Aynı test AA profilinde yer alıyor. Çift sayımı önlemek için dışlandı. [Kaynak](https://lastexam.ai/) |
| Epoch AI | GPQA Diamond | Muhakeme | Bağımsız | — | fable-5.2, sonnet-5.5, gpt-6.2-astra, argon | 4 | 0 | Belirlenen çapa sırasındaki hiçbir satırın kullanılabilir ölçümü yok. [Kaynak](https://epoch.ai/datahub/benchmarks/gpqa-diamond) |
| OSWorld (ahmetbalaman.com, layer3labs.io, eesel.ai, scaler.com) | OSWorld-2.1 (Offline subset, partial credit) | Bilgi işi | Satıcı | — | fable-5.2, opus-5.5, sonnet-5.5, hydrogen, argon | 5 | 0 | Satıcı değerlendirmelerinden derlenmiştir. [Kaynak](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEr2mRhWWQQadCwZ8bYtIq_71SYUm-dOFY2hqoSN2-qhQg_K8fVECLyjWBoeLahJoQKgGwZpce1vsROhAb63LCZ2emQStyk_GVDUy5RPvDifhJUgF2J7Yog43wYSVL3FO_F-I1PigjIfe3ahOETjPYS41Sc1icjDS5CDApkPaLC0fD-qWnrSE96HB0FQFRus9xjQ_xGuCJN1fY=) |

GDPval-AA ve AA-Omniscience de çift sayım kuralı kapsamındadır. Araştırma raporlarının ölçüm tablolarında bu iki teste ait satır bulunmuyor.

## Ölçüm sayımı

- AA dışı girdi · 18 kaynak ve 112 değer. 61 değer ortalamaya girdi, 15 değer kaynak düzeyinde dışlandı, 36 değer seçili effort satırlarının dışında kaldı.
- AA ve AA dışı toplam · 67 AA puanı + 61 AA dışı puan = ana tablodaki n değerlerinin toplamı 128.

## Profil puanları

Her hücre ortalama (n, minimum–maksimum, AA farkı) biçimindedir.

| Model / effort | Kod | Muhakeme | Doğruluk | Bilgi işi |
|---|---:|---:|---:|---:|
| opus-5.5/high | 81,00 (n=3, 81,00–81,00, 0,00) | 72,00 (n=4, 72,00–72,00, 0,00) | 55,00 (n=4, 55,00–55,00, 0,00) | 85,00 (n=5, 85,00–85,00, 0,00) |
| opus-5.5/medium | 76,00 (n=1, 76,00–76,00, 0,00, yalnız AA) | 65,00 (n=1, 65,00–65,00, 0,00, yalnız AA) | 53,00 (n=1, 53,00–53,00, 0,00, yalnız AA) | 78,00 (n=1, 78,00–78,00, 0,00, yalnız AA) |
| sonnet-5.5/high | 72,89 (n=3, 64,00–82,88, +8,89) | 61,77 (n=2, 52,00–71,53, +9,77) | 46,17 (n=3, 35,42–55,09, −1,83) | 77,79 (n=4, 62,98–85,86, −0,21) |
| haiku-5.5/high | 57,37 (n=2, 41,00–73,75, +16,37) | 49,67 (n=2, 35,00–64,35, +14,67) | 52,12 (n=2, 50,24–54,00, −1,88) | 53,00 (n=1, 53,00–53,00, 0,00, yalnız AA) |
| gpt-6.2-astra/high | 95,00 (n=1, 95,00–95,00, 0,00, yalnız AA) | 92,00 (n=1, 92,00–92,00, 0,00, yalnız AA) | 60,00 (n=1, 60,00–60,00, 0,00, yalnız AA) | 83,00 (n=1, 83,00–83,00, 0,00, yalnız AA) |
| gpt-6.2-astra/medium | 89,23 (n=2, 85,46–93,00, −3,77) | 78,77 (n=2, 71,53–86,00, −7,23) | 61,00 (n=1, 61,00–61,00, 0,00, yalnız AA) | 82,61 (n=3, 73,00–89,02, +9,61) |
| gpt-6.2-sol/high | 82,42 (n=2, 77,84–87,00, −4,58) | 75,88 (n=2, 70,75–81,00, −5,12) | 56,00 (n=1, 56,00–56,00, 0,00, yalnız AA) | 81,65 (n=3, 79,00–85,85, +2,65) |
| gpt-6.2-sol/medium | 87,00 (n=1, 87,00–87,00, 0,00, yalnız AA) | 76,00 (n=1, 76,00–76,00, 0,00, yalnız AA) | 54,00 (n=1, 54,00–54,00, 0,00, yalnız AA) | 77,00 (n=1, 77,00–77,00, 0,00, yalnız AA) |
| neon/high | 88,53 (n=3, 84,06–94,00, −5,47) | 84,00 (n=1, 84,00–84,00, 0,00, yalnız AA) | 84,00 (n=1, 84,00–84,00, 0,00, yalnız AA) | 91,95 (n=4, 85,88–97,39, +0,95) |
| neon/medium | 84,00 (n=1, 84,00–84,00, 0,00, yalnız AA) | 78,00 (n=1, 78,00–78,00, 0,00, yalnız AA) | — (n=0) | 84,00 (n=1, 84,00–84,00, 0,00, yalnız AA) |
| hydrogen/high | 78,57 (n=3, 73,00–83,00, −4,43) | 69,09 (n=2, 69,00–69,19, +0,09) | 82,00 (n=1, 82,00–82,00, 0,00, yalnız AA) | 81,04 (n=4, 77,17–88,07, +2,04) |
| hydrogen/medium | 63,00 (n=1, 63,00–63,00, 0,00, yalnız AA) | 55,00 (n=1, 55,00–55,00, 0,00, yalnız AA) | 79,00 (n=1, 79,00–79,00, 0,00, yalnız AA) | 70,00 (n=1, 70,00–70,00, 0,00, yalnız AA) |
| argon/medium | 79,05 (n=3, 75,00–82,45, +4,05) | 69,24 (n=3, 63,00–74,26, +6,24) | 71,64 (n=3, 67,65–78,00, −6,36) | 82,59 (n=2, 75,00–90,19, +7,59) |
| fable-5.2/medium | 85,06 (n=2, 84,12–86,00, −0,94) | 77,19 (n=2, 72,39–82,00, −4,81) | 65,00 (n=1, 65,00–65,00, 0,00, yalnız AA) | 84,35 (n=3, 80,00–86,63, +4,35) |
| gpt-6.1-terra/medium | 72,98 (n=2, 63,00–82,95, +9,98) | 59,63 (n=2, 50,00–69,27, +9,63) | 61,55 (n=4, 43,65–74,21, −0,45) | 56,00 (n=1, 56,00–56,00, 0,00, yalnız AA) |
| gpt-6-luna/high | 30,00 (n=1, 30,00–30,00, 0,00, yalnız AA) | 22,00 (n=1, 22,00–22,00, 0,00, yalnız AA) | 41,20 (n=2, 29,00–53,41, +12,20) | 45,00 (n=1, 45,00–45,00, 0,00, yalnız AA) |
| deepseek-flash/max | 58,21 (n=2, 54,41–62,00, −3,79) | 28,00 (n=1, 28,00–28,00, 0,00, yalnız AA) | 37,69 (n=2, 32,38–43,00, −5,31) | 71,00 (n=1, 71,00–71,00, 0,00, yalnız AA) |

## AA’ya göre sıralaması değişen yerler

- **Kod** · gpt-6.2-sol/high 4 → 7, argon/medium 11 → 9, hydrogen/high 8 → 10
- **Muhakeme** · neon/medium 6 → 4, gpt-6.2-sol/high 5 → 7, argon/medium 11 → 9, hydrogen/medium 12 → 14
- **Doğruluk** · haiku-5.5/high 11 → 13
- **Bilgi işi** · fable-5.2/medium 5 → 3, gpt-6.2-astra/medium 12 → 6, argon/medium 11 → 7, gpt-6.2-sol/high 6 → 8, hydrogen/high 6 → 9, opus-5.5/medium 8 → 10, sonnet-5.5/high 8 → 11, gpt-6.2-sol/medium 10 → 12

## Uyarılar

- benchlm, aiiq ve cleus ikincil derleme siteleridir. Kaynak bağlantılarının bir kısmı testin ana sayfasına gider. Ölçümler verilen araştırma raporlarındaki tablolardan alınmıştır.
- Vals Index v2.2’deki GPT-6.2 Sol ölçümünü araştırma raporu, Vals’a atıf yapan Google DeepMind duyurusundan aktarıyor.
- Belirtilmemiş effort için varsayılan eşlemeler · fable-5.2/medium, opus-5.5/high, sonnet-5.5/high, haiku-5.5/high, gpt-6.2-astra/medium, gpt-6.2-sol/high, gpt-6.1-terra/medium, gpt-6-luna/high, neon/high, hydrogen/high, argon/medium, deepseek-flash/max. Açık max ve xhigh ölçümleri, seçili satırlara taşınmadı. Bu ölçümler gerektiğinde kaynak çapası olarak kullanıldı.
- Neon medium için AA Doğruluk puanı kaynakta boş. Veri bulunmayan hücrelerde n=0 gösterildi. Çapa ölçeklemesi puanları 100 ile sınırlamaz.
