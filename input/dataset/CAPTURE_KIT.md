# Capture kit: replacing synthetic media with real

Do this once the pipeline works on the synthetic set. Keep the file names and case folders; `inbox/inbox.json` and the payload files reference them by path.

## Photos (phone camera, no editing; send through WhatsApp so it recompresses)

| Case | File | Shot |
|---|---|---|
| C01 | `01`..`03` photos, see `inbox.json` | Rating plate of any split AC, straight on, flash off; wall below an indoor unit with a damp streak (a wet cloth is enough) |
| C02 | `02_photo.jpg` | AC display showing a two-character code (a coloured sticker or printed card held in front of the display is fine) |
| C04 | `02_photo.jpg` | A TDS meter reading in the 600s in a kitchen |
| C05 | `02_photo.jpg` | A wall-mounted geyser with pipes visible and the bathroom floor wet |
| C06 | `02_photo.jpg` | Freezer compartment with frost build-up |
| C07 | `01_photo.jpg`, `02_photo.jpg` | A purchase invoice (blur names and GSTIN) and an AC carton label. These travel inside the retailer handover payload as attachments |
| C09, C13 | `02_photo.jpg` | Rating plate at an angle, once slightly blurred (C13) and once badly blurred with tap-to-focus off (C09) |

Take each twice: good light, and poor light with a thumb partly in frame.

## Voice

Use `evaluator_only/voice_scripts.json` as the script. Ask a native speaker to read it naturally, not word for word, over a normal phone call, then export the recording as Opus or WAV.

| Case | Kind | Language | Setting |
|---|---|---|---|
| C01 | WhatsApp voice note | Telugu | ceiling fan running |
| C03 | Inbound call | Hindi | kitchen, street noise from a window |
| C05 | Inbound call | Hindi | bathroom corridor, anxious tone |
| C11 | Inbound call | English | outdoors, light street noise |
| C12 | Inbound call | Telugu | ceiling fan |
| C15 | Inbound call | Hindi | a motor running nearby |
| C16 | Inbound call | Telugu | by a road, traffic |

Keep the call-log fields in `inbox.json` (dialled number, caller number, start time) unchanged. Set `duration_s` to the real length.

## Video for the stage case (C03)

C03 is the best case for the live demo. If you want a real video instead of an acted one, film these three shots with a phone camera, 1 to 2 minutes in all:

1. The front of a washing machine with an error code on the display (any code; a printed card works).
2. The bottom right front panel: the small square drain-filter cover being opened, with a bowl under it.
3. What comes out: water, lint, a coin or hair-clip, shown to the camera.

Audio plus video sessions are capped at 2 minutes on Gemini Live unless context-window compression is on, so keep the take short. `evaluator_only/personas/C03.md` says how the household answers.

## After replacing

Keep `evaluator_only/voice_scripts.json` as the reference transcript, since a natural reading drifts from it. Mark transcription against the meaning, not the exact words.
