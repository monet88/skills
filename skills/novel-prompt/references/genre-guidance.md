# Genre Guidance

Use only the sections supported by the supplied chapters. Do not import genre conventions that the text does not establish.

## Fantasy / Western-style fantasy

Prioritize:
- races/species/bloodlines
- kingdoms/empires/territories
- noble, military, religious, and organizational ranks
- factions, guilds, knight orders, churches, academies
- magic systems and supernatural mechanisms
- spells, skills, abilities, traits, artifacts, relics, monsters
- technology and magitech when present

Style guardrail: fantasy does not automatically require archaic, wuxia, xianxia, or ornate Sino-Vietnamese prose.


## English-led translations with original-script residue

Apply `multilingual-source-handling.md` whenever the supplied text is mostly English but still contains untranslated source-language fragments. The translator must process the whole linguistic mixture, not only the English layer.

- Korean-origin: do not leave Hangul raw. For Sino-Korean Murim terminology, convert identifiable Hangul forms to Vietnamese Hán-Việt; e.g. `냉혈아수라왕` → `Lãnh Huyết A Tu La Vương`.
- Chinese-origin: translate ordinary Hanzi prose; Hán-Việt-localize recurring canonical entities in the Sino-influenced genre branch.
- Japanese-origin: translate Japanese prose and transliterate/localize names and terms according to Japanese/project convention; do not leave Kanji/Kana raw merely because the surrounding source is English.
- If origin is materially uncertain and changes these rules, ask the user whether the novel is Korean, Chinese, Japanese, or another origin before drafting the prompt pack.

## Vietnamese Hán-Việt localization for Sino-influenced martial genres

Apply this branch when the target language is Vietnamese and the novel is Murim, wuxia/võ hiệp, xianxia/tiên hiệp, xuanhuan/huyền huyễn, or another clearly Chinese/Sino-Korean martial-cultivation tradition.

