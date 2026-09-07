# Self-improving AI agent workshop

Teach a fictional ParcelCo support agent to retrieve policy, check a reply, retry with concrete feedback, and decide what to remember. The model weights stay fixed; prompts and saved lessons can change.

## Choose one route

| Your route | Start here |
|---|---|
| Attend and run the local model | Complete the one-page [prework checklist](docs/PREWORK.md), then use the [workshop exercises](docs/WORKSHOP.md). |
| Follow along without a model | Open the [hosted visual guide](https://manasv20.github.io/self-improving-ai-agent-workshop/) or the offline [`docs/index.html`](docs/index.html). Use the checklist and gate exercises; the live dashboard cannot generate tickets without a model. |
| Install, troubleshoot, or restart | Use the single authoritative [setup guide](docs/SETUP.md), with separate macOS/Linux and Windows instructions. |
| Facilitate the session | Use the [facilitator notes](docs/SPEAKER_NOTES.md) and complete the 24-hour preflight. |

The hosted guide is published from `docs/` by GitHub Actions. If the link returns 404, a repository administrator may still need to choose **GitHub Actions** under **Settings → Pages → Build and deployment**. The checked-in HTML remains available offline.

The demo suite contains 47 tickets: 28 learn-set tickets and 19 holdout tickets. Model replies and timings vary; a failed retry or reverted lesson is still a useful workshop result.
