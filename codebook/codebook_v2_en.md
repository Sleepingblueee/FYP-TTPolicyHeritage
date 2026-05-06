\# Codebook for TikTok Policy Document Analysis (v2)



\*\*Project\*\*: TikTok LIVE Cultural Heritage Governance Research

\*\*Author\*\*: \[Student Name]

\*\*Advisor\*\*: Dr. Qian Guo, BNBU

\*\*Last updated\*\*: \[Date]

\*\*Coding unit\*\*: a "section" = three consecutive sentences from a TikTok policy document

\*\*Output for each code\*\*: binary judgment (1 = present, 0 = absent)

\*\*Multiple codes can apply to the same section.\*\*



\*\*Version history\*\*:

\- v1: initial draft, replicating Su \& Chan (2025) ICS Table 2 for codes A1-A10, plus 6 heritage codes (B1-B6) designed by author.

\- v2: based on pilot reliability test (n=30), tightened decision rules for power, care, engagement, community to address Gemini over-coding; added explicit "do not code" anti-patterns for each code; added few-shot disambiguation examples.



\---



\## Part A: Platform Values (10 codes, replicating Su \& Chan, 2025, ICS)



These ten codes' operational definitions are reproduced verbatim from Su, C. C., \& Chan, N. K. (2025), "Assembling platform governance as private ordering in the age of generative AI", \*Information, Communication \& Society\*, Table 2. The "Decision rule" and "DO NOT code 1 if" sections are added by the present author for coding precision.



\---



\### A1. Power



\*\*Definition (Su \& Chan, 2025)\*\*: The degree to which a platform or users can govern content and protect their rights.



\*\*Decision rule\*\*: Code 1 ONLY if the section explicitly asserts WHO holds decision-making authority — that is, the section discusses authority itself as a meta-rule. Look for cues like "sole discretion", "we reserve the right", "we may determine", "we have the authority to", "users may appeal", "we will decide", "binding arbitration".



\*\*DO NOT code 1 if\*\*:

\- The section is merely a content prohibition (e.g., "We do not permit X", "We do not allow Y"). Content prohibitions are coded under SAFETY only, NOT power.

\- The section merely lists rules users must follow (e.g., "REQUIRED disclosures include..."). Rule-listing is not the same as authority-asserting.

\- The section describes contractual terms (e.g., "subject to the following terms", "you acknowledge and agree"). These are TOS conventions, not power assertions.

\- The section describes refund/return policies (e.g., "all sales are final"). These are commercial terms, not power.



\*\*Positive examples (CODE 1)\*\*:

\- "We reserve the right to remove any content that violates these guidelines."

\- "Users may appeal account suspensions through our review process."

\- "TikTok will determine, in its sole discretion, what content qualifies."



\*\*Negative examples (CODE 0)\*\*:

\- "We do not allow content that promotes violence." → safety only, NOT power

\- "Users must follow these guidelines." → no authority claim

\- "All sales of Gifts are final." → commercial term, not power



\---



\### A2. Privacy



\*\*Definition (Su \& Chan, 2025)\*\*: The degree to which users are empowered to manage their personal information, encompassing permissions for data control, sharing, and customization.



\*\*Decision rule\*\*: Code 1 if the section discusses how users can control their personal information — including data collection, data use, data sharing, account visibility settings tied to personal info, or customization of privacy settings.



\*\*DO NOT code 1 if\*\*:

\- The section is about general user education or community-building, even if "privacy" is mentioned in passing as one of many topics.

\- The section is about preventing harm to others (doxxing, impersonation). That is SAFETY.

\- The section is about account visibility for SELECTION reasons (e.g., "make your account private as an option"). That is CHOICE, not privacy.



\*\*Positive examples (CODE 1)\*\*:

\- "You can review and delete the personal information you have shared."

\- "We will not disclose your information to third parties without consent."

\- "Users may opt out of personalized advertising."



\*\*Negative examples (CODE 0)\*\*:

\- "Do not share other people's private information." → safety, not privacy

\- "Creating a positive community involves policies, settings, technology..." → too generic, mention is incidental



\---



\### A3. Safety



\*\*Definition (Su \& Chan, 2025)\*\*: The degree to which platform allows or prohibits users from posting to preserve the well-being of users, the platform community, and/or organizations.



