# Case guide (EVALUATOR ONLY)

Do not feed this file, `ground_truth.json`, `voice_scripts.json` or `true_stock.csv` to the app. They exist so you can mark what the app did.

Twenty cases arrive on Saturday 21 Nov 2026 between 06:45 and 10:00 IST, through four triggers: household message (WhatsApp, app), household call, brand-forwarded request, retailer handover.
Each case names the receiving centre, the raw input, what a careful human would conclude, and what the app is expected to do at each gate. `evaluator_only/personas/<case>.md` tells whoever plays the household how to answer; it holds the real situation, so it never goes to the app.

| Trigger | Cases |
|---|---|
| household message | C01, C02, C04, C06, C08, C09, C10, C13, C14 |
| household call | C03, C05, C11, C12, C15, C16 |
| brand forward | C17, C18, C19 |
| retailer handover | C07, C20 |

## C01. Ramesh Babu

- Trigger and channel: household message via whatsapp
- Receiving centre: Aerovane Authorised Service, Gachibowli (`c_av`)
- Number: known to Keepwell
- Inputs: audio, image, image
- Fault: ac_drain
- Root cause: Indoor drain hose sagging with a low point since installation; water backs up over the tray
- Min technician level: 1
- Duration (min): 45
- Urgency class: standard
- Safety issue: False
- Entitlement: brand_warranty (installed 14 Dec 2025, 12 months comprehensive); installer-caused so labour should not be charged
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: asked; household says yes
  - **gate2**: asked after yes; household prefers to stay in chat
  - **fix**: SF-AC-DRAINLOOK offered; household cannot see the hose end: abandon, no harm
  - **record**: what was tried goes into the visit plan
  - **authority**: c_av is authorised for Aerovane
  - **identity**: phone and sticker resolve to the existing household and appliance
- Traps:
  - Telugu voice note
  - household says 'warranty' (true)
  - sticker and leak photos should link the case to the appliance
  - protective step: switch the AC off, catch the water

## C02. Priyanka Menon

- Trigger and channel: household message via whatsapp
- Receiving centre: Aerovane Authorised Service, Gachibowli (`c_av`)
- Number: known to Keepwell
- Inputs: text, image
- Fault: ac_lowgas
- Root cause: Slow leak at indoor flare joint; R32 low, E6 protection active
- Parts: [('R32', 3), ('FLARE', 1)]
- Min technician level: 3
- Duration (min): 100
- Urgency class: standard
- Safety issue: False
- Certification: ['gas']
- Entitlement: paid (comprehensive warranty ended 18 Jun 2026; gas and leak labour not covered)
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: asked; household says yes
  - **gate2**: asked; household chooses video
  - **fix**: no safe fix fits an E6 on an Aerovane (refrigerant protection); filter clean is not offered because filters were cleaned and an error code is showing
  - **video**: agent can read the display and the ice on the valve; no step is guided
  - **record**: checks done on video go into the plan
- Traps:
  - E6 on Aerovane means low pressure
  - needs gas-certified technician with R32 on van

## C04. Venkata Lakshmi

- Trigger and channel: household message via whatsapp
- Receiving centre: AquaCare RO and Geyser Services, Manikonda (`c_aq`)
- Number: known to Keepwell
- Inputs: text, image
- Fault: ro_membrane
- Root cause: RO membrane scaled; sediment filter exhausted; output TDS 612
- Parts: [('MEMB', 1), ('SED', 1), ('CARB', 1)]
- Min technician level: 2
- Duration (min): 50
- Urgency class: planned
- Safety issue: False
- Entitlement: AMC covers labour and visits; membrane and filters are excluded consumables
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: asked; yes
  - **gate2**: asked; household declines video, continues in chat
  - **fix**: SF-RO-FLOW does not fit (flow is normal, taste is the problem): none offered
  - **identity**: household and appliance known; the AMC plan belongs to this centre
- Traps:
  - TDS 612 is read from the photo
  - AMC covers labour not parts
  - filter change four months ago does not mean the sediment filter is fine

## C06. Harika Reddy

