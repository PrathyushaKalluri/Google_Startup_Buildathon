# Circuit — Round 3 Part 2: the business around the agent

Editable online version: https://claude.ai/code/artifact/d75c092c-2d21-4b0a-969e-f444b2a068a2
Landing page: https://claude.ai/artifact/XDhbAZG6KthSpGiRQX6rbS

Servify should build Circuit and sell it to independent multi-brand repair agencies, the after-sales market its brand-first business can't reach today.

## Where Circuit lives and how a customer starts

Circuit lives on the agency's own WhatsApp Business number and phone line, sold by Servify as "Servify Circuit". There is no new app for anyone. The household thinks it is talking to Sri Sai Electronics, because it is: Circuit introduces itself as that agency's AI assistant.

**How an agency starts (the paying customer):**

1. The owner signs up on the landing page and gets a 30-day free pilot.
2. Servify's onboarding team connects the agency's WhatsApp Business number and forwards unanswered or after-hours calls to Circuit.
3. The owner shares the technician list, skills, prices and parts on hand, as a photo of the register or a Google Sheet. This is Circuit's day-one knowledge.
4. From the next customer message, Circuit handles intake, questions, technician ranking, quotes and readiness checks. The owner gets a WhatsApp summary every evening at 8 PM.

**How a household starts:** exactly as today. They message or call the agency they already trust, and Circuit answers in Telugu, Hindi or English.

## Why Servify should build it

Servify already owns three of the four things Circuit needs: device and warranty data, a parts business, and an appliance repair network. What it lacks is a reason for independent agencies to let it in.

| Asset | Evidence | What Circuit uses it for |
| --- | --- | --- |
| Scale in after-sales | About 8 million service transactions a year, 18,000+ service centres, 12 countries (Blume) | Seeds Mistri Gyan, the shared fault library, with real repair outcomes |
| Appliance home-service network | Acquired 247around in 2022: 150+ partner brands, service across about 19,000 PIN codes (BusinessWire) | Technicians and agencies already on Servify's books become the first pilot users |
| Warranty and protection plans | Runs white-labelled programmes such as AppleCare and Samsung Care+; protection plans and platform licensing were its biggest revenue line at ₹663 Cr (A Junior VC) | Circuit checks warranty status and sells a protection plan after each repair |
| Spare parts | Handset and spare-parts sales grew 66% to ₹91 Cr in the same period (A Junior VC) | Supplies the part Circuit predicts, before the technician leaves |

**Why it hasn't built Circuit yet:** Servify's paying customers are brands, and its platform is sold by the number of devices a brand manages (Gartner). A brand wants its own authorised centres fixing its own machines, in warranty. Out-of-warranty repairs by independent, multi-brand agencies in Eluru or Ramagundam earn a brand nothing, so no brand client asks Servify to serve them.

That gap is the opportunity. Most of an AC's life is spent out of warranty, and most tier-2 and tier-3 households call a local agency for that work. Circuit is how Servify reaches those repairs without competing with its brand clients: it equips the agency the household already trusts, under that agency's name.

## Who pays, and how Servify makes money

Servify sells Circuit to **independent multi-brand AC and appliance repair agencies in tier-2 and tier-3 towns, with 2 to 15 technicians**. The agency pays; the household pays nothing extra.

**What agencies do today:** the owner's personal phone, a WhatsApp chat per customer, and a register or notebook. The technician often arrives without the model number or the right part, diagnoses on site, and comes back with the part later.

**What that costs:** published visit charges cluster at ₹200–500, and a wasted trip's real cost is 45–90 minutes of technician time and a lost job slot, not petrol (team desk research, file 04). No India first-visit-fix rate is published; the global field-service average is about 77%, so roughly one job in four needs another trip. Missed after-hours calls go to a competitor.