Default naming policy:
- Hán-Việt-localize reusable proper nouns instead of leaving them as raw romanization: personal names, surnames, martial epithets, sects, clans, families, alliances, cults, palaces, castles, techniques, manuals, formations, realms, ranks, constitutions, named items, herbs, pills, weapons, mountains, peaks, cities, counties, provinces, and other recurring places.
- `raw_name` may preserve the source spelling for glossary matching, but it is not the preferred Vietnamese display form. `translated_name` and running translation should use the Hán-Việt/localized Vietnamese form.
- Evidence priority: (1) explicit Hanzi/Hanja in the source, (2) user-supplied or established glossary canon, (3) official/explicit semantic gloss in the source, (4) a strongly supported Sino-Korean/Sino-Chinese reading, (5) a stable project-local Hán-Việt localization when the original characters cannot be recovered.
- If step 5 is necessary, prefer consistency and Vietnamese genre readability over preserving romanization. Do not state or imply that the inferred characters/etymology are historically certain. If metadata fields exist, note that the Hán-Việt form is a project localization inferred from romanization/context.
- **Dịch 100% Hán-Việt** for recurring Sino-origin names in this branch: convert all still-romanized Romaja/pinyin/English-rendered canonical names to a complete Hán-Việt Vietnamese display form instead of leaving partial romanization behind.
- Never output hybrid half-localized names such as `Dư-min` or `Thủy-ryun`. A Hán-Việt name must be complete across the whole canonical name; replace romanization hyphens with normal word spacing only after every syllable/name component has been localized. Do not merely delete the hyphen while keeping `min`, `ryun`, or another romanized remainder.
- Apply the same rule to English-rendered Sino-origin canonical names: translate/localize the full name/title to Hán-Việt when the source/canon/context establishes that it is a Sino-origin entity.
- **English-calqued proper noun reconstruction (Phục nguyên Danh từ riêng tiếng Anh sang Từ ghép Hán-Việt cô đọng 2–4 âm tiết):** In English translations of Murim/wuxia/xianxia/historical works, proper nouns for pavilions, brothels, inns, halls, towers, fortresses, valleys, sects, formations, techniques, realms, items, and martial epithets are frequently rendered in English words (`Dusk Sentiments Pavilion`, `Mandarin Duck Pavilion`, `Bowed Pavilion`, `Dog Fortress`, `Lightning Strike`). Always reconstruct these into concise **2–4 syllable Head-Final Sino-Vietnamese (Hán-Việt) compounds** (`[Modifier Hán-Việt] + [Head Noun Hán-Việt: Các / Lâu / Điện / Đường / Viện / Hiên / Trại / Bảo / Cốc / Môn / Phái / Bang / Hội / Trận / Pháp / Quyết / Công / Kích / Trảm]`, e.g. `Dusk Sentiments Pavilion` → `Mộ Tình Các` / `Tịch Tình Các`, `Bowed Pavilion` → `Khung Lâu`, `Dog Fortress` → `Khuyển Trại`, `Lightning Strike` → `Lôi Kích`). Never translate them word-by-word in modern Head-Initial vernacular Vietnamese order (`Lâu Các Tinh Thần Buổi Tối`, `Chó Trại`, `Sét Đánh`), and never include parenthetical glosses inside `translated_name` (`Khung Lâu (Lầu Cúi Đầu)`). Clarify that "do not fabricate Hanja/Hanzi" only forbids inventing CJK characters or claiming verified historical etymology—it never forbids translating English-calqued proper nouns into Sino-Vietnamese compounds.
- **Historical brothel / courtesan / common role terms:** Never extract generic descriptive role phrases (`leading courtesan`, `oldest courtesan`, `brothel keeper`, `innkeeper`, `guard`) as `character` rows. In historical/Murim brothel (`thanh lâu / kỹ viện`) contexts, translate `courtesan` as `kỹ nữ / ca kỹ / thanh y / hoa khôi` (`leading courtesan` → `hoa khôi đứng đầu / kỹ nữ đứng đầu`), never `y quan`.
- **Standalone bare titles / honorifics rejection (Murim / wuxia / xianxia):** Do not extract bare standalone titles or institutional roles (`Sect Leader`, `Cult Leader`, `Alliance Leader`, `Patriarch`, `Matriarch`, `Elder`, `Grand Elder`, `Pavilion Master`, `Hall Master`, `Peak Master`, `Young Master`, `Young Lady`, `Master`, `Senior Brother`, `Junior Sister`, `Lord`) as independent glossary rows unless bound to a specific proper noun or organization (`Mount Hua Sect Leader` → `Chưởng môn Hoa Sơn`, `Blood Demon` → `Huyết Ma`). Standalone titles vary by organization (`Chưởng môn` for orthodox sects, `Môn chủ` for gates/schools, `Giáo chủ` for cults, `Gia chủ` for clans, `Bang chủ` for gangs) and must be resolved in scene context rather than locked globally in the glossary.
- **Bracketed CJK / Hanja glosses, CJK verses, and trailing watermarks (Murim / wuxia / xianxia):**
  - When an English/romanized term is followed by raw Hanja/Hanzi/Hangul in parentheses or brackets (`Mental Imagery Sparring [心像比武]`, `Peerless Prodigy (千古奇才)`), localize the term into Vietnamese/Hán-Việt and **strip the bracketed CJK/Hangul gloss** so zero raw CJK characters remain in reader-facing Vietnamese prose (preventing QA `Chinese_text_found` failures).
  - When standalone CJK poems, chants, martial formulas, or stele inscriptions appear in the source, render them into full Hán-Việt or natural Vietnamese verse rather than leaving raw CJK characters.
  - If a chapter ends with a standalone romanized or translated novel-title watermark tacked onto the final sentence/paragraph without grammatical connection (e.g., `Chang-gwi-musang`), omit the watermark rather than translating it into the prose.
