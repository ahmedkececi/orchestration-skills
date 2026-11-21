# Artificial Analysis skorları (2026-11-15)

Kaynak: [Artificial Analysis](https://artificialanalysis.ai/) (atıf şartı). Intelligence Index v5.0.1. Genel endeks API'nin ücretsiz katmanından (`/api/v2/language/models/free`); test başına skorlar API'de Pro istediği için herkese açık `artificialanalysis.ai/leaderboards/models` sayfasındaki veriden alındı (aynı ölçümler). Eski `/api/v2/data/*` uçları 2026-11-04'te kapandı.

## Test → görev profili

Her test yığındaki en iyi skora göre 0–100'e ölçeklendi (Briefcase Elo: (elo−900)/(en iyi−900)), sonra ağırlıklı ortalama:

| Profil | Testler (ağırlık) | Hangi iş |
|---|---|---|
| **Kod** | FrontierCode 2.0 (.4), Terminal-Bench 4.0 (.4), AutomationBench (.2) | çok dosyalı uygulama, hata ayıklama, terminal işi |
| **Muhakeme** | CritPt v2 Hard (.35), HLE-Diamond (.35), Terminal-Bench-Science (.3) | zor karar, matematik/fizik, bilimsel akıl yürütme |
| **Doğruluk** | Omniscience doğruluk (.4), uydurmama oranı (.6) | kaynak okuma, denetim, "bilmiyorum" diyebilme |
| **Bilgi işi** | AA-Briefcase (.5), GDP.pdf (.25), AutomationBench (.25) | belge/PDF işi, özet, toplu düzenleme, araç zinciri |

Hız: **sn/görev** = II takımında görev başına ortalama süre (düşünme dahil uçtan uca); "en hızlı" seçimi buna göre. **$/görev** API fiyatıyla; abonelik tüketimini ölçmez, yalnız aynı havuz içinde modelin ne kadar konuşkan olduğunu gösterir.

## Sınırlar
- V4.1 Flash için "1017" ölçümü kullanıldı. Bir API ağ geçidinin sunduğu sürüm farklı olabilir.
- Gemini 4 Carbon (II 60) agy listesinde yok → yığında değil.
- Talimat izleme (IFBench), uzun bağlam (LCR/MLCR) ve görsel (MMMU) bu modellerin çoğunda boş ya da eksik; profillere girmedi. Video/ses yeteneği AA'da yok, ayrıca kapı olarak uygulanır.
- Claude modellerinde uydurmama oranı düşük (Opus 5.5 medium %33, Fable %42); Google 4 serisinde yüksek (Hydrogen %91, Argon %85–96). Doğruluk profilindeki fark bundan gelir.

## Tablo (II'ye göre)

Kod/Muh./Doğr./Bilgi: profil puanı (0–100). Diğer sütunlar ham skor (%), Briefcase Elo.

| Model (effort) | Şirket / istemci | II | Kod | Muh. | Doğr. | Bilgi | FC2 | TB4 | TBS | CritPt | HLE-D | Omni acc | Uydurmama | Briefcase | AutoB | GDP.pdf | sn/görev | $/görev |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
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
