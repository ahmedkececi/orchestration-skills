# Ultimate Orchestration Skills

[English](#english) · [Türkçe](#türkçe) · [Offline demo](examples/first-run.md) · [Contributing](CONTRIBUTING.md)

## English

**Keep your agents working when a model hits its quota.** Add quota-aware routing, independent review and restartable handoffs to Claude Code, Codex or Antigravity. The presets guide your coordinator using the model runners and permissions you configure.

[Try the offline benchmark preview](examples/first-run.md#preview-model-data-offline) · [See a quota handoff](examples/first-run.md#follow-a-quota-handoff)

### Quick install

From your project, choose the command for your client. This copies just the coordinator and the measurement updater into the project. The optional provider skill can be added to the same install by appending `--skill add-provider-orchestration-skills`.

```sh
# Codex
npx skills add ahmedkececi/ultimate-orchestration-skills --agent codex --copy \
  --skill sol-orchestration --skill update-orchestration-skills

# Claude Code
npx skills add ahmedkececi/ultimate-orchestration-skills --agent claude-code --copy \
  --skill opus-orchestration --skill update-orchestration-skills
```

For Antigravity, another coordinator, or an install without Node.js, use the manual instructions below. [Skills CLI options](https://github.com/vercel-labs/skills#usage)

### What makes it different

| Design choice | Why it matters |
| --- | --- |
| Route by the task and the quota pool | A fast implementation model, a reviewer who can check a PDF, and the worker with capacity left may be three different choices. The presets account for difficulty, input type, read/write permissions and available allowance. |
| Compare the profiles that matter | Coding, reasoning, factual accuracy and knowledge work are separate signals. Pick a replacement on the evidence that matters for this unit and compare task times only where they were measured on the same basis. |
| Make reviews independent | Give a fresh reviewer from another model family the artifact and acceptance checks. The coordinator sees both the result and its limits before accepting it. |
| Resume from artifacts | The handoff records ownership, accepted decisions, remaining units and the next check. A new coordinator can pick up from the checkpoint when a quota window closes. |
| Refresh without waiting for a release | The updater verifies model releases and measurements from their sources and refreshes the current workspace. The next routing decision can use that data immediately. |

### Choose a coordinator

| Preset | Coordinator | Project location |
| --- | --- | --- |
| [Astra](skills/astra-orchestration/) | Astra in Codex | `.agents/skills/` |
| [Sol](skills/sol-orchestration/) | Sol in Codex | `.agents/skills/` |
| [Neon](skills/neon-orchestration/) | Neon in Antigravity | `.agents/skills/` |
| [Mythos/Fable](skills/fable-orchestration/) | Either Mythos or Fable in Claude Code | `.claude/skills/` |
| [Opus](skills/opus-orchestration/) | Opus in Claude Code | `.claude/skills/` |

1. For manual installation, copy the chosen skill folder and the [update skill folder](skills/update-orchestration-skills/) into the project's location above. Keep both folder names.
2. Fill in the project profile example from the coordinator folder. List authorized runners, data scopes, budget, writable paths and verification commands. Confirm model IDs and effort levels in your client.
3. Invoke the coordinator skill by folder name, using `/<name>` in Claude Code or Antigravity and `$<name>` in Codex. Start with a bounded deliverable, one eligible worker and a verifiable acceptance check.

### Refresh model data on demand

Run `/update-orchestration-skills` in Claude Code or Antigravity. In Codex use `$update-orchestration-skills`.

- **No model name:** Lists verified releases newer than the presets' reference models and asks which to add. The update looks up benchmarks and saves data for the models you choose. Incomplete catalog coverage is reported alongside the list.
- **One model name:** For example, `/update-orchestration-skills Claude Opus 4.8` requests just that model. Named lookups accept any release date. Its exact model ID and any published scores are verified before saving. You can also ask for a preview or import your own measurements.

For each model and effort, the update checks every raw test from the bundled benchmark suite. The output uses `-` for any test result it could not verify. The command uses the client's live source tools and the included Python 3.9+ helper. It merges verified source observations into `.orchestration/model-measurements.md` in the current workspace. Newly announced models can appear with unknown scores. Comparable observations have source links, a date, model and effort, version or cohort, and a count and range for averaged results. The project's access and routing rules still determine which models can run.

The [historical snapshot](skills/update-orchestration-skills/references/model-measurements.md) combines benchmark scores and profile averages in one Markdown file. The [collection guide](skills/update-orchestration-skills/references/collection.md) describes live lookup and custom imports.

### Add a provider

Install [add-provider-orchestration-skills](skills/add-provider-orchestration-skills/) alongside the updater. Run `/add-provider-orchestration-skills PROVIDER` in Claude Code or Antigravity, or `$add-provider-orchestration-skills PROVIDER` in Codex. The agent checks the provider's public catalog and how to call its models. It asks which models you want, then looks up the full benchmark suite for your choices. The provider's sources and setup details go in `.orchestration/provider-catalogs.json`. Future catalog checks include that provider. The project profile still controls which runners can receive work.

Client docs [Claude Code](https://code.claude.com/docs/en/skills) · [Codex](https://learn.chatgpt.com/docs/build-skills) · [Antigravity](https://antigravity.google/docs/migration/workflows-to-skills/)

## Türkçe

**Bir modelin kotası dolduğunda iş devam etsin.** Claude Code, Codex veya Antigravity’de kota durumuna göre görev dağıt, bağımsız inceleme yap ve yarım kalan işi dosyalardan devret. Hazır profiller, projene tanımladığın model çalıştırıcılarını ve yetkileri kullanır.

[API anahtarı gerektirmeyen demo](examples/first-run.md#türkçe-kısa-başlangıç) · [Kota devri örneği](examples/first-run.md#follow-a-quota-handoff)

### Hızlı kurulum

Proje dizininde yukarıdaki [kurulum bölümünden](#quick-install) Codex veya Claude Code komutunu seç. Komut seçili koordinatörü ve ölçüm güncelleyicisini projeye kopyalar. Antigravity, farklı bir koordinatör veya Node.js olmadan kurulum için aşağıdaki adımları kullan.

### Neyi farklı yapıyor?

| Tasarım tercihi | Ne kazandırır? |
| --- | --- |
| Göreve ve kota havuzuna göre yönlendirme | Hızlı kod yazan model, PDF doğrulayabilen model ve kotası müsait model farklı olabilir. Hazır profiller işin zorluğunu, girdi türünü, okuma ve yazma yetkilerini ve kalan kotayı hesaba katar. |
| İşe uygun ölçümleri karşılaştırma | Kodlama, muhakeme, olgusal doğruluk ve bilgi işi ayrı değerlendirilir. Yedek seçerken göreve uygun ölçümleri kullanır, süreleri yalnızca aynı koşullarda ölçüldüklerinde karşılaştırırsın. |
| Bağımsız inceleme | Başka bir model ailesinden yeni bir inceleyiciye çıktıyı ve kabul ölçütlerini verirsin. Koordinatör işi kabul etmeden önce sonucu ve doğrulamanın sınırlarını görür. |
| Dosyalardan devam etme | Devir kaydı, sorumluları, alınan kararları, kalan işleri ve sıradaki kontrolü içerir. Kota penceresi dolduğunda yeni koordinatör kaldığı yerden devam edebilir. |
| Yeni sürüm beklemeden güncelleme | Yenileme skill’i yeni çıkan modelleri ve ölçümlerini kaynaklarından doğrular. Bir sonraki yönlendirme kararı, çalışma alanındaki güncel veriyi kullanabilir. |

### Koordinatör seç

| Hazır profil | Koordinatör | Projedeki konumu |
| --- | --- | --- |
| [Astra](skills/astra-orchestration/) | Codex’te Astra | `.agents/skills/` |
| [Sol](skills/sol-orchestration/) | Codex’te Sol | `.agents/skills/` |
| [Neon](skills/neon-orchestration/) | Antigravity’de Neon | `.agents/skills/` |
| [Mythos/Fable](skills/fable-orchestration/) | Claude Code’da Mythos veya Fable | `.claude/skills/` |
| [Opus](skills/opus-orchestration/) | Claude Code’da Opus | `.claude/skills/` |

1. Elle kurulumda, seçtiğin skill klasörünü ve [yenileme skill’i klasörünü](skills/update-orchestration-skills/) tablodaki proje dizinine kopyala. Klasör adlarını koru.
2. Koordinatör klasöründeki örnek proje profilini doldur. Yetkili çalıştırıcıları, veri kapsamını, bütçeyi, yazılabilir yolları ve doğrulama komutlarını belirt. Model kimliklerini ve efor seviyelerini istemcinde doğrula.
3. Koordinatör skill’ini klasör adıyla çağır. Claude Code ve Antigravity’de `/<ad>`, Codex’te `$<ad>` kullan. Kapsamı belli, tek bir uygun ajana verilebilen ve ölçülebilir kabul kriteri olan bir işle başla.

### Model verilerini istediğin anda yenile

Claude Code veya Antigravity’de `/update-orchestration-skills`, Codex’te `$update-orchestration-skills` yaz.

- **Model adı yoksa:** Hazır profillerdeki referans sürümlerden daha yeni, doğrulanmış modelleri listeler ve hangilerini eklemek istediğini sorar. Sadece seçtiğin modellerin benchmark sonuçlarını araştırır ve kaydeder. Eksik taramalar listede belirtilir.
- **Bir model adı varsa:** Örneğin `/update-orchestration-skills Claude Opus 4.8` yalnızca o modeli arar. Model adı verildiğinde tarih sınırı uygulanmaz. Tam model kimliğini ve yayımlanmış skorları doğrulayıp kaydeder. Önizleme isteyebilir veya kendi ölçüm verini de içe aktarabilirsin.

Güncelleme, her model ve efor seviyesi için arşivdeki testlerin tamamını arar. Doğrulanamayan test sonuçlarını tabloda `-` ile gösterir. Komut, istemcinin canlı kaynak araçlarını ve paketteki Python 3.9+ yardımcısını kullanır. Doğrulanan ölçümleri çalışma alanındaki `.orchestration/model-measurements.md` dosyasına yazar. Yeni duyurulmuş bir modelin skoru henüz yoksa bu alan bilinmiyor olarak kalır. Karşılaştırılabilir ölçümler kaynak bağlantısı, tarih, model, efor ve ölçüm sürümüyle birlikte gösterilir. Ortalamalarda ölçüm sayısı ve aralığı yer alır. Hangi modellerin kullanılabileceğini projenin yetki ve yönlendirme kuralları belirler.

[Arşiv](skills/update-orchestration-skills/references/model-measurements.md), benchmark skorlarını ve profil ortalamalarını tek Markdown dosyasında birleştirir. [Veri toplama kılavuzu](skills/update-orchestration-skills/references/collection.md) canlı aramayı ve özel veri aktarmayı açıklar.

### Sağlayıcı ekle

[add-provider-orchestration-skills](skills/add-provider-orchestration-skills/) klasörünü güncelleyicinin yanına kur. Claude Code veya Antigravity’de `/add-provider-orchestration-skills SAĞLAYICI`, Codex’te `$add-provider-orchestration-skills SAĞLAYICI` yaz. Ajan resmî kataloğu ve modellerin nasıl çağrıldığını araştırır. Hangilerini eklemek istediğini sorar, ardından seçtiklerin için benchmark listesinin tamamını kontrol eder. Sağlayıcının kaynaklarını ve kurulum bilgilerini `.orchestration/provider-catalogs.json` dosyasına kaydeder. Sonraki katalog taramaları bu sağlayıcıyı da içerir. Hangi çalıştırıcılara görev verilebileceğini proje profili belirler.

İstemci belgeleri [Claude Code](https://code.claude.com/docs/en/skills) · [Codex](https://learn.chatgpt.com/docs/build-skills) · [Antigravity](https://antigravity.google/docs/migration/workflows-to-skills/)

## License · Lisans

[MIT](LICENSE)
