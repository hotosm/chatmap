import { afterEach, expect, test as it, vi } from 'vitest'
import { createIntl } from 'react-intl';

import { RTL_LANGS, applyLang, dirOf, getLocalCode, localeNames, locales } from '../src/lang';
import En from '../src/int/en.json';
import Ar from '../src/int/ar.json';

afterEach(() => {
  vi.unstubAllGlobals();
});

// dirOf
it('should write Arabic, and Hebrew if it is ever added, from right to left', () => {
  expect(dirOf("ar")).toBe("rtl");
  expect(dirOf("he")).toBe("rtl");
  expect(RTL_LANGS.has("ar")).toBe(true);
});
it('should write the other languages from left to right', () => {
  for (const lang of Object.keys(locales).filter((lang) => lang !== "ar")) {
    expect(dirOf(lang)).toBe("ltr");
  }
});

// applyLang
it('should set the language and the direction of the page', () => {
  const root = { lang: "en", dir: "" };
  applyLang("ar", root);
  expect(root).toEqual({ lang: "ar", dir: "rtl" });
});
it('should set the page back from right to left when the language changes again', () => {
  const root = { lang: "ar", dir: "rtl" };
  applyLang("es", root);
  expect(root).toEqual({ lang: "es", dir: "ltr" });
});

// getLocalCode
it('should take Arabic of any country as Arabic', () => {
  for (const language of ["ar", "ar-PS", "ar-EG", "ar-SA"]) {
    vi.stubGlobal('navigator', { language });
    expect(getLocalCode()).toBe("ar");
  }
});
it('should fall back to English for a language it does not speak', () => {
  vi.stubGlobal('navigator', { language: "he-IL" });
  expect(getLocalCode()).toBe("en");
});

// ar.json
it('should name Arabic in Arabic', () => {
  expect(localeNames.ar).toBe("العربية");
  expect(locales.ar).toBe(Ar);
});
it('should have exactly the texts of English in Arabic', () => {
  expect(Object.keys(Ar).sort()).toEqual(Object.keys(En).sort());
});
it('should have no Arabic text left empty', () => {
  for (const [key, text] of Object.entries(Ar)) {
    expect(text.trim(), key).not.toBe("");
  }
});
it('should keep the placeholders of each English text', () => {
  // The name of each argument, as in {place} or {days, plural, …}: not the words that open a plural form, as in {A group …}
  const placeholders = (text) => [...text.matchAll(/\{\s*(\w+)\s*[,}]/g)].map((match) => match[1]).sort();
  for (const [key, text] of Object.entries(En)) {
    expect(placeholders(Ar[key]), key).toEqual(placeholders(text));
  }
});
it('should format every Arabic text, with the six plural forms of Arabic', () => {
  const errors = [];
  const intl = createIntl({ locale: "ar", messages: Ar, onError: (error) => errors.push(error.message) });
  const values = { name: "n", type: "t", num: 1, count: 1, chatmapper: "c", key: "k", tag: "t", value: "v", ago: "a",
    since: "s", confirmed: "c", hours: "h", group: "g", days: 1, place: "p", rule: "r", distance: "d", code: "c", what: "w",
    lasts: "l", age: "a", when: "w", max: 1, zone: "z" };
  for (const id of Object.keys(Ar)) intl.formatMessage({ id }, values);
  expect(errors).toEqual([]);
  const days = (days) => intl.formatMessage({ id: "app.messages.days" }, { days });
  expect(days(1)).toBe("يوم واحد");
  expect(days(2)).toBe("يومان");
  expect(days(3)).toContain("أيام");
  expect(days(11)).toContain("يومًا");
});
