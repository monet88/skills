# Vietnamese Literary Craft and Scene-Dependent Address

Distill these mechanics directly into `STYLE`, `CHARACTER VOICE AND PRONOUNS`, and `IDIOMS, SLANG, PROFANITY, ONOMATOPOEIA` in `system_prompt.md` — the translation model at runtime sees only `system_prompt.md`.

## 1. Priority: Tín before Đạt and Nhã

- **Tín (Accuracy):** Preserve source facts, actors, recipients, negations (`không/chưa/chẳng/đừng`), modality/certainty, chronology, exact numbers/units, POV, emotional force, deliberate repetition, and dialogue/action beat timing.
- **Đạt (Naturalness):** Translate sense-by-sense using idiomatic Vietnamese clause structure and direct verbs without adding implied feelings or dropping propositions.
- **Nhã (Voice fidelity):** Match the **author's** tone, genre, imagery, restraint, tempo, and humor. Keep crisp prose crisp, modern banter modern, and classical narration composed without forced flowery padding.

## 2. Core Vietnamese Syntax & Anti-Translationese (for `STYLE`)

1. **Topic–Comment (`Đề–Thuyết`) & Serial Verb Chains (`Chuỗi động từ nối tiếp`):**
   - Front-load time, place, or condition as Topic (`Đề`) before action (`Thuyết`) when natural (*"The chief always complained like that when drunk"* → *"Mỗi khi say khướt, trưởng làng bao giờ cũng càu nhàu như thế"*).
   - Chain consecutive same-subject actions directly without mechanical `"và sau đó"` / `"rồi thì"`, dropping repeated subjects once clear (*"He stood up, walked to the window, and looked out"* → *"Anh đứng dậy, bước đến bên cửa sổ, nhìn ra ngoài"*).
   - Split overloaded English relative/participle chains (`who/which/that`, `-ing`) into crisp Vietnamese clauses without shattering cohesive paragraphs into choppy 1–2 sentence lines.
2. **Semantic Aspect over Mechanical Tense (`đã / đang / sẽ`):**
   - Once past timeframe is clear, drop repetitive `"đã"` on subsequent verbs; keep `"đã"` for completed contrast, distance, or sequence shifts.
   - Avoid translating habitual/stative `was/were + -ing` as `"đang"` or conversational `will` as `"sẽ"` (*"I'll head home"* → *"Tôi về nhé"*). Prefer exact aspect markers (`vừa`, `mới`, `từng`, `sắp`, `hay`, `thường`) and correlatives (`đang... thì`, `vừa... xong`, `chưa... đã`, `mới... đã`).
3. **Directional Verb Complements (`Bổ ngữ chỉ hướng`):**
   - Attach natural directional complements (`ra, vào, lên, xuống, đi, lại, về, sang, qua, tới/đến`) to motion, posture, gaze, and emotion verbs (*"ngã xuống"*, *"rời đi"*, *"ngước lên"*, *"giọng trầm xuống"*, *"cơn giận bùng lên"*).
4. **Active Direct Verbs, Classifiers & Anti-Slop:**
   - Replace nominalizations (`"sự/việc + V"`), weak verb wrappers (`"thực hiện việc"`, `"tiến hành"`, `"đưa ra sự"`), and `-ly` calques (`"một cách + adj"`) with direct verbs, specific adverbs, or fitting từ láy / từ tượng hình / từ tượng thanh.
   - Prefer expressive classifiers (`nỗi, niềm, mối, cơn, luồng, tấm`) over cold `"sự"` (*"nỗi buồn"*, *"cơn giận"*, *"mối lo"*).
   - Convert `"bị/được ... bởi"` passives to active or Topic–Comment clauses unless narrative focus belongs on the affected party (*"The blade was shattered by his palm"* → *"Một chưởng của hắn đánh nát thanh đao"*).
   - Drop redundant possessives (`"của anh ấy/cô ấy/hắn/nó"`) on body parts, clothing, faculties, or held weapons (`"nắm chặt chuôi kiếm"`, `"nhíu mày"`, `"trong lòng"`), and use `classifier + noun` anaphora (`"vị trưởng lão"`, `"người hiệp sĩ"`) rather than repeating pronouns every clause.
   - Avoid stacking synonymous two-syllable compounds mechanically (`"xấu xí gớm ghiếc"`, `"chần chừ ngần ngại"`) and repetitive AI templates (`"không phải..., mà là..."`, monotonic time-marker openers).

## 3. Dialogue Cadence, Action Beats, Monologue & Scene-Local `Xưng Hô`

- **Spoken dialogue vs. narration vs. internal monologue:**
  - Dialogue must sound spoken by that character: natural clause length, ellipses, interjections, and sentence-final modal particles (`à, ừ, nhỉ, nhé, đấy, thôi, mà, chứ, cơ, hả, sao, đâu, ạ`) matched to hierarchy, closeness, and mood.
  - **Dialogue action beats & speech verbs:** Replace mechanical `"hắn nói" / "cô hỏi" / "anh đáp"` loops with sharp contextual speech verbs (`đáp gọn`, `hỏi khẽ`, `hừ lạnh`, `cười khẩy`, `quát lên`, `lẩm bẩm`) or omit redundant `"nói"` when an adjacent action beat already identifies the speaker.
  - Keep internal monologue (free indirect speech / inner thoughts) distinct from spoken dialogue — matching the character's unguarded voice without forcing polite spoken markers into silent thought.
- **Bidirectional scene-local address (`A → B` and `B → A`):**
  - Silently check every dialogue turn independently in both directions: speaker, addressee, witnesses, confirmed age/rank/generation, kinship, public vs. private setting, intimacy/contempt, disguise, speaker knowledge, and timeline stage.
  - Keep register stable within a scene unless the source motivates a shift. Use any supplied Glossarion chapter-gated `relations` column as supporting evidence without letting later-chapter knowledge leak into earlier scenes.
  - Match pronoun family to the setting: Murim/wuxia/xianxia (`ta/ngươi`, `tại hạ/các hạ`, `tiền bối/vãn bối`, `sư phụ/đệ tử`, `huynh/tỷ/đệ/muội`) versus feudal/Western/modern (`cha/mẹ–con`, `tôi–ngài/cậu/anh/chị/em`, `mày–tao`). Never apply a global ban on neutral/family pronouns (`cha/mẹ/con`, `tôi`, `mình`) where source context calls for them; reserve `hắn/gã/ả/mụ/lão/y` for fitting viewpoint/distance rather than assigning mechanically by gender.