- **Canonical Sino-Korean (Romaja) & Sino-Chinese (Pinyin) → Hán-Việt Anchor Table (for Murim / wuxia / xianxia):**
  - **Compound Surnames & Great Clans (Thế Gia / Họ Kép — watch for distorted English-from-Korean spellings):**
    - `Namgung / Nangong` → `Nam Cung` (`Namgung Clan` → `Nam Cung Thế Gia`)
    - `Bukgung / Baek Gung / Baekgung / Beigong` → `Bắc Cung` (English translations of Korean Murim frequently distort `Bukgung` 北宮 into `Baek Gung`; always render the two-syllable surname as `Bắc Cung`, never `Bạch Cung`)
    - `Moyong / Mo-yong / Murong` → `Mộ Dung`
    - `Jegal / Zhuge` → `Gia Cát`
    - `Sacheon Tang / Dang / Tang Clan` → `Tứ Xuyên Đường Môn` (`Dang` / `Tang` surname → `Đường`)
    - `Habuk Paeng / Peng` → `Hà Bắc Bành Gia` (`Paeng` / `Peng` surname → `Bành`)
    - `Hwangbo / Huangfu` → `Hoàng Phủ`
    - `Danmok / Duanmu` → `Đan Mộc`
    - `Seomun / Ximen` → `Tây Môn`
    - `Dokgo / Dugu` → `Độc Cô`
    - `Dongbang / Dongfang` → `Đông Phương`
    - `Sama / Sima` → `Tư Mã`
    - `Sanggwan / Shangguan` → `Thượng Quan`
    - `Ohyang / Ouyang` → `Âu Dương`
    - `Hagun / Xiahoudun / Xiahou` → `Hạ Hầu`
    - `Wi / Wei` → `Ngụy`; `Baek / Bai` (single surname) → `Bạch`; `Cheon / Tian` → `Thiên`; `Jin / Chen / Qin` → `Trần / Tần`
  - **Nine Sects One Gang & Major Factions (Cửu Phái Nhất Bang & Tứ Đại Thế Lực):**
    - `Sorim / Shaolin` → `Thiếu Lâm`; `Mudang / Wudang` → `Võ Đang`; `Hwasan / Mount Hua / Huashan` → `Hoa Sơn`; `Ami / Emei` → `Nga Mi`; `Gonryun / Kunlun` → `Côn Luân`; `Jeomchang / Diancang` → `Điểm Thương`; `Cheongseong / Qingcheng` → `Thanh Thành`; `Kongtong / Gongdong` → `Không Động`; `Jongnam / Zhongnan` → `Chung Nam`; `Haenam / Hainan` → `Hải Nam`; `Gaebang / Beggars Sect / Beggars' Union` → `Cái Bang`
    - `Murim Meng / Murim Alliance / Martial Arts Alliance` → `Võ Lâm Minh` (`Alliance Leader / Mengju` → `Minh chủ`)
    - `Jeongpa / Orthodox Faction / Righteous Faction` → `Chính Phái / Bạch Đạo`
    - `Sapa / Unorthodox Faction / Evil Faction` → `Tà Phái / Hắc Đạo`; `Hao Mun / Haomun / Lower District Sect` → `Hạo Môn`
    - `Magyo / Cheonmagyo / Heavenly Demon Divine Cult / Demonic Cult` → `Ma Giáo / Thiên Ma Thần Giáo` (`Cheonma / Heavenly Demon` → `Thiên Ma`)
    - `Hyeolgyo / Blood Cult` → `Huyết Giáo` (`Blood Demon / Hyeolma` → `Huyết Ma`)
    - `Saewoe / Outer Regions`: `Bukhae Binggung / North Sea Ice Palace` → `Bắc Hải Băng Cung`; `Namman Yasugung / Beast Palace` → `Nam Man Dã Thú Cung`; `Potala Palace` → `Bố Đạt La Cung`
- **Contextual Sino-Korean name check (evidence-first):** For a character rendered as an unhyphenated English/Romaja name, a single name without a family name, or a minority/borderland name:
  1. **Verify the input identity:** find the actual Hangul/Hanja spelling, source-backed aliases, and approved project canon. Do not reverse-engineer one supposed Hangul spelling from English letters alone; English romanization may merge syllables or reflect a non-Korean name.
  2. **Confirm the source tradition:** a minority or frontier character is not automatically Sino-origin. If a Sino-Korean etymology is confirmed, look up compatible Hanja readings and produce one complete, consistent Hán-Việt name. Never invent a Han surname or conflate the name with a title.
  3. **Fail conservatively on ambiguity:** Hanja are not determined by Hangul sound alone. Do not construct historical-looking characters or force a Chinese phonetic bridge merely because a raw name happens to be a common Vietnamese word. When source evidence cannot establish the mapping, keep the existing user-approved form or a clearly provisional project convention, flag uncertainty in optional description, and avoid claiming an original-character reading.
  4. **Maintain identity:** preserve useful raw Romaja/Hangul/Hanja variants only as verified matching metadata, and do not create multiple character rows for one person.
- Do not mix raw romanized names and Hán-Việt names for the same entity after a canonical Vietnamese form has been chosen.
- User-supplied canon overrides the default localization policy. If the user explicitly requests raw names, preserve them.

