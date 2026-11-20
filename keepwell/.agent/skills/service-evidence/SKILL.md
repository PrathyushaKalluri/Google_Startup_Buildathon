---
name: service-evidence
description: Standards for appliance identity verification and Home Memory service record evidence.
---

# KeepWell Domain Skill: Service Evidence & Home Memory

## Appliance Identity Standards
1. **Model Plate OCR**:
   - Primary: Model number (e.g. `GL-B201ABPY`, `RT28T3722S8`, `183V CZR`), Serial number, Date of manufacture, Rated wattage/capacity.
   - Confidence threshold: Field confidence >= 0.85. If lower, prompt household or technician to verify or type manually.
2. **Matching Rule**:
   - Exact match on (Customer Phone + Model / Serial) -> Link to existing Appliance Record.
   - If no match -> Create new unverified appliance passport, marked `provisional: true`.

## Home Memory Lifecycle Events
Every repair creates a permanent event in the appliance passport:
- `technician_reported`: Work done, parts replaced, initial symptoms diagnosed.
- `customer_verified`: Customer confirmation received after on-site testing.
- `14_day_health_check`: Automated check-in with customer on day 14 to confirm First-Visit Resolution.
