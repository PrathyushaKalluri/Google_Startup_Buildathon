---
name: repair-vocabulary
description: Domain dictionary and phonetics for Indian appliance repair in Telugu, Hindi, and Indian English code-switching.
---

# KeepWell Domain Skill: Repair Vocabulary

Guides the extraction and transcription normalization of multilingual colloquial repair terminology used across Telangana, Andhra Pradesh, and North India.

## Telugu Repair Terms
- **Cooling issues**: "cool avadam ledu" (not cooling), "chilling ledu" (no chilling), "ice kattatledu" (not making ice), "water leak avtundi" (water leaking), "deep fridge lone cooling undi" (cooling only in freezer).
- **Compressor & Gas**: "gas aipoyindi" (gas empty/leak), "gas kottali" (need gas refilling), "compressor on avvatledu" (compressor not starting), "sound vastundi" (making abnormal noise), "tik tik sound" (relay clicking).
- **Electrical**: "current shock kodutundi" (giving electric shock), "power ravatledu" (no power), "stabilizer trip avtundi" (stabilizer tripping), "spark vastundi" (sparking), "vasana vastundi" (smell coming).
- **AC terms**: "remote pani cheyatledu" (remote not working), "air ravatledu" (no air flow), "water tapak mani paduthundi" (water dripping inside room), "outdoor unit tiragatledu" (outdoor fan not spinning).

## Hindi Repair Terms
- **Cooling**: "thanda nahi kar raha" (not cooling), "ice nahi jam raha" (ice not setting), "pani gir raha hai" (water leaking), "chilling band ho gaya" (chilling stopped).
- **Compressor/Gas**: "gas khatam ho gaya" (gas finished/leaked), "gas dalna padega" (need gas refill), "compressor se awaz aa rahi hai" (compressor noisy), "khad khad awaz" (rattling noise).
- **Electrical**: "current mar raha hai" (body shock), "jalne ki badbu aa rahi hai" (burning smell), "dhuan nikal raha hai" (smoke coming).

## Normalization Mapping
When extracting customer input:
- Map "gas issue" / "gas kottali" / "gas khatam" -> `symptom_category: REFRIGERANT_OR_COOLING`
- Map "ice jam" / "ice kattadam" / "defrost problem" -> `symptom_category: DEFROST_SYSTEM`
- Map "shock" / "spark" / "badbu" -> Trigger Immediate `HAZARD_FLAG`
