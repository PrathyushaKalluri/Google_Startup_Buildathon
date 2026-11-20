---
name: safety-escalation
description: Hazard lexicon and emergency triage rules for immediate human escalation.
---

# KeepWell Domain Skill: Safety Escalation Protocol

Safety rules are deterministic and run BEFORE any LLM reasoning or diagnostic generation.

## Critical Hazards (P0 - Immediate Human Escalation)
If any of the following symptoms or keywords are detected, the job is immediately flagged with `hazard_status: CRITICAL` and moved to `HAZARD_REVIEW` state:

1. **Refrigerant Gas Leak (R-600a / R-32 Flammable Gas)**:
   - Keywords: pungent chemical smell, hissing sound with oily discharge, flammable gas odor, breathing difficulty near unit.
   - Action: Instruct customer to ventilate room, do not operate switches or open flames, prioritize emergency dispatcher contact.

2. **Electrical Shock / Earthing Failure**:
   - Keywords: "shock kodutundi", "current mar raha hai", body shock, tingling sensation on appliance metallic door/chassis.
   - Action: Instruct customer to unplug the unit from wall socket immediately and avoid touching the appliance with bare hands.

3. **Burning Smell / Sparks / Smoke**:
   - Keywords: "spark vastundi", "jalne ki badbu", smoke, burning plastic smell, burnt wire odor, loud pop with sparks.
   - Action: Turn off main MCB/switch, disconnect supply, flag for senior technician inspection.

4. **Water Leakage onto Electrical Components**:
   - Keywords: water leaking onto compressor junction box, water on socket/plug.

## Safety Release Gate Requirement
- **Hazard Escalation Recall**: Must be 100% on the evaluation test suite. Zero tolerance for missed hazards.
