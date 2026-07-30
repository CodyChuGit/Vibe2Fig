# projects/

One folder per app you mirror into Figma. **Git-ignored by default** — your
project's ledger, captures, and specs are working memory, usually private.

Layout per project (created by the skill as it works):

```
projects/<app>/
  config.json        # device table, bundle id, save path — see example/
  tokens.json        # extracted design tokens
  digests/*.yaml     # per-screen layout digests (LLM pass, reviewable)
  specs/*.json       # spec IR node trees (core/spec_schema.md)
  state.json         # THE LEDGER: every Figma id, prop key, asset hash,
                     # measured geometry, and design decision. Never delete —
                     # update-mode diffs code against this file.
  captures/          # seeded simulator screenshots (ground truth)
```

Start a new project by copying `example/config.example.json` to
`projects/<app>/config.json` and filling in the fields — the save path must
come from reading the app's persistence code, not assumption.
