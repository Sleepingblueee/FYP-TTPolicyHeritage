\# Codebook for TikTok Policy Document Analysis (v3)



\*\*Version\*\*: v3 (operational alignment)

\*\*Coding unit\*\*: 3-sentence section

\*\*Output\*\*: 16 binary judgments (1=present, 0=absent), multiple codes can apply.



\*\*v3 KEY PRINCIPLES\*\*:

\- (1) \*\*POWER and SAFETY co-occur\*\* in TikTok content rules. Most "we do not allow X / NOT ALLOWED / Do not post" clauses simultaneously assert platform authority (power) AND prevent harm (safety). Code BOTH.

\- (2) \*\*HERITAGE codes (B1-B6) use keyword-anchored judgment\*\*: when a section contains heritage-related vocabulary (religion, religious, sacred, ceremony, ritual, indigenous, tribal, ethnic, traditional, cultural practice, heritage, ancestral) AND discusses what kind of content is permitted/prohibited/governed, code the relevant B-code as 1. Do NOT require "substantive elaboration" — keyword presence within a content-governance context is sufficient.

\- (3) \*\*When in doubt for Part A platform values: code 0\*\*. \*\*When in doubt for Part B heritage codes: code 1\*\* (research focuses on heritage; false negatives lose more signal than false positives).



\---



\## Part A: Platform Values (10 codes, replicating Su \& Chan, 2025, ICS)



\### A1. Power \[v3 OPERATIONAL CHANGE]



\*\*Definition\*\*: The degree to which a platform or users can govern content and protect their rights.



\*\*v3 Decision rule\*\*: Code 1 if the section contains ANY of:

\- Explicit platform-authority language: "we may", "we will", "we reserve the right", "sole discretion", "we will remove", "we will suspend", "we may take action", "subject to enforcement"

\- Content prohibitions framed as platform-issued rules: "We do not allow X", "NOT ALLOWED", "Do not post", "Do not upload", "We do not permit"

\- User-recourse mechanisms: "you may appeal", "binding arbitration"



\*\*v3 RATIONALE\*\*: TikTok's content rules are simultaneously safety substance + power assertions. The platform's authoritative voice ("we do not allow") IS the power signal, even without phrases like "sole discretion".



\*\*Co-coding rule\*\*: When the section is a content prohibition, code BOTH power=1 AND safety=1.



\*\*DO NOT code 1 if\*\*:

\- The section is a routine commercial/contractual term ("all sales are final", "subject to the following terms") with no rule-issuing or enforcement framing.

\- The section is purely user-facing instruction ("you must enter your password correctly").



\*\*Examples\*\*:

\- "We do not allow violent content. NOT ALLOWED: ..." → power=1, safety=1

\- "Content depicting graphic violence will be removed." → power=1, safety=1

\- "All sales of Gifts are final." → power=0, safety=0

\- "Users may appeal account suspensions." → power=1



\---



\### A2. Privacy \[unchanged]



Code 1 if the section discusses how users control their personal information.



DO NOT code 1 if: The section is about preventing harm to others (doxxing) — that is safety. The section is about account visibility for selection — that is choice.



\---



\### A3. Safety \[v3 confirmation]



\*\*Decision rule\*\*: Code 1 if the section describes content prohibitions, restrictions, or affirmative protections oriented toward preventing harm — physical, psychological, social, or to public order.



\*\*v3 Note\*\*: Most TikTok content rules trigger BOTH safety AND power. Default: when you code safety=1 for a prohibition clause, also code power=1 (the platform issuing the prohibition is the power signal).



\---



\### A4. Choice \[unchanged]



Code 1 if section describes user-selectable options. Cues: "you can choose", "opt in/opt out", "toggle", "switch between".



\---



\### A5. Community \[unchanged from v2]



Code 1 ONLY if section invokes "community"/"users"/"creators" as a \*\*valued collective with positive valence\*\*.



DO NOT code 1 if: "Community Guidelines" appears only as document title; "creators" used merely as rule-recipient.



\---



\### A6. Engagement \[unchanged from v2]



Code 1 ONLY if section affirmatively describes mechanisms BY WHICH users participate (posting, livestreaming, gifting, monetization tools, FYP eligibility).



DO NOT code 1 if: section is a content prohibition (those are safety+power); section discusses payment processing; section merely says rules apply.



\---



\### A7. IP Protection \[unchanged]



Code 1 if section discusses copyright, trademark, licensing, content ownership, unauthorized use/reproduction.



\---



\### A8. Improvement \[unchanged]



Code 1 if section describes platform enhancing/expanding/evolving features. Forward-looking language is key cue.



\---



\### A9. Care \[unchanged from v2]



Code 1 ONLY if section directs users to \*\*support resources for distress, harm, vulnerability, wellbeing\*\* — crisis hotlines, mental health resources, abuse reporting paths.



DO NOT code 1 if: section directs users to general educational/reference materials (Creator Academy, Help Center, Safety Center, Learn more pages without distress framing).



\---



\### A10. Accountability \[unchanged]



Code 1 if section describes formal mechanisms to hold the PLATFORM accountable — transparency reports, appeal processes, external audits.



\---



\## Part B: Heritage Codes \[v3 KEYWORD-ANCHORED JUDGMENT]



\*\*v3 OPERATIONAL FRAMEWORK\*\*:



A section qualifies for B-codes if BOTH:

(a) It contains one or more heritage-related keywords (see lists below).

(b) The keyword appears within a section that discusses content rules, content categories, regional exceptions, monetization eligibility, or governance of user behavior.



