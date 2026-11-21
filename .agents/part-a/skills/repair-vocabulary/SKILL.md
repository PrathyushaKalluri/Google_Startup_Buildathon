---
name: repair-vocabulary
description: Indic appliance repair vocabulary, colloquialisms, error-code phrasings, and phonetic mappings across English, Hindi, Telugu, and mixed speech for Keepwell's five appliance categories.
---

# Repair Vocabulary (Indic Multilingual)

## Scope
Applies strictly to Keepwell's five appliance categories: `ac`, `refrigerator`, `washing_machine`, `ro_purifier`, `geyser`. Runtime lexicon lives at `services/agents/lexicon/repair_vocabulary.yaml` and is loaded by the intake agent, identity agent, part-name matcher, and Live system prompt.

## Mapping Rules
1. **Normalize colloquialisms before matching:**
   - **Washing machine:** *paani nahi nikal raha / neeru bayataku ravatledu* -> `drain_blocked` (`E21` / drain filter / drain pump); *kapde geela / drum nahi ghoom raha* -> `spin_failure`.
   - **AC:** *thanda nahi kar raha / cooling ledu* -> `no_cooling`; *paani tapak raha / indoor leak* -> `condensate_drain_blocked`; *baraf jam gayi / ice formation* -> `evaporator_frost`.
   - **Refrigerator:** *freezer thanda par niche garam / lower compartment warm* -> `damper_or_airflow_fault`; *compressor awaaz / loud hum* -> `compressor_noise`.
   - **RO purifier:** *paani dheere aa raha / slow flow* -> `sediment_or_membrane_clog`; *swad kharab / bad taste / TDS high* -> `membrane_exhausted`.
   - **Geyser:** *paani garam nahi ho raha / hot water ledu* -> `heating_element_or_thermostat_fault`; *trip ho raha / MCB trips* -> `earth_leakage_safety` (triggers `safety` class).
2. **Error codes:** Spoken digits in Hindi/Telugu (*ee ikkis*, *E twenty one*, *F two*) normalize to uppercase alphanumeric tokens (`E21`, `F2`) before querying `safe_fix_catalogue` and `search_manuals`.
3. **Part-name resolution:** Never trust free-text part names. Normalize phonetic variants (*kapisitar* -> capacitor, *thermostat*, *drain filter*) and resolve strictly through `services/agents/engines/parts.py` against `part_catalogue` + `part_compatibility`.
4. **Canonical copy:** Preserve the exact meanings of the recording notice, Gate 1, Gate 2, and safety stop across `en`, `hi`, and `te` (Contract C9).
