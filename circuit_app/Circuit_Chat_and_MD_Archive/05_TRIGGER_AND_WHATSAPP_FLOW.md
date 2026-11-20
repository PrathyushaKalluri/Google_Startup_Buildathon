# How the real household triggers Circuit

## Trigger

The backend server is already running.

A household sends a voice note to the agency’s **connected WhatsApp Business Platform** number.

Meta calls Circuit’s webhook automatically.

```text
Customer WhatsApp
   ↓
Meta Cloud API webhook
   ↓
Circuit verifies signature + dedupes + persists
   ↓
If audio: fetch media → Gnani STT
   ↓
Transcript event resumes case
   ↓
LLM + system prompt + allowed tools
   ↓
RAG / agency data / policy
   ↓
Meta outbound /messages
   ↓
Customer receives question
```

The system prompt does **not** listen to WhatsApp. It is loaded only when the backend invokes the model.

## Meta processing

1. GET webhook verification is setup, not a case event.
2. POST webhook:
   - verify `X-Hub-Signature-256` against raw body;
   - map phone number ID to agency tenant;
   - distinguish `messages[]` from delivery `statuses[]`;
   - dedupe real `wamid`;
   - persist before fast 200;
   - enqueue durable job.

3. Audio:
   - use Meta media ID;
   - get authorized short-lived media URL;
   - download bytes server-side;
   - validate MIME/codec/duration;
   - hash audio;
   - mark case `AWAITING_STT`.

4. Gnani:
   - unique audio message triggers at most one successful/counted request unless an explicit safe retry is allowed;
   - exact provider result stored;
   - `transcript.received` resumes the model.

5. Outbound:
   - Graph API `/{PHONE_NUMBER_ID}/messages`;
   - store accepted message ID;
   - separately store sent/delivered/read/failed status events;
   - obey message-window/template rules.

## Honest fallback

If the team cannot complete Meta onboarding, a local **ROLEPLAY_INBOX** can demonstrate the event loop, but must never be described as live WhatsApp integration.

Phone/SIP is not required in version one.
