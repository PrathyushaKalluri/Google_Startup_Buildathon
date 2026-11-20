# Partner integration boundaries

## Gnani — real for voice

Endpoint:
`POST https://api.vachana.ai/stt/v3`

Server-side:
- `X-API-Key-ID`;
- multipart `audio_file`;
- `language_code`;
- max 60-second REST clip;
- target demo ~15–30 seconds;
- preserve exact HTTP result;
- no assumed confidence field;
- no machine-sound fault classifier claim.

Protect credits:
- internal `GNANI_MAX_PER_CASE`;
- internal `GNANI_DEMO_MAX_STT_CALLS`;
- cache by Meta message ID + media hash;
- no silent truncation;
- safe text fallback on 403/429/credit exhaustion;
- call budgets are Circuit limits, not claimed vendor quotas.

## Pine Labs — documentation-simulated first

Use only a response shape supported by the exact supplied docs and feed it as an **external Wizard event**.

Keep distinct:
- adult payer’s real role-play permission;
- provider request created;
- mandate active;
- reserve blocked;
- debit requested;
- final settlement.

`CREATED` does not mean authorized or paid.

Core demo does not implement a 30% deposit.

No real debit in rehearsal.

## Delhivery Maps — documentation-simulated first

Use geocode/matrix/route capability only where verified from docs.

Maps does not provide:
- part inventory;
- compatible SKU;
- technician acceptance;
- literal part custody;
- guaranteed arrival time.

Main scenario uses agency-held synthetic kit plus separate role-play actor custody acknowledgment.

Delhivery One parcel booking is not a core first-demo dependency.

## Three-imagined-capability budget

Count conservatively:
1. shared Machine Kundli network;
2. shared Mistri Gyan knowledge network;
3. leave one unused unless necessary.

Do not invent a Gnani/Pine/Delhivery endpoint to use this allowance.
