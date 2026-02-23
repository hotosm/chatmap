import { createContext, useContext, useState } from 'react';
import { getLocalCode, locales } from '../lang';

const LanguageContext = createContext();

export function LanguageProvider(props) {
  const [lang, setLang] = useState(getLocalCode());
  const messages = locales[lang];

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