## Murim / martial-world fiction

Prioritize:
- sect vs clan vs family vs martial family vs alliance vs cult
- orthodox/unorthodox/demonic faction distinctions
- master-disciple and generation hierarchy
- internal energy, qi/true qi, dantian, meridians, acupoints, circulation
- martial realms/stages/rankings
- sword/saber/spear/fist/palm/finger/claw arts
- movement arts, footwork, lightness skills, internal/external arts
- martial manuals, pills, poisons, herbs, hidden weapons
- martial epithets, titles, and formal ranks

Style guardrail: do not automatically introduce xianxia concepts such as spiritual roots, Golden Core, Nascent Soul, heavenly tribulation, ascension, or immortal realms unless the source explicitly has them.

For Vietnamese output, apply the Hán-Việt localization branch above even when the source uses romanized Korean names. Do not leave names raw merely because Hanja is absent; use a stable project-local Hán-Việt form and mark uncertainty in metadata rather than asserting invented Hanja as fact.

Canonical Korean Murim Realms & Core Martial Terms (when present in the source):
- **Standard Martial Realms (Thang cảnh giới võ học Murim chuẩn):**
  - `Third-rate / Tam lưu (삼류 - Samryu)` → `Tam Lưu`
  - `Second-rate / Nhị lưu (이류 - Iryu)` → `Nhị Lưu`
  - `First-rate / Nhất lưu (일류 - Ilryu)` → `Nhất Lưu`
  - `Peak / Climax / Master (절정 - Jeoljeong)` → `Tuyệt Đỉnh` (sub-stages: `Sơ kỳ / Trung kỳ / Hậu kỳ / Đỉnh phong` or `Tiểu thành / Đại thành / Viên mãn` as evidenced)
  - `Transcendent / Super-Peak / Supreme / Grandmaster (초절정 - Chojeoljeong)` → `Siêu Tuyệt Đỉnh` (or `Siêu Phàm` when the source contrasts mortal vs. transcendent)
  - `Unrestrained / Harmony / Supreme Realm (화경 - Hwagyeong)` → `Hóa Cảnh`
  - `Mystic / Profound / Dark Realm (현경 - Hyeongyeong)` → `Huyền Cảnh`
  - `Life and Death Boundary (생사경 - Saengsagyeong)` → `Sinh Tử Cảnh`
  - `Natural Realm / Unity with Nature (자연경 - Jayeongyeong)` → `Tự Nhiên Cảnh`
  - `Void Realm / Return to Origin (공경 / 반박귀진)` → `Không Cảnh / Phản Phác Quy Chân`
- **Core Martial Terminology (Thuật ngữ võ học cốt lõi):**
  - `Naegong / Inner Qi / Internal Energy` → `Nội công / Nội lực`; `Oegong / External Arts` → `Ngoại công`; `Jingi / True Qi` → `Chân khí`; `Ganggi / Enhanced Aura / Astral Qi` → `Cương khí`; `Geomgi / Sword Qi` → `Kiếm khí`; `Geomgang / Sword Aura / Sword Energy` → `Kiếm cương`; `Geomsa / Sword Thread` → `Kiếm ti`; `Simgeom / Mind Sword` → `Tâm kiếm`; `Hogyeongganggi / Protective Ganggi` → `Hộ thể cương khí`
  - `Gyeonggong / Lightness Skill` → `Khinh công`; `Bobeop / Footwork` → `Bộ pháp`; `Sinbeop / Movement Art` → `Thân pháp`; `Simbeop / Mind Method / Heart Method` → `Tâm pháp`; `Gu-gyeol / Mantra / Formula` → `Khẩu quyết`; `Chohyeok / Form / Move` → `Chiêu thức`
  - `Danjeon / Elixir Field` → `Đan điền` (`Thượng / Trung / Hạ đan điền`); `Gyeongmaek / Meridians` → `Kinh mạch`; `Hyeoldo / Acupoints` → `Huyệt đạo`; `Im-Dok Yangmaek / Conception and Governing Vessels` → `Nhâm Đốc nhị mạch`; `Juhwa-ipma / Qi Deviation` → `Tẩu hỏa nhập ma`; `Hwangoltaltae / Shedding Mortality` → `Hoàn cốt thoát thai`; `Bongmun / Sealing the Sect` → `Phong môn`; `Pae-gong / Crippling Martial Arts` → `Phế võ công`

