# Sino-Influenced Genres & Hán-Việt Localization Guide

Load this reference **only** for Vietnamese translation of Sino-influenced genres (Korean Murim, Chinese wuxia/võ hiệp, xianxia/tiên hiệp, xuanhuan/huyền huyễn, Eastern supernatural/linh dị) and hybrids containing a Sino-origin layer. Do not import xianxia concepts into Murim or vice versa without source evidence.

## 1. Naming Policy Modes & Evidence Priority

Select the mode supported by the source and user preference:

- **`full-han-viet` (default):** Render **100% Hán-Việt** with normal spaces for all recurring Sino-origin proper nouns — personal names, surnames, epithets, sects, clans, halls, alliances, cults, arts, techniques, realms, constitutions, manuals, pills, weapons, and places.
- **`hybrid-world-hv` (e.g., modern-linked Murim hybrids like *Murim Login*):** Keep personal names (plus modern guilds/brands) in clean Romaja when requested/established; render all Sino-origin Murim world entities (places, sects, halls, pavilions, arts, techniques, realms, pills, epithets) in complete Hán-Việt with normal spaces.
- **`preserve`:** Only when the user explicitly requests raw romanized names throughout.

**Evidence priority for Hán-Việt:**
1. Explicit Hanzi/Hanja in source text
2. Approved/existing project glossary canon
3. Explicit semantic meaning or wordplay in source
4. Strongly supported Sino-Korean / Sino-Chinese reading
5. **Distinctive, natural project-local Hán-Việt form** when original characters are unavailable.

**Hard constraints for Sino-origin Hán-Việt `translated_name`:**
- Localize **every** syllable of a Sino-origin canonical name completely, then use normal spaces — never output partial romanized remainders or half-Hán half-Nôm hybrids (e.g., use `Trảm Ma Thập Giới Luật`, not `Thập Giới Săn Ma`).
- Never append invented CJK characters or parenthetical glosses inside `translated_name` (e.g., never `Khung Lâu (Lầu Cúi Đầu)`). "Do not fabricate Hanja/Hanzi" forbids inventing CJK characters or claiming verified historical etymology — it never forbids reconstructing English-calqued proper nouns into Hán-Việt or picking a consistent project-local Hán-Việt name.
- Keep `raw_name` source-faithful and store confirmed Romaja/pinyin/Hangul/English variants in `aliases` (`|`), never in running Vietnamese prose.
- **Contextual Sino-Korean check (unhyphenated / single / frontier names):** Verify actual Hangul/Hanja or context first; do not assume minority/borderland characters are Sino-origin. When Sino-Korean origin is supported, map syllables coherently to Hán-Việt; flag provisional readings only in optional `description`, never as verified Hanja.

## 2. English-Calqued Proper Noun Reconstruction (2–4 Syllable Head-Final)

When translating through English, proper nouns rendered as English words (pavilions, brothels, halls, towers, inns, fortresses, valleys, sects, formations, techniques, realms, items, epithets) must be reconstructed into **concise 2–4 syllable Head-Final Hán-Việt compounds**:

`[Modifier Hán-Việt] + [Head Noun Hán-Việt: Các / Lâu / Điện / Đường / Viện / Hiên / Trại / Bảo / Cốc / Môn / Phái / Bang / Hội / Trận / Pháp / Quyết / Công / Kích / Trảm]`

- Examples: `Dusk Sentiments Pavilion` → `Mộ Tình Các` / `Tịch Tình Các`; `Bowed Pavilion` → `Khung Lâu`; `Dog Fortress` → `Khuyển Trại`; `Lightning Strike` → `Lôi Kích`; `Blood Wolf Sword` → `Huyết Lang Kiếm`.
- Color/element modifiers: Blood/Crimson → `Huyết / Xích`; Black/Dark/Shadow → `Huyền / Hắc / Ám`; Blue/Azure → `Thanh / Thương`; White/Silver → `Bạch / Ngân`; Golden/Yellow → `Kim / Hoàng`.
- Never translate proper nouns word-for-word in modern Head-Initial vernacular order (`Lâu Các Tinh Thần Buổi Tối`, `Chó Trại`, `Sét Đánh`).

