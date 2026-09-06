# Local workshop with Qwen3.5-4B

Use LM Studio with **Qwen3.5-4B GGUF Q4_K_M** on an Apple silicon Mac with
16 GB memory. It is the verified model format for this checkout. The MLX
4-bit weights are also suitable for Apple silicon, but LM Studio catalog
registration was unreliable during this setup.
Start with an 8192-token context and the 35-ticket demo suite.

## Install

On macOS with Homebrew:

```bash
brew install --cask lm-studio
open -a "LM Studio"
```

Otherwise install from [LM Studio](https://lmstudio.ai/download).
Complete the app's first-run setup. The app must stay running while using the
workshop. Its bundled `lms` CLI manages downloads and the local server.

Download Qwen3.5-4B GGUF Q4_K_M and Nomic Embed Text v1.5 GGUF in the app.
Use these exact repositories to avoid similarly named fine-tunes:

- [lmstudio-community/Qwen3.5-4B-GGUF](https://huggingface.co/lmstudio-community/Qwen3.5-4B-GGUF)
- [nomic-ai/nomic-embed-text-v1.5-GGUF](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF)

Equivalent CLI downloads:

```bash
lms get https://huggingface.co/lmstudio-community/Qwen3.5-4B-GGUF@Q4_K_M --gguf -y
lms get https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF@Q4_K_M --gguf -y
```

Load the chat model with identifier `qwen3.5-4b` and the embedding model with
identifier `text-embedding-nomic-embed-text-v1.5`. These identifiers match
`.env.example`; use `lms ls` for downloaded paths and `lms ps` for loaded IDs.
The workshop sends `reasoning_effort=none` by default through
`PARCELCO_REASONING_EFFORT=none`: short replies must fit the 1024-token output
budget. Use a current LM Studio release that supports this parameter; clear the
environment setting for a different server that does not support it. Qwen3.5
does not support Qwen3's prompt-only thinking switches.

If an old CLI reports an invalid passkey after installing/updating the app, open
LM Studio and rerun the command once its bundled CLI has updated. Interrupted
model downloads can be resumed; a partial file is not yet a loadable model.

Start the API server at `http://127.0.0.1:1234`:

```bash
lms server start --port 1234
curl -fsS http://127.0.0.1:1234/v1/models
```

## Python and exercises

Run these commands from the checkout containing `pyproject.toml` (some downloads
have a second `self-improving-ai-agent-workshop` directory inside the first):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
cp -n .env.example .env
python -m parcelco.doctor
python -m unittest discover -s tests -v
python -m parcelco.cli serve --suite demo
```

Open [the dashboard](http://127.0.0.1:5050) and follow [WORKSHOP.md](WORKSHOP.md).
After restarting your laptop, open LM Studio, load both models, start its server,
activate `.venv`, and run the final serve command again.

The doctor checks real chat, embeddings, and Chroma retrieval. Ordinary ticket
runs fall back to keyword retrieval if embeddings fail, so a working reply alone
does not prove the embedding exercise is configured. Rebuild the Chroma index
after changing embedding models with
`python -c "from parcelco.rag import rebuild_index; print(rebuild_index())"`.

For a live integration check, run `python scripts/verify_local.py`. It evaluates
the demo suite before and after one learning round using temporary prompt,
learnings, and history files, so your workshop's learning state is preserved.
Expect this to take longer than the unit tests; pass rates depend on the model.

Langfuse is optional and disabled by default. Follow
[LANGFUSE_DOCKER.md](LANGFUSE_DOCKER.md) before filling its keys into `.env`.
The full suite has 1000 tickets (700 improve, 300 holdout); the demo uses 35
(20 improve, 15 holdout). Each ticket may generate up to three replies, and
learning rounds rerun evaluations. Start with demo before attempting full.

## References

- [LM Studio CLI](https://github.com/lmstudio-ai/lms)
- [OpenAI-compatible API](https://lmstudio.ai/docs/developer/openai-compat/chat-completions)
- [Qwen3.5-4B configuration and non-thinking mode](https://huggingface.co/Qwen/Qwen3.5-4B)
- [Setup progress and verification](SETUP_PROGRESS.md)
