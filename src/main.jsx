import React from 'react';
import ReactDOM from 'react-dom/client';
import './styles/main.css'
import Home from './pages/home';
import ErrorBoundary from './components/ErrorBoundary';
import { IntlProvider } from 'react-intl';
import En from './int/en.json';
import Es from './int/es.json';
import Pt from './int/pt.json';
import { MapDataProvider } from './context/MapDataContext';

// Shoelace UI components
import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/input/input.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';
import '@shoelace-style/shoelace/dist/components/dropdown/dropdown.js';
import '@shoelace-style/shoelace/dist/components/menu/menu.js';
import '@shoelace-style/shoelace/dist/components/menu-item/menu-item.js';

import { setBasePath } from '@shoelace-style/shoelace/dist/utilities/base-path.js';
setBasePath("https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.14.0/cdn/");

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
    <IntlProvider locale={navigator.language.slice(0,2)} messages={getLocaleMessages()}>
      <ErrorBoundary>
        <MapDataProvider>
          <Home />
        </MapDataProvider>
      </ErrorBoundary>
    </IntlProvider>
  </React.StrictMode>
);