\*\*Decision rule\*\*: Code 1 if the section describes content prohibitions, restrictions, or affirmative protections oriented toward preventing harm — physical, psychological, social, financial, or to public order. Most TikTok content rules are safety.



\*\*DO NOT code 1 if\*\*:

\- The section is purely procedural (e.g., "we may update these terms").

\- The section is about commercial terms unrelated to harm prevention.



\*\*Positive examples (CODE 1)\*\*:

\- "We do not allow content that depicts or promotes violence."

\- "Content that may harm minors will be removed."

\- "We do not allow account behaviors that may spam or mislead our community."

\- "Deceptive engagement practices are prohibited to preserve a trustworthy space."



\*\*Negative examples (CODE 0)\*\*:

\- "Users may appeal moderation decisions." → accountability, not safety

\- "Visit the Safety Center for resources." → care/reference, not safety prohibition



\---



\### A4. Choice



\*\*Definition (Su \& Chan, 2025)\*\*: The degree to which users are free to pick options that align with their interests (e.g., opt-in/opt-out).



\*\*Decision rule\*\*: Code 1 if the section describes mechanisms by which users SELECT among options to customize their platform experience. Look for: "you can choose", "opt in / opt out", "toggle", "you can set up", "switch between", "select".



\*\*DO NOT code 1 if\*\*:

\- The section discusses choices the platform makes (e.g., "we may decide to..."). That is power.

\- The section discusses what users MUST do (obligations, not choices).



\*\*Positive examples (CODE 1)\*\*:

\- "Users can choose to receive notifications via email or app."

\- "You may opt out of data collection for advertising purposes."

\- "You can set up multiple accounts on TikTok."

\- "You can use the branded content toggle to make required disclosures."



\*\*Negative examples (CODE 0)\*\*:

\- "We will determine if your content violates these rules." → power

\- "Users must comply with these terms." → obligation



\---



\### A5. Community



\*\*Definition (Su \& Chan, 2025)\*\*: The degree to which a platform values a certain social group characterized by shared practices, communication technologies, and intimate relations.



\*\*Decision rule\*\*: Code 1 ONLY if the section invokes "the community" / "our users" / "our creators" as a \*\*valued collective with positive valence\*\* — a group to be celebrated, protected, or built. The section must construct them as a coherent social group, not just reference them as users-of-the-platform.



\*\*Test before coding 1\*\*: would removing the word "community"/"creators" fundamentally change the section's meaning? If the answer is "no, the section is mainly about something else", code 0.



\*\*DO NOT code 1 if\*\*:

\- "Community" appears only in titles like "Community Guidelines" without further elaboration as a collective.

\- "Creators" is used merely to address the audience for rules (e.g., "all creators must follow X"). Mention as rule-recipient ≠ valued collective.

\- "Community" is mentioned in passing as a reason for a rule (e.g., "to protect our community from spam") — this is borderline; default to coding 0 unless the section substantively elaborates on the community as collective.



\*\*Positive examples (CODE 1)\*\*:

\- "Our community thrives on creativity and authentic expression."

\- "We are committed to building a safe space for our diverse community of millions."

\- "TikTok creators form a global network of storytellers."



\*\*Negative examples (CODE 0)\*\*:

\- "All creators must follow our creator code of conduct." → just rule-recipient

\- "We have Community Guidelines to keep TikTok a safe and positive experience." → "Community" in document title only

\- "We do not allow account behaviors that may spam or mislead our community." → community as protection-rationale, not as valued collective



\---



\### A6. Engagement



\*\*Definition (Su \& Chan, 2025)\*\*: The degree to which a platform allows or prohibits interactivity and participation through the platform for certain outcomes.



\*\*Decision rule\*\*: Code 1 ONLY if the section affirmatively describes mechanisms BY WHICH users participate on the platform — posting, livestreaming, sending gifts, earning rewards, monetization tools, FYP eligibility, etc. The section must be about how participation works.



\*\*DO NOT code 1 if\*\*:

\- The section is a content prohibition. Content prohibitions = safety, NOT engagement, even if the prohibited acts (posting, sharing, streaming) are technically participation.

\- The section merely says rules apply to users. That is not about participation mechanisms.

