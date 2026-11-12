import En from './int/en.json';
import Es from './int/es.json';
import Pt from './int/pt.json';
import De from './int/de.json';
import Nl from './int/nl.json';
import Fr from './int/fr.json';
import It from './int/it.json';
import Ne from './int/ne.json';
import Hi from './int/hi.json';
import Id from './int/id.json';
import Ar from './int/ar.json';

export const locales = {
  "en": En,
  "es": Es,
  "pt": Pt,
  "de": De,
  "nl": Nl,
  "fr": Fr,
  "it": It,
  "ne": Ne,
  "hi": Hi,
  "id": Id,
  "ar": Ar,
}

export const localeNames = {
  "en": "English",
  "es": "Español",
  "pt": "Português",
  "de": "Deutsch",
  "nl": "Nederlands",
  "fr": "Français",
  "it": "Italiano",
  "ne": "नेपाली भाषा (Nepālī bhāśā)",
  "hi": "हिन्दी (Hindī)",
  "id": "Indonesia",
  "ar": "العربية",
};

// The languages written from right to left
export const RTL_LANGS = new Set(["ar", "he"]);

// The direction of the text of a language, for the dir attribute
export function dirOf(lang) {
  return RTL_LANGS.has(lang) ? "rtl" : "ltr";
}

// Sets the language and direction of the whole page, which Shoelace and the CSS follow
export function applyLang(lang, root = document.documentElement) {
  root.lang = lang;
  root.dir = dirOf(lang);
}

// The language of the browser, by its first part: ar-PS and ar-EG are ar
export function getLocalCode() {
  const lang = navigator.language.slice(0,2);

  if (lang in locales) {
    return lang;
  }

  return "en";
};
