## Pracmo (璞奇) Skills Repository

[简体中文](README_ZH.md) | English

**This repository contains the skill service definitions used by the Pracmo (璞奇) app.**  
Each *skill* is an AI capability module for a specific interest or learning scenario. Skills can be called by the app conceptually and, in some environments, reused or extended by developers.

### Included skills

- **`pracmo-practice-everything`**
  - Purpose: turns almost any learning goal (exams, interviews, coding, languages, personal interests, etc.) into a loop of *question → answer → feedback → next question*.
  - Features: supports single choice, multiple choice, true/false questions and tutoring-style explanations, with adaptive difficulty.
  - Directory: see the `pracmo-practice-everything/` folder (for example `SKILL.md` inside it) for more detailed design and usage notes.

### Validation & tooling

- **Verified environment**: these skills are currently verified in **ClaudeCode**.  
- **Interactive dependency**: interactive practice flows rely on the **AskUserQuestion TOOL** for presenting questions and collecting answers, as described in `pracmo-practice-everything/SKILL.md`.  
- **Other environments**: other runtimes and tool stacks are not fully validated yet – you are welcome to try integrating them and share feedback via issues.

### Relation to the Pracmo app

- The **Pracmo (璞奇) app does not directly embed these `SKILL.md` files**.  
- The skills in this repo implement part of the interaction logic and behavior used when practicing with AI, but the app contains a **more complete, product-grade experience** (UI, data, additional flows, etc.).  
- For the full feature set and best experience, we recommend using the official app alongside this repository.

### Use with the Pracmo app

If you are an end user, you generally do not need to touch this repository.  
Just use the features in the app:

1. Download and install **Pracmo (璞奇)** on your phone:
   - iOS: [Download on the App Store](https://apps.apple.com/cn/app/%E7%92%9E%E5%A5%87/id6744847459)
2. Open the app and choose or create an *interest space* (for example, "Coding practice", "Sci‑fi writing", or "Spoken English").
3. Follow the in‑app guidance to start practicing or chatting with AI; the concepts here mirror part of that experience, but the app may implement additional or slightly different logic.

> Note: the exact set of capabilities and how they are wired may vary by app version and does **not** depend on this repo at runtime. Please refer to what you see in the app.

### Using this repo as a developer

If you want to integrate or extend these skills programmatically:

- Go into the corresponding skill folder (for example `pracmo-practice-everything/`) and read `SKILL.md` and other docs there.
- Follow the documented contracts/config formats to load the skill in your own agent, tooling or IDE integration.
- Ensure your environment exposes an **AskUserQuestion TOOL** (or equivalent structured question tool) so that interactive practice flows behave as designed.
- Customize the behavior with your own models or data sources while respecting privacy and security requirements.

### Feedback and contributions

- **Issues**: Please open an issue if you find problems in a skill or in its docs.
- **Usage feedback**: Especially welcome are reports from environments other than ClaudeCode, so we can improve compatibility and docs.
- **New skills**: If you have a skill design that fits this repo, feel free to propose it via issues or pull requests.

This repository will evolve together with the Pracmo (璞奇) app and related tooling to help more people turn their interests into structured learning and creative capabilities.