| Revenue line | Who pays | How it works |
| --- | --- | --- |
| Circuit subscription | Agency | ₹1,499 a month per agency (pilot assumption, to be tested). It pays for itself if it saves 3–8 wasted trips a month at ₹200–500 each. |
| Parts | Agency | Circuit predicts the likely part before dispatch; Servify supplies it through its existing parts business at a margin. |
| Protection plans | Household | After a verified repair, Circuit offers an extended warranty or annual service plan, underwritten through Servify's existing protection business. The agency earns a commission. |

The subscription gets Servify in the door; parts and protection plans are where the margin is, because Servify already runs both at scale.

## The first 1,000 users

A user is **one agency** running live customer cases through Circuit.

| Channel | Why they're there | Target agencies |
| --- | --- | --- |
| Agencies already in Servify and 247around's service network that also take private, out-of-warranty jobs | Servify already pays them and has their numbers | 400 |
| Parts wholesalers in each town | A counter poster and the shop owner's referral; the wholesaler earns per signup | 300 |
| Technician and agency WhatsApp groups and local trade associations | Where owners already trade jobs and parts | 200 |
| Agencies listed on Justdial and Sulekha in pilot towns | They already pay for leads, so they feel the cost of a missed call | 100 |

**What gets them to try it:** launch in February, before AC season peaks in March–May, with one promise: never miss an after-hours or overflow call this summer. The pilot is free for 30 days and takes the owner 20 minutes to set up.

**What keeps them after three weeks:** the 8 PM WhatsApp summary showing trips saved and money recovered, and the customer history Circuit builds, which they lose if they leave.

**Retained at three weeks means:** in week 3, the agency routed at least 10 customer cases through Circuit and the owner acted on at least 3 evening summaries. Below that, Servify's onboarding team calls the owner.

## Landing page

https://claude.ai/artifact/XDhbAZG6KthSpGiRQX6rbS — written for agency owners, with a "Start a free 30-day pilot" sign-up form. The footer states it's a competition concept, not a Servify product.

## What could kill Circuit in year one

The biggest risk is a wrong "ready" call: one technician sent with the wrong part, and the owner stops trusting Circuit.

| Risk | Why it could kill it | What we do about it |
| --- | --- | --- |
| Wrong diagnosis or wrong part | One wasted trip caused by Circuit erases a month of saved trips in the owner's mind | Circuit only calls a visit "ready" when every check passes; otherwise it books an honest inspection visit. Owner sign-off stays on for the pilot. |
| Technicians bypass it | Our interviews found informal cash side-payments beyond the quoted price, confirmed by two households and a technician | Show technicians what they gain: fewer return trips, parts ready, payment captured on proof. Don't police side deals in year one. |
| Brand clients see a conflict | A brand may not want Servify helping independents repair its machines | Circuit sends in-warranty cases to the official brand route and never touches warranty claims. |
| WhatsApp and voice costs or rules change | Meta's pricing or policy on business messaging decides Circuit's unit cost | Keep the phone and Gnani voice route working as a fallback channel. |
| Data and consent | Machine history and household numbers are personal data under India's data protection law | Consent at first contact; household data stays with the agency; nothing shared across agencies without consent. |
| Seasonality | AC demand drops sharply after summer, and agencies may cancel | Add washing machines, RO purifiers and refrigerators before the first monsoon. |

## Sources

- Blume Ventures on Servify: https://blume.vc/commentaries/from-service-engineer-to-servify-how-sreevathsa-prabhakar-is-transforming-the-boring-after-sales-service-industry-into-a-billion-dollar-opportunity
- BusinessWire, Servify acquires 247around: https://www.businesswire.com/news/home/20220218005234/en
- A Junior VC case study: https://www.ajuniorvc.com/servify-unicorn-public-case-study-ipo-electronics-device-management
- Gartner Peer Insights, Servify: https://www.gartner.com/reviews/product/servify
- Team desk research, research/04_technician_and_agency_economics.md
- Team interviews (7 calls, Sep 2026)

The ₹1,499 price, channel targets and retention threshold are our assumptions for the pilot, not measured figures.