\- The section discusses payment processing details. That is commercial, not engagement.



\*\*Positive examples (CODE 1)\*\*:

\- "Users may post videos up to 10 minutes in length."

\- "Sending virtual gifts is a way to support your favorite creators."

\- "Eligible content may be recommended on the For You feed."

\- "Creators can earn through the Creator Rewards Program."



\*\*Negative examples (CODE 0)\*\*:

\- "Do not post, upload, stream, or share sexually exploitative content." → safety, NOT engagement (it's a prohibition)

\- "These rules apply to everyone and everything on our platform." → not about participation mechanism

\- "It is your responsibility to ensure that you provide your PayPal information correctly." → payment processing, not engagement



\---



\### A7. Protection of Intellectual Property



\*\*Definition (Su \& Chan, 2025)\*\*: The degree to which a platform establishes rules, guidelines, and mechanisms to safeguard the ownership and rights of creators and organizations over their content, ideas, and digital assets, including prohibiting unauthorized use, distribution, and reproduction.



\*\*Decision rule\*\*: Code 1 if the section discusses copyright, trademark, licensing, content ownership, ownership of digital assets, or unauthorized use/reproduction of content.



\*\*DO NOT code 1 if\*\*:

\- The section is about user privacy, not creative ownership.

\- The section is about platform's authority to use content (that overlaps with power; code based on the section's main focus).



\*\*Positive examples (CODE 1)\*\*:

\- "We respect the intellectual property rights of creators."

\- "Do not post content that infringes on copyright."

\- "Diamonds do not constitute property and are not transferable."

\- "The Services and related documentation are 'Commercial Items' under federal regulations."



\*\*Negative examples (CODE 0)\*\*:

\- "We do not allow account behaviors that may spam or mislead our community." → safety, not IP



\---



\### A8. Improvement



\*\*Definition (Su \& Chan, 2025)\*\*: The degree to which a platform strives to improve its available features and become central actors of private and public life.



\*\*Decision rule\*\*: Code 1 if the section describes how the platform is enhancing, expanding, or evolving its features, services, or role in society. Forward-looking language ("we will", "upcoming", "we are working on", "we continually improve") is a key cue.



\*\*DO NOT code 1 if\*\*:

\- The section merely describes existing functionality. ("Users can post videos" = engagement, not improvement.)

\- The section is about updating policy text itself ("we may update these terms"). That is procedural.



\*\*Positive examples (CODE 1)\*\*:

\- "We continually improve our recommendation algorithms."

\- "TikTok is investing in new tools for creators."

\- "Our upcoming Transparency and Accountability Center will offer..."

\- "We are diversifying our recommendations approach."



\*\*Negative examples (CODE 0)\*\*:

\- "We may update these guidelines from time to time." → procedural

\- "Users can post videos." → describes existing functionality



\---



\### A9. Care



\*\*Definition (Su \& Chan, 2025)\*\*: The degree to which a platform provides information about support for users and outlines how users can seek help.



\*\*Decision rule\*\*: Code 1 ONLY if the section directs users to \*\*support resources for distress, harm, vulnerability, or wellbeing\*\* — crisis hotlines, mental health resources, abuse reporting paths, parent guidance for harmful content, eating disorder support, etc.



\*\*DO NOT code 1 if\*\*:

\- The section directs users to general educational/reference materials (Creator Academy, Help Center articles, Safety Center policy explanations). Educational resources ≠ care.

\- The section says "Learn more about \[topic]" without explicit framing around user wellbeing or distress.

\- The section refers to internal report buttons or moderation appeal tools. Those are accountability or engagement, not care.



\*\*Positive examples (CODE 1)\*\*:

\- "If you or someone you know is struggling with thoughts of self-harm, please contact the National Suicide Prevention Lifeline at..."

\- "Resources for parents whose children may have encountered harmful content are available at..."

\- "Users experiencing harassment can find support at our Safe Space hub."



\*\*Negative examples (CODE 0)\*\*:

\- "Learn more about the creator code of conduct in our Creator Academy." → education, NOT care

\- "The Safety Center includes information about our partnerships." → reference, NOT care

\- "Learn more about our approach to safeguarding..." → meta-information, NOT care

\- "Visit our Help Center for FAQs." → operational reference, NOT care



