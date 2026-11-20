# Next steps

1. Unzip this archive into a private project folder.
2. Give Codex/Claude Code the whole folder.
3. Paste **only `03_MASTER_BUILD_PROMPT.md`** as the coding instruction.
4. Choose Gemini OR Claude and put the real key into a private `.env`.
5. Add Gnani key privately.
6. Implement local event/state/RAG skeleton first.
7. Implement actual Meta webhook/media flow.
8. Run one small real Gnani probe.
9. Prove vertical slice:
   **WhatsApp audio → Meta webhook → Gnani → one LLM grounded question → real WhatsApp response → trace**.
10. Only then build technician/part/quote/S5 flow.
11. Add Pine/Delhivery documentation-simulation.
12. Rehearse unhappy paths.
13. Record the ≤5-minute submission.
14. Generate final Round 3 decision table and mockups from the **actual running UI**, not from static prebuilt screens.

## Manual access needed
- Meta WhatsApp Business Platform test/business setup;
- one runtime LLM key/model;
- Gnani STT key/credit;
- consenting participant(s);
- at least one rights-cleared AC source passage;
- documented Pine/Delhivery examples.

## Stop criteria
Do not call the prototype “live” until real Meta+Gnani+LLM+WhatsApp outbound has actually been exercised and logged.
