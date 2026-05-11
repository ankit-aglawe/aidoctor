# Maintainer acks

Before any famous-repo entry lands in `leaderboard.yaml`, a maintainer of that
repo must explicitly ack inclusion. Acks live here as one file per repo:

```
.maintainer-acks/<owner>-<name>.md
```

Each ack file must contain:

1. **Date** the ack was given.
2. **Maintainer's GitHub handle** (must be a maintainer per the repo's public
   member list, or able to merge to main).
3. **Source link** to the ack — a tweet, a comment on an aidoctor issue, a DM
   screenshot stored elsewhere, etc.
4. **Verbatim quote** of the maintainer's ack.

Without all four, the entry must not land in `leaderboard.yaml`. This rule
exists so we never publicly score a famous repo without explicit consent.

If a maintainer ever wants their entry removed, we remove it within 24h, no
explanation required.

## Template

```markdown
# Ack: <owner>/<name>

Date: 2026-MM-DD
Maintainer: @githubhandle
Source: https://twitter.com/.../status/...

> "Verbatim quote of the maintainer agreeing to inclusion."

Verified by: @aidoctor-maintainer
```