\---



\### A10. Accountability



\*\*Definition (Su \& Chan, 2025)\*\*: The degree to which a platform or users has a mechanism for holding the platform accountable.



\*\*Decision rule\*\*: Code 1 if the section describes formal mechanisms by which the platform commits to transparency, audit, appeal, or external oversight — that is, ways to check on PLATFORM behavior.



\*\*DO NOT code 1 if\*\*:

\- The section is about platform holding USERS accountable (e.g., "we hold users accountable for their content"). That is power, not accountability.

\- The section is about content moderation enforcement. That is power.

\- The section describes user obligations, not platform obligations.



\*\*Positive examples (CODE 1)\*\*:

\- "Users may appeal moderation decisions through our review process."

\- "We publish a quarterly transparency report on content removal."

\- "Our policies are reviewed by an independent advisory council."



\*\*Negative examples (CODE 0)\*\*:

\- "We will remove violating content." → power

\- "You acknowledge that you have no right to receive any income from User Content." → contractual term about user, not accountability mechanism



\---



\## Part B: Cultural Heritage Codes (6 codes, original to this study)



These six codes apply ONLY when a section explicitly engages with cultural, religious, traditional, or indigenous content. Generic mentions of "sensitive content", "misleading content", "misinformation", or "hate speech" without cultural specificity DO NOT trigger any heritage code.



\*\*Hard threshold\*\*: Heritage codes (B1-B6) require at least one of these terms to appear AND be substantively engaged with: religion, religious, sacred, faith, ritual, ceremony, indigenous, tribal, ethnic minority, traditional, heritage, cultural practice, folklore, ancestral, spiritual.



\---



\### B1. Authenticity Claims (Heritage Authenticity)



\*\*Definition\*\*: The platform asserts, evaluates, or governs whether cultural, traditional, or religious content is "authentic", "genuine", "original", or "real" — invoking notions of cultural truthfulness or traditional legitimacy.



\*\*Theoretical anchor\*\*: Smith (2006, \*Uses of Heritage\*) — institutions implicitly define which cultural performances count as "authentic heritage".



\*\*Decision rule\*\*: Code 1 if the section evaluates the legitimacy or authenticity of CULTURAL/TRADITIONAL/RELIGIOUS performances or claims to ethnic/cultural identity.



\*\*DO NOT code 1 if\*\*:

\- The section discusses general misinformation/deepfakes/impersonation without cultural specificity.

\- The section discusses authenticity of accounts (e.g., real-name policies) without cultural framing.



\*\*Positive examples (CODE 1)\*\*:

\- "Content claiming to represent a religious tradition must accurately reflect that tradition's teachings."

\- "We may remove content that misrepresents indigenous cultural practices."



\*\*Negative examples (CODE 0)\*\*:

\- "Misinformation about elections is not allowed." → general, not cultural

\- "Deepfakes of public figures are prohibited." → general, not cultural



\---



\### B2. Religious and Sacred Sensitivity



\*\*Definition\*\*: The platform articulates rules about content depicting, discussing, or engaging with religious figures, sacred objects, religious rituals, or sacred sites.



\*\*Decision rule\*\*: Code 1 ONLY if the section explicitly references religion, religious figures, religious practices, sacred objects, or places of worship in the context of what is allowed or prohibited.



\*\*DO NOT code 1 if\*\*:

\- "Religion" appears only in a list of protected attributes without elaboration (e.g., "race, ethnicity, religion, national origin"). Code 0 unless the section substantively elaborates on religious content.



\*\*Positive examples (CODE 1)\*\*:

\- "Content that disparages religious beliefs or sacred symbols may have its visibility reduced."

\- "We do not allow content that mocks religious figures."



\*\*Negative examples (CODE 0)\*\*:

\- "Hate speech against any group, including based on religion, is prohibited." → list-mention only, no substantive elaboration



\---



\### B3. Indigenous and Minority Cultural Protection



\*\*Definition\*\*: The platform articulates specific protections for indigenous peoples, ethnic minorities, or marginalized cultural communities — recognizing their distinct cultural rights, vulnerabilities, or representation needs.



\*\*Decision rule\*\*: Code 1 if the section explicitly mentions indigenous peoples, ethnic minorities, tribal groups, or specific marginalized cultural communities — and discusses their cultural representation, rights, or appropriation specifically.