## 3. Bracketed CJK Glosses, CJK Verses, Watermarks & Rejection Rules

- **Bracketed CJK/Hangul glosses:** When source attaches raw Hanja/Hanzi/Hangul after a term (`Mental Imagery Sparring [心像比武]`, `Peerless Prodigy (千古奇才)`), localize into Vietnamese/Hán-Việt and **strip the bracketed script** completely so zero raw CJK/Hangul survives in prose.
- **Standalone CJK verses/chants/inscriptions:** Convert to full Hán-Việt or natural Vietnamese verse.
- **Aggregator watermarks vs. genuine footnotes:** Omit bare romanized/translated novel-title watermarks or site promos tacked onto a chapter's end (e.g., `Chang-gwi-musang`, `27+ chapters ahead on...`). Translate genuine author/translator `Footnotes:` / `TL Notes:` cleanly (`Chú thích:`) so paragraph alignment and QA length ratios stay intact.
- **Bare standalone titles (reject in glossary):** Do not extract standalone institutional roles lacking a proper noun or organization (`Sect Leader`, `Cult Leader`, `Alliance Leader`, `Patriarch`, `Matriarch`, `Elder`, `Grand Elder`, `Pavilion Master`, `Hall Master`, `Peak Master`, `Young Master`, `Young Lady`, `Master`, `Senior Brother`, `Junior Sister`, `Lord`). Their Vietnamese rendering depends on scene context (`Chưởng môn` for orthodox sects, `Môn chủ` for gates, `Giáo chủ` for cults, `Gia chủ` for clans, `Bang chủ` for gangs). Extract only when bound to a specific canonical entity (`Mount Hua Sect Leader` → `Chưởng môn Hoa Sơn`).
- **Generic descriptive roles & brothel terms:** Never extract unnamed roles (`leading courtesan`, `brothel keeper`, `innkeeper`, `guard`) as `character` rows. In historical/Murim brothel (`thanh lâu / kỹ viện`) contexts, render `courtesan` as `kỹ nữ / ca kỹ / thanh y / hoa khôi` (never `y quan`).

## 4. Canonical Sino-Korean / Sino-Chinese Anchor Tables

### Compound Surnames & Great Clans (Thế Gia / Họ Kép)
- `Namgung / Nangong` → `Nam Cung` (`Namgung Clan` → `Nam Cung Thế Gia`)
- `Bukgung / Baek Gung / Baekgung / Beigong` → `Bắc Cung` *(English KR-Murim often distorts `Bukgung` 北宮 as `Baek Gung` — use `Bắc Cung`, not `Bạch Cung`)*
- `Moyong / Mo-yong / Murong` → `Mộ Dung`; `Jegal / Zhuge` → `Gia Cát`
- `Sacheon Tang / Dang / Tang Clan` → `Tứ Xuyên Đường Môn` (`Dang/Tang` → `Đường`)
- `Habuk Paeng / Peng` → `Hà Bắc Bành Gia` (`Paeng/Peng` → `Bành`)
- `Hwangbo / Huangfu` → `Hoàng Phủ`; `Danmok / Duanmu` → `Đan Mộc`; `Seomun / Ximen` → `Tây Môn`
- `Dokgo / Dugu` → `Độc Cô`; `Dongbang / Dongfang` → `Đông Phương`; `Sama / Sima` → `Tư Mã`
- `Sanggwan / Shangguan` → `Thượng Quan`; `Ohyang / Ouyang` → `Âu Dương`; `Hagun / Xiahou` → `Hạ Hầu`
- Single surnames: `Wi / Wei` → `Ngụy`; `Baek / Bai` → `Bạch`; `Cheon / Tian` → `Thiên`; `Jin / Chen / Qin` → `Trần / Tần`

