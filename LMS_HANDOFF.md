# GLC v1 — assignment setup for the LMS agent

## What this assignment is

Students implement one slot of the GLC v1 gateway: either a channel
adapter (15 slots) or a voice provider (7 slots). Each slot is
independent — one group's broken code does not fail another group's
CI. Each slot has a fixed 7-test suite (6 structural + 1 behavioural)
that the student must pass.

**Repository**: https://github.com/theschoolofai/glc_v1
**Branch**: `main`
**License**: MIT
**Tech stack**: Python 3.11+, uv, FastAPI, Pydantic v2.

## How many groups

**22 groups maximum**, one slot per group.

### Channel adapter slots (15)

| Slot          | Difficulty | What students implement                                   |
|---------------|------------|-----------------------------------------------------------|
| telegram      | Easy       | Bot API long-poll → ChannelMessage; sendMessage out       |
| discord       | Easy       | Gateway MESSAGE_CREATE; mention resolution                |
| slack         | Medium     | Events API + chat.postMessage; thread_ts continuity       |
| webui         | Easy       | In-browser WebSocket; typing indicator pre-frame          |
| twilio_sms    | Easy       | form-urlencoded webhook; messages.create out              |
| matrix        | Medium     | matrix-nio /sync; mxc:// media download                   |
| line          | Medium     | replyToken store; reply vs push selection                 |
| signal        | Medium     | signal-cli JSON-RPC; group vs DM dispatch                 |
| whatsapp      | Hard       | Cloud API webhook with HMAC X-Hub-Signature-256           |
| teams         | Medium     | Bot Framework activity; Adaptive Card body extraction     |
| gmail         | Hard       | Pub/Sub push → history → messages.get → multipart parse   |
| imap          | Hard       | RFC 822 + IDLE; PDF attachment to artifact store          |
| twilio_voice  | Hard       | TwiML + Media Streams; transcribe + voice_audio_ref       |
| webhook       | Medium     | Stripe-style signed webhook + replay window               |
| local_mic     | Hard       | WAV + VAD + /v1/transcribe round-trip + /v1/speak playback|

### Voice provider slots (7)

| Slot                | Difficulty | What students implement                                  |
|---------------------|------------|----------------------------------------------------------|
| groq_whisper        | Easy       | OpenAI-compat multipart; whisper-large-v3-turbo          |
| kokoro              | Medium     | Local Kokoro-82M pipeline; load-once-reuse pattern       |
| elevenlabs          | Medium     | Flash v2.5 HTTP; 10k chars/month free-tier quota track   |
| cartesia            | Hard       | Sonic streaming HTTP; sub-50ms time-to-first-audio       |
| whisper_cpp         | Hard       | Local whisper-cli subprocess; VAD silence skipping       |
| gemini_live (STT)   | Hard       | BidiGenerateContent WebSocket; setup-frame-first         |
| gemini_live (TTS)   | Hard       | BidiGenerateContent WebSocket; responseModalities=AUDIO  |

`system_fallback` (the eighth TTS provider) is NOT a student slot —
it ships pre-implemented so `/v1/speak?prefer=fallback` works out of
the box on a fresh install.

### If the cohort is smaller than 22 groups

Pick slots in this priority order (most pedagogical value first):
- **Round 1 (Easy)**: telegram, discord, slack, webui, twilio_sms, groq_whisper, kokoro
- **Round 2 (Medium)**: matrix, line, signal, whatsapp, teams, elevenlabs, webhook
- **Round 3 (Hard)**: gmail, imap, twilio_voice, cartesia, whisper_cpp, gemini_live_stt, gemini_live_tts, local_mic

## How students claim a slot

