import React from 'react';
import ReactDOM from 'react-dom/client';
import './hot.css';
import './hot-font-face.css';
import './index.css';
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import { IntlProvider } from 'react-intl';
import En from './int/en.json';
import Es from './int/es.json';
import Pt from './int/pt.json';

const locales = {
  "en": En,
  "es": Es,
  "pt": Pt
}

const getLocaleMessages = () => {
  const lang = navigator.language.slice(0,2);
  if (lang in locales) {
    return locales[lang];
  }
  return locales["en"]
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <IntlProvider locale ={navigator.language} messages={getLocaleMessages()}>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </IntlProvider>
  </React.StrictMode>
);