\*\*The keyword does NOT need to be the section's main topic.\*\* If "religion" appears as one item in a list of protected attributes within a section about hate speech rules, that section IS coded B2=1 (because the keyword is functionally part of the platform's governance discourse around religious content).



\*\*v3 EXPLICIT REJECTION OF v2 RULE\*\*: v2 said "list-mention of religion does not trigger B2". v3 OVERRIDES this — list-mention within a content-governance section DOES trigger B2.



\---



\### B1. Authenticity Claims (Heritage Authenticity)



\*\*Keywords\*\*: authentic, genuine, real, original — IN COMBINATION with cultural/traditional/religious context.



\*\*Decision rule\*\*: Code 1 if section governs the authenticity/legitimacy of cultural, traditional, or religious content. Rare in policy text.



\*\*Note\*\*: Most TikTok policy sections do NOT trigger B1. Reserve for explicit cultural-authenticity discussions.



\---



\### B2. Religious and Sacred Sensitivity \[v3 EXPANDED]



\*\*Keywords\*\*: religion, religious, faith, sacred, ritual, ceremony, ceremonial, worship, spiritual, deity, blasphem, clergy.



\*\*v3 Decision rule\*\*: Code 1 if section contains ANY of these keywords AND discusses content rules, prohibitions, exceptions, or governance.



\*\*v3 INCLUDES\*\* (was 0 in v2, is 1 in v3):

\- Hate speech sections listing "religion" as a protected attribute among others — code B2=1

\- Anti-terrorism sections mentioning "religious motivation" as a category of terrorist intent — code B2=1

\- Content rules where religious context is the keyword trigger but other elements are also governed — code B2=1



\*\*Code 0 if\*\*: section has none of these keywords. (Not "has keywords but doesn't elaborate" — pure keyword absence.)



\---



\### B3. Indigenous and Minority Cultural Protection \[v3 EXPANDED]



\*\*Keywords\*\*: indigenous, tribal, aboriginal, native peoples, ethnic minority, ethnic group, marginalized, appropriation, AND ALSO cultural practice, cultural norm, regional culture, regional exception (cultural).



\*\*v3 Decision rule\*\*: Code 1 if section contains ANY of these keywords AND discusses content rules, exceptions, governance, or behavior categorization.



\*\*v3 INCLUDES\*\* (was 0 in v2, is 1 in v3):

\- Sections about regional/cultural exceptions to content rules (e.g., "we allow regional exceptions for body exposure in common cultural practices") — code B3=1

\- Sections listing "ethnicity" as a protected attribute within hate speech context — code B3=1

\- Sections that mention "cultural practice" or "cultural norms" as a content-governance consideration — code B3=1



\*\*Code 0 if\*\*: section has none of these keywords.



\---



\### B4. Traditional Craftsmanship and Skill Display \[v3 EXPANDED]



\*\*Keywords\*\*: tradition, traditional, heritage, folklore, ancestral, custom (as in customary practice), craftsmanship, artisan, calligraphy, opera, weaving, embroidery, traditional medicine.



\*\*v3 Decision rule\*\*: Code 1 if section contains the word "tradition" or "traditional" or other listed keywords AND the section discusses content rules, content categories, or governance.



\*\*v3 INCLUDES\*\* (was 0 in v2, is 1 in v3):

\- Sections where "traditional" modifies platform-related concepts (e.g., "traditional advertising", "traditional paid promotion") — code B4=1

\- Sections discussing content categories where "traditional" appears in any role — code B4=1

\- Sections about regional content exceptions where cultural/traditional considerations apply — code B4=1



\*\*v3 RATIONALE\*\*: For research operationalization, the appearance of "traditional"/"tradition" within a TikTok policy section is itself a signal that the platform's policy text engages with traditional/heritage concepts in some capacity, even if the immediate semantic referent is "traditional advertising" rather than "traditional crafts". Such sections are research-relevant.



\*\*Code 0 if\*\*: section has none of these keywords.



\---



\### B5. Commercialization of Culture \[unchanged from v2]



Code 1 ONLY if section discusses monetization/virtual gifts/advertising AND cultural/traditional/religious framing is explicit.



\---



\### B6. AI-Generated Cultural Content \[unchanged from v2]



Code 1 ONLY if section discusses AI-generated content AND specifies cultural/traditional/religious/heritage subject matter.



\---



\## Part C: Coding Procedure (v3)



1\. Read the entire 3-sentence section.

2\. For Part A: when in doubt, code 0. EXCEPT for power+safety co-occurrence — when the section is a content prohibition, code BOTH.

3\. For Part B: scan for keywords from the keyword lists. If found AND the section discusses content rules/governance/exceptions, code the relevant B-code = 1.

4\. Heritage keywords carry research-operational weight. Do NOT require "substantive elaboration" beyond the keyword + governance context.



\---



\## Part D: Quick Reference (v3 vs v2)



| Pattern | v2 | v3 |

|---|---|---|

| "We do not allow X" (any prohibition) | safety only | \*\*safety + power\*\* |

| "Subject to terms" (no rule) | nothing | nothing |

| "Religion in protected-attribute list" | nothing | \*\*B2\*\* |

| "Ethnicity in protected-attribute list" | nothing | \*\*B3\*\* |

| "Regional exception for cultural practices" | maybe B3 | \*\*B3 confirmed\*\* |

| "Traditional advertising" | nothing | \*\*B4\*\* |

| "Traditional medicine demonstration rules" | B4 | \*\*B4\*\* |

| "Hate speech: attacks based on race, religion, ethnicity..." (within governance section) | nothing | \*\*B2 + B3 + safety + power\*\* |