\*\*DO NOT code 1 if\*\*:

\- The section discusses general anti-discrimination without indigenous/minority cultural context.

\- The section lists "race, ethnicity" as protected attributes without cultural elaboration.



\*\*Positive examples (CODE 1)\*\*:

\- "We protect content from indigenous creators sharing their cultural heritage."

\- "Cultural appropriation, particularly of indigenous traditions, is not permitted."



\*\*Negative examples (CODE 0)\*\*:

\- "We protect users from harassment based on race or ethnicity." → general anti-discrimination



\---



\### B4. Traditional Craftsmanship and Skill Display



\*\*Definition\*\*: The platform articulates rules or recognition specifically for content depicting traditional crafts, artisanal practices, traditional performance arts, or skill-based heritage practices.



\*\*Decision rule\*\*: Code 1 if the section references traditional crafts, artisanal practices, performance traditions (opera, calligraphy, weaving, traditional medicine), or skill-based cultural practices.



\*\*DO NOT code 1 if\*\*:

\- The section is about creative content in general without traditional/cultural specificity.



\*\*Positive examples (CODE 1)\*\*:

\- "Content showcasing traditional crafts is welcome on our platform."

\- "Demonstrations of traditional medicine practices must include disclaimers."



\---



\### B5. Commercialization of Culture



\*\*Definition\*\*: The platform articulates rules about the monetization, commercial use, or commodification of cultural, traditional, or religious content.



\*\*Decision rule\*\*: Code 1 ONLY if the section discusses monetization, virtual gifts, advertising, or commercial use AND the cultural/traditional/religious framing is explicit.



\*\*DO NOT code 1 if\*\*:

\- The section is about general monetization rules.

\- The section mentions "sensitive content categories" without naming culture/religion/tradition.



\*\*Positive examples (CODE 1)\*\*:

\- "Content depicting religious ceremonies is not eligible for virtual gift monetization."

\- "Sponsored content involving sacred objects requires disclosure."



\---



\### B6. AI-Generated Cultural Content



\*\*Definition\*\*: The platform articulates rules about AI-generated or AI-modified content depicting cultural, traditional, religious, or heritage subject matter.



\*\*Decision rule\*\*: Code 1 ONLY if the section discusses AI-generated content AND specifies cultural/traditional/religious/heritage subject matter.



\*\*DO NOT code 1 if\*\*:

\- The section is about general AI labeling or general deepfake policy.

\- The section is about platform's own use of AI for moderation.



\*\*Positive examples (CODE 1)\*\*:

\- "AI-generated content depicting religious figures must be clearly labeled."

\- "Synthetic media imitating traditional cultural performances is subject to additional review."



\*\*Negative examples (CODE 0)\*\*:

\- "Deepfakes are prohibited." → general AI policy

\- "AI-generated content must be labeled." → general AI labeling



\---



\## Part C: Coding Procedure



1\. Read the entire section (3 sentences) before coding any code.

2\. Code each code independently. A section can have multiple 1s.

3\. \*\*When in doubt, code 0\*\*. False negatives are preferred. This applies especially to:

&#x20;  - Power vs Safety (most prohibitions are safety, not power)

&#x20;  - Engagement vs Safety (most "do not post X" rules are safety, not engagement)

&#x20;  - Care vs general references (educational links are not care)

&#x20;  - Community (most "creators" mentions are not community)

4\. Heritage codes require explicit cultural/religious/traditional language. Generic language never triggers heritage codes.



\---



\## Part D: Quick Reference — Anti-patterns Summary



| Pattern | Wrong code | Right code |

|---|---|---|

| "We do not permit X" | power, engagement | safety only |

| "Subject to the following terms" | power | (TOS convention, often nothing) |

| "All sales are final" | power | (commercial, often nothing) |

| "Learn more in \[Help/Creator Academy/Safety Center]" | care | (educational, often nothing) |

| "Mention of 'creators' as audience" | community | (just rule recipient) |

| "Community Guidelines" as title | community | (title only) |

| "Religion" in list of protected attributes | B2 | safety only |

| "Misinformation about elections" | B1 | safety only |

| "Deepfakes prohibited" | B6 | safety only |

