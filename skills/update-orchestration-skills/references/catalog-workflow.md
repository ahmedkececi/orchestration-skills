# Catalog discovery and provider registration

## Discover releases after the preset versions

Run the catalog plan inside the skill using the actual workspace root. The bundled registry defines the active reference models named by the orchestration presets. It includes official [OpenAI](https://developers.openai.com/api/docs/models), [Anthropic](https://platform.claude.com/docs/en/models/overview), [Google](https://aistudio.google.com/docs/models) and [DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/) sources as well as additions from this workspace.

```sh
python3 -B scripts/catalogs.py plan --workspace /path/to/project
```

1. Use the official model documentation and dated release history to confirm each reference model's release date. For a moving alias, use the pinned revision documented by the preset or archive. Keep the alias and its model revision distinct.
2. In each catalog, inspect all relevant pages and versions. In each release feed, inspect the complete date range back to the earliest applicable reference date (or the configured `since` date if earlier or there is no reference). Keep the union of model IDs plausibly in range from the two sources and their linked model pages, including entries with an unclear date. Exclude unrelated product features, aliases that only point at an already counted release, and models outside the catalog's documented scope. Preserve real versioned previews when documented as accessible, and describe their access conditions.
3. Resolve each seen ID against the official documentation. Use that family's reference date. Use family `other` for a genuinely new family, which starts at the configured `since` date, or `unknown` when the family cannot be resolved. Dates must be the underlying model release dates, not the date a feature was added to a client. Report an unresolved order when only a matching calendar date is known.
4. Mark a source `read` only if all relevant pages, tabs and dates were covered. Use `partial` for any truncated list, inaccessible page or insufficient history, and `unavailable` when no relevant content could be read. Include seen IDs only where actually observed. Public coverage applies to the listed sources; private account catalogs and unannounced releases are outside that coverage.

### Report format

Supply one JSON object with `checked_on` (an ISO date) and `providers` (an array). Each provider report has the following fields.

| Field | Contents |
| --- | --- |
| `id` | Provider ID from the plan. |
| `sources` | Objects with `url` (exact registered catalog or release-history URL), `status` (`read`, `partial`, or `unavailable`) and `seen` (list of model IDs actually observed). |
| `anchors` | Objects with `family`, `model` (the planned reference ID), `released` (ISO date), and `url` (official date evidence). Omit unverified anchors. An added provider uses an empty list. |
| `releases` | Unique objects with `model` (canonical ID), `family` (a planned family, `other` or `unknown`), `released` (ISO date or null) and `url` (official model or release page). Include seen IDs with a verifiable identity even when their date is unknown. |

When an apparent alias from one source resolves to a canonical release listed elsewhere, use the canonical release ID in both `seen` and `releases`. A catalog row that cannot be resolved keeps its observed ID in `seen` so the verifier can flag it.

```sh
python3 -B scripts/catalogs.py verify --workspace /path/to/project --input scan.json
```

The helper checks each registered provider, source, reference version and observed ID. It returns only verified models with dates strictly after their reference date and reports incomplete coverage separately. Read this output before looking up benchmark scores. In catalog mode, pass only `measurements` to the refresh helper (or omit `--input` when there are none); model rows come from the verified catalog report. The program checks structure, date order and source coverage against the submitted evidence. Live lookups and confirmation of what each source says are the agent's responsibility.

## Register a provider

Use the provider command to verify official catalog, release-history and runtime documentation before making a registration. Save these fields as a JSON object.

| Field | Contents |
| --- | --- |
| `id` | Stable lowercase provider name with optional hyphens. |
| `catalogs`, `release_notes`, `usage_docs` | Nonempty arrays of official public HTTPS documentation URLs. For the catalog, use model listings; for release notes, use dated entries or dated model documentation with navigable history. |
| `since` | ISO date from which the updater should discover releases. Use the user's requested date or the date on the bundled plan. |
| `runtime` | Object with `mode` (`api`, `cli`, or `managed-client`), `entrypoint` (documented HTTPS API base URL, executable name or client name), `auth` (`api-key`, `oauth`, `account-session`, `platform-managed`, or `none`), `credential_env` (environment variable name or null), and `model` (an exact documented example ID). |

The registry is `.orchestration/provider-catalogs.json` in the project. A registration records how to discover and call a provider; the caller still configures its account, data permissions and budgets in the project profile. The helper accepts an identical repeat registration and reports an existing provider if the supplied entry differs.