- Trigger and channel: household message via whatsapp
- Receiving centre: Lakeshore Service Centre, Jubilee Hills (`c_ls`)
- Number: known to Keepwell
- Inputs: text, image
- Fault: fr_defrost
- Root cause: Defrost heater open circuit plus stuck defrost bimetal; evaporator iced over
- Parts: [('DEFH', 1), ('DEFT', 1)]
- Min technician level: 3
- Duration (min): 85
- Urgency class: urgent
- Safety issue: False
- Entitlement: paid (12 month warranty ended 25 May 2023)
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: asked; yes
  - **gate2**: asked; household stays in chat
  - **fix**: SF-FR-SEAL: seal and thermostat fine -> not_worked; stop condition 'food at risk' is true so no further fixes
  - **urgency**: class urgent from rule: food and infant milk at risk; the household is never asked 'how urgent'
  - **protective**: advice to move milk and medicines to a neighbour's fridge is a safety message regardless of gate 1
- Traps:
  - Roman Telugu with English
  - food spoilage
  - model not verified in memory

## C08. Meera Nair

- Trigger and channel: household message via whatsapp
- Receiving centre: Cool Craft Appliance Services, Madhapur (`c_cc`)
- Number: known to Keepwell
- Inputs: text
- Job type: preventive_service
- Root cause: Three split ACs due for service; the fixed-speed unit's outdoor fan capacitor is weak
- Min technician level: 1
- Duration (min): 70
- Urgency class: planned
- Safety issue: False
- Entitlement: one unit under Cool Craft AMC (service included); two paid
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: not applicable: preventive service
  - **gate2**: not applicable
  - **batching**: one visit for three units; the 3-day window applies to slot shaping, not here
  - **reminder**: the reply links to the reminder row; only c_cc sends reminders for these units
- Traps:
  - same-household batching
  - reply to a reminder
  - service intervals differ per unit
  - household mentions the slow fan: add to the plan

## C09. Tenant (Rohit)

- Trigger and channel: household message via whatsapp
- Receiving centre: Zenith Care Hub, Kondapur (`c_zn`)
- Number: new to Keepwell
- Inputs: text, image
- Fault: ac_dirty
- Root cause: Indoor coil and filters heavily clogged; not serviced in over a year
- Min technician level: 1
- Duration (min): 70
- Urgency class: standard
- Safety issue: False
- Entitlement: paid; payer is the landlord (tenant is not owner); Zenith warranty ended 20 Jun 2023
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: asked; yes
  - **gate2**: asked; household chooses video
  - **fix**: SF-AC-FILTER guided on video (Zenith manual cover); partial improvement, smell remains -> worked or not_worked recorded as the household reports
  - **identity**: blurry sticker; the label is read properly on video; serial matches no existing record: create verified appliance
- Traps:
  - blurry sticker
  - tenant versus owner payer
  - no history

## C10. Unknown

- Trigger and channel: household message via whatsapp
- Receiving centre: Frost and Wave Service Point, Kukatpally (`c_fw`)
- Number: new to Keepwell
- Inputs: text
- Fault: fr_ptc
- Root cause: PTC start relay burnt; compressor clicks and trips
- Parts: [('PTC', 1)]
- Min technician level: 2
- Duration (min): 45
- Urgency class: standard
- Safety issue: False
- Entitlement: paid (Frostline FL-D340 bought 3 Sep 2024)
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: asked after the clarifying questions; yes
  - **gate2**: asked; household stays in text
  - **fix**: SF-ANY-POWER (socket and plug check) -> not_worked
  - **clarify**: agent has to ask brand, symptom, address and whether food is at risk; one question at a time
  - **urgency**: class set by the three fact questions: little food at risk, appliance partly working -> standard
- Traps:
  - one-line message with no media
  - no household record
  - brand and model unknown until asked

## C13. Shilpa Rao

- Trigger and channel: household message via whatsapp
- Receiving centre: Cool Craft Appliance Services, Madhapur (`c_cc`)
- Number: known to Keepwell
- Inputs: text, image
- Fault: wm_lid
- Job type: repair
- Root cause: Lid switch not registering closure
- Parts: [('LIDSW', 1)]
- Min technician level: 2
- Duration (min): 40
- Urgency class: standard
- Safety issue: False
- Entitlement: paid (WC-TL70 bought 5 Nov 2021)
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: asked; yes
  - **gate2**: asked; video
  - **fix**: SF-WM-LID guided on video: still beeps -> not_worked
  - **identity**: provisional appliance (no serial); the label is read on video; merge provisional into verified; log the merge