Glossary extraction/refinement emphasis for Korean Murim when supported by the sample:
- canonical full personal names plus confirmed Hangul/Hanja/Romaja/English aliases
- stable titles, epithets, academy/sect/clan ranks, and reusable master-disciple/senior-junior forms of address
- sect vs clan vs family vs martial family vs alliance vs cult; academy, hall, pavilion, palace, gang, government office, and similar institutions only when actually present
- Orthodox/Unorthodox/Demonic and other source-established faction distinctions
- internal energy/true qi, dantian, meridians, acupoints, circulation, internal/external arts, movement arts, footwork, lightness skills, weapon arts, named arts/forms/ultimate techniques, realms/ranks
- manuals, medicines, pills, poisons, herbs, hidden weapons, formations, special constitutions, recurring weapons/items/locations
- do not extract ordinary pronouns or every conversational kinship word as glossary entries; retain only stable reusable forms of address/titles whose translation consistency matters

Murim Vietnamese dialogue may use `ta/ngươi`, `tại hạ`, `sư phụ`, `huynh/đệ`, `lão`, `nàng` **when the character and moment warrant them**. Do not apply one courtly or hostile register to every speaker: family intimacy, child/parent speech, casual banter, rank reversals, apparent versus actual seniority, hidden identities and a narrator with a different voice all require separate analysis. Avoid a global ban on `tôi`, `mình`, `cha/mẹ/con` or all neutral third-person terms; choose according to demonstrated source social context. Use `hắn/gã/ả` only when their distance or disparagement is consistent with the viewpoint. Do not let formal Murim vocabulary make ordinary dialogue wooden.

## Wuxia / võ hiệp

Prioritize:
- jianghu/võ lâm social hierarchy, sects, clans, escorts, guilds, courts, and regional powers
- internal energy, meridians, acupoints, lightness skills, weapon arts, manuals, poisons, hidden weapons, formations, and martial epithets
- master-disciple, senior-junior, sworn-family, clan, and official forms of address

For Vietnamese output, use Hán-Việt naming aggressively and consistently. Raw pinyin/romanization should not remain as the default display form for recurring Sino-origin proper nouns.

Glossary extraction/refinement emphasis for Chinese wuxia when supported by the sample:
- canonical Chinese names, compound surnames, epithets, official/clan/sect titles, ranks, and reusable forms of address
- jianghu/võ lâm institutions such as sects, clans, martial families, escort agencies, guilds, alliances, courts, halls, pavilions, palaces, gangs, manors, fortresses, and government offices as distinct categories where the source distinguishes them
- internal energy/true qi, meridians, acupoints, internal/external arts, movement arts, footwork, lightness skills, weapon arts, named techniques/forms, manuals, poisons, hidden weapons, formations, realms/ranks, medicines/items/locations
- preserve role distinctions such as sư phụ/sư huynh/sư tỷ/sư đệ/sư muội, trưởng lão, chưởng môn, môn chủ, giáo chủ, minh chủ, gia chủ/tộc trưởng, đường chủ/các chủ/cung chủ/bang chủ only when the source identity/role supports them; do not mechanically map every English `master`, `lord`, `senior`, `teacher`, or `leader` to one fixed term
- treat Hán-Việt terms as canonical only when supported by Hanzi/canon/context; do not invent source characters as historical fact

## Xianxia / cultivation

Prioritize only source-established concepts such as:
- qi/spiritual energy systems
- dantian/meridians if present
- cultivation methods and Dao concepts
- realms/stages/breakthroughs
- spiritual roots, cores, souls, tribulations, ascension only when actually present
- sect hierarchy and cultivation titles
- pills, talismans, formations, artifacts, spirit stones, herbs, beasts

Keep distinct source terms distinct; do not flatten all progression concepts into generic "cảnh giới" if the system differentiates them. For Vietnamese output, apply the Hán-Việt localization branch to names, sects, Daoist titles, techniques, realms, artifacts, formations, pills, herbs, locations, and other recurring Sino-origin entities.

