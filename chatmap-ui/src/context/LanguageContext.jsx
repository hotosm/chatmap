import { createContext, useContext, useLayoutEffect, useState } from 'react';
import { applyLang, getLocalCode, locales } from '../lang';

const LanguageContext = createContext();

export function LanguageProvider(props) {
  const [lang, setLang] = useState(getLocalCode());
  const messages = locales[lang];

  // Before painting, so a right to left language is never shown left to right
  useLayoutEffect(() => {
    applyLang(lang);
  }, [lang]);

  return (
    <LanguageContext value={{lang, messages, setLang}}>
      {props.children}
    </LanguageContext>
  );
};

export function useLanguage() {
  const context = useContext(LanguageContext);

  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }

  return context;
};