- Traps:
  - very blurry sticker
  - household typed 'WC TL 70 maybe'
  - do not reserve parts before the model is confirmed

## C14. Faisal Ahmed

- Trigger and channel: household message via whatsapp
- Receiving centre: Cool Craft Appliance Services, Madhapur (`c_cc`)
- Number: known to Keepwell
- Inputs: text
- Job type: repair
- Root cause: Two appliances: AV-FL12N3 low gas; FL-S190 fridge gasket torn
- Parts: [('R32', 3), ('FLARE', 1), ('GASK', 1)]
- Min technician level: 3
- Duration (min): 150
- Urgency class: standard
- Safety issue: False
- Certification: ['gas']
- Entitlement: paid for both
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: asked once for the message; yes
  - **gate2**: asked; Rukhsar switches to video for the fridge
  - **fix**: SF-FR-SEAL on video: seal torn -> not_worked, but the label is read
  - **identity**: fridge is provisional; model and serial read from the label on video; merge logged
  - **consent**: household has NOT agreed to share technical history across centres: do not read other centres' records
- Traps:
  - two tickets from one message
  - one visit across two categories
  - fridge gasket is model-specific

## C03. Sunita Sharma

- Trigger and channel: household call via voice
- Receiving centre: Frost and Wave Service Point, Kukatpally (`c_fw`)
- Number: known to Keepwell
- Inputs: call
- **Best case for the stage prototype**
- Fault: wm_drain
- Root cause: Pump housing blocked: coins and lint in the filter, one coin lodged in the pump housing
- Min technician level: 1
- Duration (min): 40
- Urgency class: standard
- Safety issue: False
- Entitlement: paid (24 month warranty ended 30 Oct 2026, 22 days ago); brand may still consider goodwill
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: asked on the call; yes
  - **gate2**: asked; household switches to video through a WhatsApp link
  - **fix**: SF-WM-DRAINFILTER guided on video; partial drain, E21 returns -> not_worked
  - **record**: what was tried, what came out (coins), what the machine did after
  - **rerun**: diagnosis re-run: pump housing now more likely than filter; visit plan lists 'already tried'
- Traps:
  - warranty expired 22 days ago
  - Hindi voice
  - E21 maps to drain failure; no part should be quoted before the technician sees the pump
  - filter cover is a manual-sanctioned cover

## C05. Rajesh Agarwal

- Trigger and channel: household call via voice
- Receiving centre: Heatwell Authorised Service, Banjara Hills (`c_hw`)
- Number: known to Keepwell
- Inputs: call, image
- Fault: gy_earth
- Root cause: Heating element insulation breakdown leaking current to tank body
- Parts: [('HEL_ST', 1)]
- Min technician level: 3
- Duration (min): 70
- Urgency class: safety
- Safety issue: True
- Certification: ['electrical']
- Entitlement: brand_warranty (24 months from 14 Feb 2025)
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: NOT asked (safety flag)
  - **gate2**: NOT asked
  - **fix**: none; protective steps only: keep the geyser and its MCB off, do not touch taps or the unit, keep children away
  - **video**: not offered; the household is not asked to go near the heater
  - **record**: protective message logged as sent
- Traps:
  - SAFETY: no household inspection
  - household already switched it off
  - Hindi voice

## C11. Naveen

- Trigger and channel: household call via voice
- Receiving centre: Cool Craft Appliance Services, Madhapur (`c_cc`)
- Number: new to Keepwell
- Inputs: call
- Fault: ac_lowgas
- Root cause: Likely low refrigerant
- Parts: [('R32', 3)]
- Min technician level: 3
- Duration (min): 100
- Urgency class: standard
- Safety issue: False
- Entitlement: unknown
- First-visit fix possible: False
- Expected behaviour:
  - **gate1**: asked; yes
  - **gate2**: asked; stays on the call
  - **fix**: SF-AC-FILTER cannot be guided without video and the household declines the panel step: none
  - **service_area**: 501218 is outside this centre's service pincodes: decline politely, say plainly that this line cannot book it, capture the contact for follow-up only with consent, do not name another centre
- Traps:
  - Shamshabad is outside every service area
  - agent must not recommend another centre

