/**
 * i18n.js — Japanese translation helpers for product data.
 */

const SUFFIX_TRANSLATIONS = {
  "Men's Watch": "メンズ腕時計",
  "Women's Watch": "レディース腕時計",
  "Unisex Watch": "ユニセックス腕時計",
  "Men's": "メンズ",
  "Women's": "レディース",
};

const CATEGORY_TRANSLATIONS = {
  "Casio G Shock 57": "カシオ G-SHOCK",
  "Casio Digital 350": "カシオ デジタル",
  "Casio Protrek 58": "カシオ PRO TREK",
  "Citizen 74": "シチズン",
  "Orient Watches 252": "オリエント",
  "Avi 8 Watches 484": "AVI-8",
  "Bulova Watches 271": "ブローバ",
  "Invicta Watches 307": "インヴィクタ",
  "Luminox Watches 306": "ルミノックス",
  "Refurbished Watches 321": "再生品",
  "Fragrances 749": "フレグランス",
};

const FEATURE_TRANSLATIONS = {
  "Solar": "ソーラー",
  "Automatic": "自動巻き",
  "Quartz": "クォーツ",
  "Chronograph": "クロノグラフ",
  "Digital": "デジタル",
  "Analog": "アナログ",
  "Analog Digital": "アナログデジタル",
  "Limited Edition": "限定品",
  "Vintage": "ビンテージ",
  "Diver's": "ダイバーズ",
  "G-Shock": "G-SHOCK",
  "Pro Trek": "PRO TREK",
  "Eco-Drive": "エコ・ドライブ",
  "Bio-Based": "バイオベース",
  "Resin Strap": "樹脂ベルト",
  "Stainless Steel": "ステンレススチール",
  "Leather Strap": "レザーベルト",
  "Rubber Band": "ラバーベルト",
  "Smartphone Link": "スマホリンク",
  "Full Metal": "フルメタル",
  "Refurbished": "再生品",
  "Pro Diver": "プロダイバー",
  "Grand Diver": "グランダイバー",
  "Stainless Steel": "ステンレススチール",
  "Eco-Drive": "エコ・ドライブ",
  "Kinetic Direct Drive": "キネティックダイレクトドライブ",
  "Fuel For Life Pour Homme": "フューエルフォーライフプールオム",
  "Eau de Toilette Spray": "オードトワレ",
};

/**
 * Translate a product name to Japanese.
 */
export function translateProductName(name) {
  let result = name;

  // Water resistance: 200M → 200m防水
  result = result.replace(/(\d{2,3})M\b/g, '$1m防水');

  // Feature translations (longest first to avoid partial matches)
  const sorted = Object.entries(FEATURE_TRANSLATIONS)
    .sort((a, b) => b[0].length - a[0].length);

  for (const [en, jp] of sorted) {
    // Use word boundary for safer replacement
    result = result.replace(new RegExp(en.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), jp);
  }

  // Suffix translations
  for (const [en, jp] of Object.entries(SUFFIX_TRANSLATIONS)) {
    if (result.endsWith(en)) {
      result = result.slice(0, -en.length) + jp;
      break;
    }
  }

  // Clean up
  result = result.replace(/\s+/g, ' ').trim();

  return result;
}

/**
 * Translate category to Japanese.
 */
export function translateCategory(cat) {
  return CATEGORY_TRANSLATIONS[cat] || cat;
}

/**
 * Translate product description to Japanese.
 */
export function translateDescription(desc) {
  let result = desc;
  result = result.replace(/(\d{2,3})M\b/g, '$1m防水');
  for (const [en, jp] of Object.entries(FEATURE_TRANSLATIONS)) {
    result = result.replace(new RegExp(en.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), jp);
  }
  for (const [en, jp] of Object.entries(SUFFIX_TRANSLATIONS)) {
    if (result.endsWith(en)) {
      result = result.slice(0, -en.length) + jp;
      break;
    }
  }
  return result;
}