### Major Sects & Factions (Cửu Phái Nhất Bang & Tứ Đại Thế Lực)
- `Sorim / Shaolin` → `Thiếu Lâm`; `Mudang / Wudang` → `Võ Đang`; `Hwasan / Mount Hua` → `Hoa Sơn`; `Ami / Emei` → `Nga Mi`; `Gonryun / Kunlun` → `Côn Luân`; `Jeomchang / Diancang` → `Điểm Thương`; `Cheongseong / Qingcheng` → `Thanh Thành`; `Kongtong / Gongdong` → `Không Động`; `Jongnam / Zhongnan` → `Chung Nam`; `Haenam / Hainan` → `Hải Nam`; `Gaebang / Beggars Sect` → `Cái Bang`
- `Murim Meng / Martial Arts Alliance` → `Võ Lâm Minh` (`Mengju` → `Minh chủ`)
- `Jeongpa / Orthodox` → `Chính Phái / Bạch Đạo`; `Sapa / Unorthodox` → `Tà Phái / Hắc Đạo`; `Hao Mun / Lower District Sect` → `Hạo Môn`
- `Magyo / Cheonmagyo / Heavenly Demon Divine Cult` → `Ma Giáo / Thiên Ma Thần Giáo` (`Cheonma` → `Thiên Ma`); `Hyeolgyo / Blood Cult` → `Huyết Giáo` (`Hyeolma` → `Huyết Ma`)
- `Saewoe / Outer Regions`: `Bukhae Binggung` → `Bắc Hải Băng Cung`; `Namman Yasugung` → `Nam Man Dã Thú Cung`; `Potala Palace` → `Bố Đạt La Cung`

## 5. Murim & Wuxia Taxonomy & Realms

Keep distinct in classification and prose:
- **Institutions:** `sect` (môn phái) vs `clan/martial family` (thế gia/gia tộc) vs `alliance` (minh) vs `cult` (giáo) vs `gang` (bang) vs `escort/guild/hall/pavilion/fortress/court`
- **Arts & systems:** `internal energy/true qi` (`nội công/nội lực/chân khí`) vs `ganggi/aura` (`cương khí`); `dantian/meridians/acupoints` (`đan điền/kinh mạch/huyệt đạo`); `internal arts` (`nội công/tâm pháp`) vs `external arts` (`ngoại công`); `lightness skill` (`khinh công`) vs `footwork` (`bộ pháp`) vs `movement art` (`thân pháp`); `weapon arts` (`kiếm/đao/thương/chưởng/quyền/trảo pháp`); complete martial systems vs individual named forms/ultimate moves (`chiêu thức/tuyệt kỹ`); manuals (`bí kíp`), pills (`đan dược`), poisons (`độc dược`), hidden weapons (`ám khí`), formations (`trận pháp`).
- **Standard Korean Murim Realms:** `Third-rate (삼류)` → `Tam Lưu` → `Second-rate (이류)` → `Nhị Lưu` → `First-rate (일류)` → `Nhất Lưu` → `Peak / Master (절정)` → `Tuyệt Đỉnh` (`Sơ/Trung/Hậu kỳ/Đỉnh phong` or `Tiểu thành/Đại thành/Viên mãn`) → `Transcendent / Super-Peak (초절정)` → `Siêu Tuyệt Đỉnh` (or `Siêu Phàm`) → `Unrestrained / Harmony (화경)` → `Hóa Cảnh` → `Mystic / Profound (현경)` → `Huyền Cảnh` → `Life and Death (생사경)` → `Sinh Tử Cảnh` → `Natural Realm (자연경)` → `Tự Nhiên Cảnh` → `Void / Return to Origin (공경 / 반박귀진)` → `Không Cảnh / Phản Phác Quy Chân`.
- **Core Murim Terms:** `Geomgi` → `Kiếm khí`; `Geomgang` → `Kiếm cương`; `Geomsa` → `Kiếm ti`; `Simgeom` → `Tâm kiếm`; `Hogyeongganggi` → `Hộ thể cương khí`; `Gu-gyeol` → `Khẩu quyết`; `Im-Dok Yangmaek` → `Nhâm Đốc nhị mạch`; `Juhwa-ipma` → `Tẩu hỏa nhập ma`; `Hwangoltaltae` → `Hoàn cốt thoát thai`; `Bongmun` → `Phong môn`; `Pae-gong` → `Phế võ công`.
- **Guardrail:** Keep xianxia terms (spiritual roots, Golden Core, tribulation, ascension) out of pure Murim/wuxia unless explicitly present. Do not force archaic speech onto casual family banter or deadpan comedy.