## C12. Srinivas Goud

- Trigger and channel: household call via voice
- Receiving centre: Lakeshore Service Centre, Jubilee Hills (`c_ls`)
- Number: known to Keepwell
- Inputs: call
- Fault: wm_drain
- Root cause: Outlet hose kinked behind the machine and standpipe partly blocked; the drain motor replaced 18 days ago is working
- Min technician level: 2
- Duration (min): 40
- Urgency class: urgent
- Safety issue: False
- Entitlement: repeat visit within 30 days of a repair by the same centre: no visit charge; flag for quality review
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: asked once, calmly; household declines
  - **gate2**: not asked (gate 1 not yes)
  - **fix**: none offered after the no; the agent does not press
  - **urgency**: rule URG-REPEAT-30D fires: urgent
  - **record**: earlier ticket linked; assign by fit, flag the earlier technician for review without blame
- Traps:
  - repeat complaint 18 days after drain motor replacement
  - Telugu voice with frustration
  - household refuses video

## C15. Pooja Singh

- Trigger and channel: household call via voice
- Receiving centre: Lakeshore Service Centre, Jubilee Hills (`c_ls`)
- Number: known to Keepwell
- Inputs: call
- Fault: wm_motor_sa
- Root cause: Wash motor winding overheated after run-capacitor failure; smoke and burning smell
- Parts: [('MCAP', 1)]
- Min technician level: 2
- Duration (min): 60
- Urgency class: safety
- Safety issue: True
- Entitlement: paid (bought 15 Jul 2019)
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: NOT asked (safety flag)
  - **gate2**: NOT asked
  - **fix**: none; keep it unplugged, do not run, ventilate the balcony
  - **protective**: safety message sent regardless of any gate
- Traps:
  - SAFETY: smoke from the motor
  - Hindi voice
  - semi-automatic model

## C16. Ganesh Yadav

- Trigger and channel: household call via voice
- Receiving centre: Aerovane Authorised Service, Gachibowli (`c_av`)
- Number: known to Keepwell
- Inputs: call
- Fault: ac_cap
- Root cause: Outdoor fan run capacitor failed (fixed-speed unit); compressor runs, condenser fan does not
- Parts: [('CAPF', 1)]
- Min technician level: 2
- Duration (min): 45
- Urgency class: standard
- Safety issue: False
- Entitlement: paid (2020 unit)
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: asked; household says no
  - **gate2**: not asked
  - **fix**: none: a no is a no
  - **record**: declined gate recorded; no pressure; the visit plan notes no self-fix was tried
  - **clarify**: agent still asks the diagnostic questions it needs
- Traps:
  - traffic noise on the call
  - inverter ACs have no fan capacitor but this is fixed-speed
  - capacitor is a common van-stock part

## C17. Sandeep Kulkarni

- Trigger and channel: brand forward via brand_api
- Receiving centre: Zenith Care Hub, Kondapur (`c_zn`)
- Number: known to Keepwell
- Inputs: brand_request payload
- Fault: fr_defrost
- Root cause: Defrost heater failed; dF shown
- Parts: [('DEFH', 1)]
- Min technician level: 3
- Duration (min): 85
- Urgency class: standard
- Safety issue: False
- Entitlement: brand_warranty (Zenith 24 months from Dec 2024; ends 7 Dec 2026); claim reference ZN-CRM-2026-0481923
- First-visit fix possible: True
- Expected behaviour:
  - **authority**: c_zn is authorised for Zenith: warranty claim allowed
  - **identity**: payload phone resolves to the existing household via household_member; serial resolves to the existing appliance
  - **gate1**: asked after the agent calls the household; yes
  - **gate2**: asked; video
  - **fix**: SF-FR-SEAL on video: seal fine, vents under frost -> not_worked
  - **brand_loop**: status goes back to the brand under the same reference
  - **invoice**: ask for the invoice: serial prefix suggests an earlier build
- Traps:
  - brand has already taken the story once: do not make the household repeat it
  - dF differs from Frostline Er4
  - warranty ends in 16 days: claim date matters

## C18. Deepak Chowdary