Canonical Xianxia / Tiên Hiệp Realms & Core Terms (when present in the source):
- **Standard Cultivation Realms (Thang cảnh giới tu tiên chuẩn):**
  - `Qi Condensation / Qi Refining (Lianqi)` → `Luyện Khí kỳ` (`Tầng 1–13` or `Sơ / Trung / Hậu kỳ / Đại viên mãn`)
  - `Foundation Establishment (Zhuji)` → `Trúc Cơ kỳ`
  - `Core Formation / Golden Core (Jiedan / Jindan)` → `Kết Đan / Kim Đan kỳ`
  - `Nascent Soul (Yuanying)` → `Nguyên Anh kỳ`
  - `Soul Formation / Spirit Severing / Deity Transformation (Huashen)` → `Hóa Thần kỳ`
  - `Void Refining / Spatial Tempering (Lianxu)` → `Luyện Hư kỳ`
  - `Body Integration / Conjoining (Heti)` → `Hợp Thể kỳ`
  - `Mahayana / Great Vehicle (Dacheng)` → `Đại Thừa kỳ`
  - `Tribulation Transcendence (Dujie)` → `Độ Kiếp kỳ`
  - `Immortal Realms`: `Loose Immortal` → `Tán Tiên`; `Earth Immortal` → `Địa Tiên`; `True Immortal` → `Chân Tiên`; `Heavenly Immortal` → `Thiên Tiên`; `Golden Immortal` → `Kim Tiên`; `Taiyi / Primordial / Dao Ancestor` → `Thái Ất / Đại La / Đạo Tổ`
- **Core Cultivation Terminology (Thuật ngữ tu tiên cốt lõi):**
  - `Spiritual Root (Linggen)` → `Linh căn` (`Thiên / Dị / Chân / Ngụy linh căn`); `Spiritual Qi (Lingqi)` → `Linh khí`; `Spirit Stone (Lingshi)` → `Linh thạch` (`Hạ / Trung / Thượng / Cực phẩm`); `Divine Sense / Spiritual Sense (Shenshi / Lingshi)` → `Thần thức / Linh thức`
  - `Magical Artifact / Spirit Tool (Faqi / Lingqi)` → `Pháp khí / Linh khí`; `Dharma Treasure / Magic Treasure (Fabao)` → `Pháp bảo`; `Natal Treasure (Benming Fabao)` → `Bản mệnh pháp bảo`; `Ancient / Chaos / Immortal Treasure (Gubao / Lingbao / Xianbao)` → `Cổ bảo / Thông Thiên Linh Bảo / Tiên thiên linh bảo`
  - `Cave Abode (Dongfu)` → `Động phủ`; `Secret Realm (Mijing)` → `Bí cảnh`; `Storage Bag / Ring (Chuwu Dai / Jie)` → `Túi trữ vật / Nhẫn trữ vật`; `Jade Slip (Yujian)` → `Ngọc giản`; `Talisman (Fulu)` → `Phù lục`; `Formation / Array (Zhenfa)` → `Trận pháp`; `Restriction / Ward (Jinzhi)` → `Cấm chế`
  - `Heart Demon (Xinmo)` → `Tâm ma`; `Heavenly / Lightning Tribulation (Tianjie / Leijie)` → `Thiên kiếp / Lôi kiếp`; `Secluded Meditation (Biguan)` → `Bế quan`; `Seize the Body / Possession (Duoshe)` → `Đoạt xá`

## LitRPG / system / game-like progression

Prioritize:
- system/UI messages
- stats/attributes
- classes/jobs
- levels/tiers/ranks
- skills/abilities/traits/talents/perks
- quests/objectives/rewards
- items/equipment/materials/currencies
- status effects, cooldowns, damage types, system-specific mechanics

Preserve exact distinctions and concise UI-like formatting. Do not make technical system terminology overly literary.

## Military / political / magitech fantasy

Prioritize:
- military ranks vs noble titles vs government offices
- units, commands, academies, ministries/cabinets
- modern bureaucracy and technology if present
- mana science, fictional engineering, weapons systems, dimensional phenomena

Do not assume medieval technology merely because the setting contains nobles, castles, or knights.

## Urban / modern fantasy

Prioritize:
- modern institutions, slang, bureaucracy, media, law enforcement, schools/workplaces
- supernatural organizations and powers
- contemporary speech register

Do not archaize modern dialogue or institutions.

## Hybrid novels

Combine only supported rules. Example: a Murim + system novel may need both martial hierarchy and UI/stat terminology. A fantasy + magitech novel may need both noble ranks and technical scientific vocabulary. Avoid forcing one genre's vocabulary over another when the source keeps them distinct.
