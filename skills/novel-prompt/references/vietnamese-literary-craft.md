# Vietnamese literary craft and scene-dependent address

Use when translating novels into Vietnamese. Distill these rules into the `STYLE`, `CHARACTER VOICE AND PRONOUNS`, and `IDIOMS, SLANG, PROFANITY, ONOMATOPOEIA` sections of Glossarion's combined `system_prompt.md` so the translation model executes them directly without needing external skills at runtime.

## 1. Priority: Tín before Đạt and Nhã

- **Tín:** preserve source facts, actors, recipients, negation, modality/certainty, chronology, identity, intentions, point of view, emotional intensity, meaningful repetition, and the exact timing of dialogue/action beats.
- **Đạt:** translate **sense-by-sense**, not English word order. Use idiomatic Vietnamese clause order and specific verbs without changing any source proposition or inventing implied feelings.
- **Nhã:** preserve the **author's** voice, genre, imagery, understatement, tension, tempo, and humor. Do not make minimal writing flowery, modern banter archaic, or Murim dialogue uniformly ceremonial.

## 2. Vietnamese syntax and anti-translationese mechanics (for `STYLE`)

Bake these high-leverage structural rules into `STYLE` in `system_prompt.md`:

- **Topic–Comment (`Đề–Thuyết`) and Serial Verbs (`Chuỗi động từ nối tiếp`):**
  - Front-load time, place, or condition as the Topic (`Đề`) before the main action or observation (`Thuyết`) when it improves flow (e.g., *“The chief always complained like that when drunk”* → *“Mỗi khi say khướt, trưởng làng bao giờ cũng càu nhàu như thế”*).
  - For consecutive actions by the same actor, use Vietnamese serial verb chains without mechanical conjunctions (`"và sau đó"`, `"rồi thì"`) and omit repeated subjects once the actor is unambiguous (*“He stood up, walked to the window, and looked out”* → *“Anh đứng dậy, bước đến bên cửa sổ, nhìn ra ngoài”*).
- **Semantic aspect over mechanical tense (`đã / đang / sẽ`):**
  - Vietnamese encodes time via context and aspect, not verb conjugation. Once past timeframe is established, drop mechanical `"đã"` on subsequent verbs; use `"đã"` only for completed contrast, emotional distance, or shifts in sequence.
  - Do not render every English `was/were + -ing` as `"đang"` (never use `"đang"` for habits or states) or every conversational `will` as `"sẽ"` (*“I'll go home”* → *“Tôi về nhé”*). Choose precise aspect markers (`vừa`, `mới`, `từng`, `đã từng`, `sắp`, `hay`, `thường`) and correlative pairs (`đang... thì`, `vừa... xong`, `chưa... đã`, `mới... đã`).
- **Directional verb complements (`Bổ ngữ chỉ hướng`):**
  - Attach natural physical or figurative directional complements (`ra, vào, lên, xuống, đi, lại, về, sang, qua, tới/đến`) to motion, posture, gaze, and emotion verbs so clauses do not sound clipped (*“ngã xuống”*, *“rời đi”*, *“nhìn ra/nhìn vào/ngước lên/cúi xuống”*, *“giọng trầm xuống”*, *“cơn giận bùng lên”*, *“chìm vào u uất”*).
- **Anti-nominalization, active voice, and expressive classifiers:**
  - Replace nominalizations (`"sự/việc + V"`), weak verb wrappers (`"thực hiện việc"`, `"tiến hành"`, `"đưa ra sự"`), and mechanical `-ly` calques (`"một cách + adj"`) with direct verbs, specific adverbs, or fitting từ láy / từ tượng hình / từ tượng thanh.
  - When keeping abstract emotion/state nouns, prefer expressive classifiers (`nỗi, niềm, mối, cơn, luồng, tấm`) over cold `"sự"` (*“nỗi buồn”*, *“cơn giận”*, *“mối lo”*).
  - Convert English `"bị/được ... bởi"` passives into active clauses or Topic–Comment sentences (*“Lời anh khiến cô xúc động”* rather than *“Cô ấy bị xúc động bởi lời của anh ấy”*). Retain `"bị"` (adverse) or `"được"` (favorable) only when narrative focus belongs on the affected person.
- **Possessive pruning and anti-synonym-stacking:**
  - Drop redundant `"của anh ấy / cô ấy / hắn / cậu ấy / nó"` on body parts, clothing, faculties, or held weapons when ownership is obvious, or use reflexive `"mình"` (*“nắm chặt chuôi kiếm”*, *“nhíu mày”*, *“trong lòng”*). Use `classifier + noun` anaphora (*“vị mục sư”*, *“người hiệp sĩ”*) naturally instead of repeating third-person pronouns in every clause.
  - Split overloaded English relative/participle chains (`who/which/that`, `-ing`) into crisp Vietnamese clauses; use abrupt short sentences for impact beats. Avoid stacking two synonymous two-syllable compounds side by side (*“xấu xí gớm ghiếc”*, *“chần chừ ngần ngại”*) unless building deliberate ascending rhythm.

## 3. Dialogue cadence, modal particles, and scene-dependent xưng hô

- **Spoken dialogue vs. narration:** Dialogue must sound spoken aloud by that specific character, not like written narration. Use natural clause length, ellipsis, interjections, and sentence-final modal particles (`à, ừ, nhỉ, nhé, đấy, thôi, mà, chứ, cơ, hả, sao, đi, đâu, ạ`) matched to hierarchy, intimacy, and emotional state (*“Em nghĩ không ổn đâu”* rather than *“Tôi không nghĩ đó là một ý tưởng tốt”*).
- **Bidirectional scene-local address (`A → B` and `B → A`):** Silently inspect each dialogue turn: speaker, addressee, witnesses, confirmed age/rank/generation, kinship, formal vs. private setting, intimacy, contempt, disguise, speaker knowledge, and timeline. Keep register stable within an exchange unless a motivated shift occurs. Narrator labels never dictate self-address.
- **Genre-appropriate pronouns:** Murim/wuxia may use `"ta/ngươi"`, `"tại hạ"`, `"tiền bối"`, `"sư phụ"`, `"huynh/đệ"`, while Western/modern settings use appropriate feudal, familial, or social pairs (`"cha/mẹ - con"`, `"tôi - ngài/cậu/anh/cô"`, `"ta - ngươi/khanh"`). `"Hắn"`, `"gã"`, `"ả"`, `"mụ"`, `"lão"`, `"y"` carry viewpoint or attitude—never assign them mechanically by gender alone.
- **Glossary separation:** The glossary records stable honorific titles and verified directional relationships only when description metadata is enabled; it does **not** store fixed pronoun pairs.

## 4. Glossarion contract and final QA

Keep **exact** section-heading lines `STYLE` and `CHARACTER VOICE AND PRONOUNS`, plus the normal profile, placeholder, HTML, split-marker, and glossary format contracts. Put style rules **under** these headings, not in renamed headings. Verify fluent Vietnamese **without** added information, lost action beats, imposed contempt, forced meters, genre drift, or sound substitutions unrelated to the scene.