- Trigger and channel: brand forward via brand_api
- Receiving centre: Cool Craft Appliance Services, Madhapur (`c_cc`)
- Number: new to Keepwell
- Inputs: brand_request payload
- Fault: ac_lowgas
- Root cause: Low refrigerant (leak at outdoor service valve)
- Parts: [('R32', 3)]
- Min technician level: 3
- Duration (min): 100
- Urgency class: standard
- Safety issue: False
- Entitlement: brand_warranty on paper (bought 14 Mar 2026), but the receiving centre is independent for Aerovane
- First-visit fix possible: False
- Expected behaviour:
  - **authority**: c_cc holds 'independent' for Aerovane: no authority for warranty work; the agent must say so, return the request to the brand with the reason, and not book a warranty visit
  - **paid_option**: may offer a paid (non-warranty) visit only if the household chooses after being told the warranty would not apply
  - **identity**: new household from the brand record (verified_via brand_record), appliance created from the serial
- Traps:
  - brand routed to a centre that cannot honour warranty
  - no recommendation of another centre

## C19. Ananya Das

- Trigger and channel: brand forward via brand_api
- Receiving centre: AquaCare RO and Geyser Services, Manikonda (`c_aq`)
- Number: known to Keepwell
- Inputs: brand_request payload
- Fault: gy_thermo
- Root cause: Thermostat cut-out tripped; reset needs a technician after checking the element
- Parts: [('THS', 1)]
- Min technician level: 3
- Duration (min): 60
- Urgency class: standard
- Safety issue: False
- Certification: ['electrical']
- Entitlement: brand_warranty (Heatwell 24 months from 13 Jun 2025)
- First-visit fix possible: True
- Expected behaviour:
  - **authority**: c_aq holds authorised_service for Heatwell since 1 Sep 2026: allowed
  - **identity**: payload phone and serial resolve to the existing household and appliance known to c_hw
  - **cross_centre**: household consented to share technical history: read_shared_history returns c_hw's technical rows (not its prices); the read is logged
  - **gate1**: asked; yes
  - **gate2**: asked; household chooses to stay in chat
  - **fix**: SF-GY-SWITCH: switch on, thermostat mid, light off -> not_worked; stop condition (any shock, tripping) not met
- Traps:
  - household expects the previous centre
  - the agent must not disclose c_hw's prices or notes
  - do not recommend either centre

## C07. Anand Iyer

- Trigger and channel: retailer handover via retailer_api
- Receiving centre: Zenith Care Hub, Kondapur (`c_zn`)
- Number: new to Keepwell
- Inputs: retailer_handover payload with 2 attachment(s)
- Job type: installation
- Root cause: New Zenith Aura 1.5T inverter split on 9th floor, outdoor unit on an external ledge; copper run about 5 m
- Parts: [('FLARE', 1)]
- Min technician level: 3
- Duration (min): 150
- Urgency class: planned
- Safety issue: False
- Certification: ['work_at_height', 'gas']
- Entitlement: paid installation; Zenith warranty requires authorised or approved installer
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: not applicable: installation is not a repair
  - **gate2**: not applicable
  - **identity**: new phone: create a household with verified_via retailer_record, provisional until the household replies
  - **appliance**: serial from the handover and the carton label match: create a verified appliance
  - **authority**: c_zn is authorised for Zenith
- Traps:
  - unknown household
  - invoice and carton label agree with the payload
  - location pin in the payload
  - work-at-height certified installer

## C20. Mahesh Raj

- Trigger and channel: retailer handover via retailer_api
- Receiving centre: Frost and Wave Service Point, Kukatpally (`c_fw`)
- Number: known to Keepwell
- Inputs: retailer_handover payload
- Job type: installation
- Root cause: Front-load washer installation and demo; household already known to Keepwell through another phone number
- Min technician level: 1
- Duration (min): 60
- Urgency class: planned
- Safety issue: False
- Entitlement: paid installation; Wavecrest warranty starts from installation
- First-visit fix possible: True
- Expected behaviour:
  - **gate1**: not applicable
  - **gate2**: not applicable
  - **identity**: retailer phone is a household_member's number: resolve to the existing household, do not create a second household
  - **appliance**: serial new: create a verified appliance, link the fridge's household
  - **reminder**: no reminder consent assumed for the new appliance
- Traps:
  - retailer used the husband's number
  - the owner on record is the wife
  - duplicate household risk
