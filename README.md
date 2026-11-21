# Agent orchestration skills

Six reusable skills for coordinating work across Claude Code, Codex and Antigravity. Use one to assign work, verify results, manage usage limits and hand off an unfinished session.

## Choose a skill

| Skill | Coordinator | Copy the skill folder into |
| --- | --- | --- |
| [Astra](skills/astra-orchestration/) | Codex | `.agents/skills/` |
| [Sol](skills/sol-orchestration/) | Codex | `.agents/skills/` |
| [Neon](skills/neon-orchestration/) | Antigravity | `.agents/skills/` |
| [Fable](skills/fable-orchestration/) | Claude Code | `.claude/skills/` |
| [Mythos](skills/mythos-orchestration/) | Claude Code | `.claude/skills/` |
| [Opus](skills/opus-orchestration/) | Claude Code | `.claude/skills/` |

## Use it in your project

1. Copy the entire folder for your coordinator to the project directory shown above. Keep the folder name and its three files together.
2. Fill in the included project profile example and tell your coordinator where to find the completed profile. List only the workers and providers you can use, plus your permissions, checks and spending rules.
3. Start a session in your project and invoke the skill by name. Try a bounded task with a clear deliverable, one worker and a verification command before attempting a parallel run.

The model and effort names are routing preferences. Check availability, command syntax and usage limits in your own client. These skills contain Markdown instructions and templates. They require no project-specific scripts.

Client documentation follows. [Claude Code](https://code.claude.com/docs/en/skills) · [Codex](https://learn.chatgpt.com/docs/build-skills) · [Antigravity](https://antigravity.google/docs/skills)

## Türkçe kısa başlangıç

Tablodan ana ajanına uygun skill’i seç. Klasörün tamamını kendi projendeki belirtilen dizine kopyala. Örnek proje profilini kullandığın modeller, yetkiler ve test komutlarıyla doldur. Ardından yeni bir oturumda skill’i adıyla çağır.

## License

[MIT](LICENSE)