1. **Fork** the repo (it's public — students can fork without permission).
2. Open a PR against the upstream titled `claim: <slot> for <group>`
   that replaces `(unclaimed)` with the group name in
   [`CLAIMS.md`](https://github.com/theschoolofai/glc_v1/blob/main/CLAIMS.md).
3. First-come, first-served. CI rejects double-claims via
   `scripts/validate_claims.py`.
4. The reviewer (`@theschoolofai`) approves and merges the claim PR.

## How students submit their implementation

1. After their claim PR merges, they start their implementation PR
   from a fresh branch off main.
2. The PR body MUST contain:
   - `# Group: <group-name>` marker (one line, exact format)
   - `# Slot: <slot-name>` marker (one line, exact format)
   - Group members list
   - YouTube/Loom demo video link
   - 1-paragraph description of wire-format quirks they hit
3. CI runs three jobs on every push:
   - **boundary** — fails if the PR touches files outside the slot's
     `Owned paths` in CLAIMS.md
   - **test-changed-slot** — runs only their 7-test file, plus ruff +
     mypy on their slot directory
   - **scorecard** — auto-comments a 10-point rubric on the PR

The reviewer (`@theschoolofai`) approves once all three jobs are
green and the demo video has been watched.

## Grading rubric (10 points, auto-scored)

The scorecard bot posts this as a PR comment on every push:

| Item                                  | Points |
|---------------------------------------|--------|
| 6 structural tests pass (1 each)      | 6      |
| 1 behavioural test passes             | 2      |
| `ruff check` clean on owned path      | 0.5    |
| `mypy` clean on owned path            | 0.5    |
| PR template completeness              | 0.5    |
| Adapter discipline (no LangChain etc.)| 0.5    |

**The behavioural test is the load-bearing grader.** Each slot has a
channel/provider-specific test that requires understanding the real
wire format — not just satisfying the envelope contract. A group
that passes all 6 structural tests but fails the behavioural test
demonstrates they wrote an adapter that won't survive the first real
upstream call.

Full per-slot behavioural test list lives in
[`docs/ADAPTER_GUIDE.md §2`](https://github.com/theschoolofai/glc_v1/blob/main/docs/ADAPTER_GUIDE.md)
(channels) and `§9` (voice providers).

## What the LMS shows per group

For each enrolled group, post the following as the assignment page:

- Slot name + difficulty + brief description (from this doc and CLAIMS.md)
- Link to the slot's stub: `glc/<owned_path>/adapter.py`
- Link to the slot's test file: `tests/<slot_test_path>.py`
- Link to the slot's mock-fake: `tests/<mock_path>.py`
- Link to the slot's per-channel README in the catalogue dir
- The 10-pt rubric breakdown above
- Link to [`docs/ADAPTER_GUIDE.md`](https://github.com/theschoolofai/glc_v1/blob/main/docs/ADAPTER_GUIDE.md)
- Link to the live `CLAIMS.md` row so they see the latest claim state

Path patterns the LMS agent can compute mechanically:

```
Channel adapter slot <name>:
  Stub        glc/channels/catalogue/<name>/adapter.py
  Schemas     glc/channels/catalogue/<name>/schemas.py
  README      glc/channels/catalogue/<name>/README.md
  Tests       tests/channels/test_<name>.py
  Mock        tests/channels/mocks/<name>_mock.py
  Owned path  glc/channels/catalogue/<name>/**

STT voice provider slot <name>:
  Stub        glc/voice/stt/providers/<name>/adapter.py
  Tests       tests/voice/stt/test_<name>.py
  Mock        tests/voice/stt/mocks/<name>_mock.py
  Owned path  glc/voice/stt/providers/<name>/**

TTS voice provider slot <name>:
  Stub        glc/voice/tts/providers/<name>/adapter.py
  Tests       tests/voice/tts/test_<name>.py
  Mock        tests/voice/tts/mocks/<name>_mock.py
  Owned path  glc/voice/tts/providers/<name>/**
```

## Deadlines (fill in per cohort)

- Claim deadline: <YYYY-MM-DD>
- Implementation PR deadline: <YYYY-MM-DD>
- Demo video deadline: <YYYY-MM-DD>
- Review window: <YYYY-MM-DD> – <YYYY-MM-DD>

## Repo settings already configured

The upstream maintainer (`@theschoolofai`) has set the following on
`theschoolofai/glc_v1`:

- Branch protection on `main`:
  - Requires PR before merging
  - Requires 1 approving review from `@theschoolofai` (the CODEOWNER)
  - Requires status checks: `boundary`, `test-changed-slot`, `lint`,
    `test`, `schema-validation`, `claims-uniqueness`
  - Requires linear history (no merge commits from forks)
- Actions: workflow write permissions enabled (so the scorecard bot
  can post PR comments)
- Public repo: students fork without an invite

## What success looks like

Per group:
- Their PR merged.
- Scorecard ≥ 8/10.
- Demo video shows their adapter working against the real channel /
  provider, not just the mock.

For the cohort:
- All 22 slots merged.
- The fully-implemented gateway services `/v1/transcribe`,
  `/v1/speak`, and all 15 channels under `WS /v1/channels/<name>`
  end-to-end.

## Files the LMS agent should read

| File                          | Why                                                         |
|-------------------------------|-------------------------------------------------------------|
| `CLAIMS.md`                   | Slot list + Owned paths (the canonical truth)               |
| `docs/ADAPTER_GUIDE.md`       | Full workflow + 7-test rubric per slot                      |
| `docs/ARCHITECTURE.md`        | What students are building inside (Session 11 §7 moves)     |
| `docs/POLICY_GUIDE.md`        | The policy engine reference (relevant to security review)   |
| `docs/VOICE_GUIDE.md`         | STT/TTS provider setup + free-tier signup pointers          |
| `VALIDATION.md`               | What's already verified; remaining caveats                  |
| `.github/workflows/`          | CI gates the assignment relies on                           |
| `scripts/scorecard.py`        | The grading script (run manually for spot-checks)           |
| `scripts/check_pr_boundaries.py` | The boundary enforcer                                    |