## 6. Xianxia, Xuanhuan & Eastern Supernatural Taxonomy & Realms

Keep cleanly separated from Murim/wuxia (never tag xianxia/supernatural works as `martial`). Always use **formal Hán-Việt (Hán-Việt trang trọng)** for realms, arc/novel titles, sects/orders/halls, spells/methods, and professions/ranks — never Western-style vernacular (`thợ săn yêu ma`, `người luyện thuốc`) or modern office words (`nhân viên`, `ngoại vụ nhân viên`, `công ty`).

- **Standard Cultivation Realms:** `Qi Refining/Condensation (Lianqi)` → `Luyện Khí kỳ` → `Foundation Establishment (Zhuji)` → `Trúc Cơ kỳ` → `Core Formation / Golden Core (Jiedan/Jindan)` → `Kết Đan / Kim Đan kỳ` → `Nascent Soul (Yuanying)` → `Nguyên Anh kỳ` → `Soul Formation / Deity Transformation (Huashen)` → `Hóa Thần kỳ` → `Void Refining (Lianxu)` → `Luyện Hư kỳ` → `Body Integration (Heti)` → `Hợp Thể kỳ` → `Mahayana (Dacheng)` → `Đại Thừa kỳ` → `Tribulation Transcendence (Dujie)` → `Độ Kiếp kỳ` → Immortals: `Tán Tiên / Địa Tiên / Chân Tiên / Thiên Tiên / Kim Tiên / Thái Ất / Đại La / Đạo Tổ`.
- **Core Cultivation Terms:** `Spiritual Root` → `Linh căn` (`Thiên/Dị/Chân/Ngụy`); `Spiritual Qi` → `Linh khí`; `Spirit Stone` → `Linh thạch`; `Divine/Spiritual Sense` → `Thần thức / Linh thức`; `Magic/Spirit Artifact` → `Pháp khí / Linh khí`; `Dharma Treasure` → `Pháp bảo`; `Natal Treasure` → `Bản mệnh pháp bảo`; `Ancient/Immortal Treasure` → `Cổ bảo / Linh bảo / Tiên bảo`; `Cave Abode` → `Động phủ`; `Secret Realm` → `Bí cảnh`; `Storage Bag/Ring` → `Túi/Nhẫn trữ vật`; `Jade Slip` → `Ngọc giản`; `Talisman` → `Phù lục`; `Formation/Array` → `Trận pháp`; `Restriction/Ward` → `Cấm chế`; `Heart Demon` → `Tâm ma`; `Heavenly/Lightning Tribulation` → `Thiên kiếp / Lôi kiếp`; `Secluded Meditation` → `Bế quan`; `Possession` → `Đoạt xá`.
- **Cultivation / Exorcism Roles (`VietPhrase`-verified formal Hán-Việt):** `Demon Hunter / Exorcist` → `Trảm Ma Sư / Khu Ma Sư`; `Alchemist` → `Đan Sư / Luyện Đan Sư`; `Formation Master` → `Trận Sư / Trận Pháp Sư`; `Artifact Refiner` → `Luyện Khí Sư`; `Talisman Master` → `Phù Lục Sư`; `Sect/Order Leader` → `Tông Chủ / Lệnh Chủ`; `Hall/Pavilion Master` → `Đường Chủ / Các Chủ`; `Inner / Outer / Core Disciple` → `Nội Môn / Ngoại Môn / Chân Truyền Đệ Tử`; `Demon Race` → `Ma Tộc`; `Demon Beast` → `Yêu Thú`; `Demonic/Evil Qi` → `Ma Khí / Tà Khí`; `Demon/Ghost King` → `Ma Vương / Quỷ Vương`.
