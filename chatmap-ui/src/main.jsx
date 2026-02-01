import './styles/main.css'
import React from 'react';
import ReactDOM from 'react-dom/client';
import ErrorBoundary from './components/ErrorBoundary';
import { IntlProvider } from 'react-intl';
import { HashRouter } from 'react-router-dom';
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
import { MapDataProvider } from './context/MapDataContext';
import { ConfigProvider } from './context/ConfigContext';
import { AuthProvider } from './context/AuthContext';
import AppRoutes from './routes'; 

// Shoelace UI components
import '@shoelace-style/shoelace/dist/components/alert/alert.js';
import '@shoelace-style/shoelace/dist/components/badge/badge.js';
import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/dialog/dialog.js';
import '@shoelace-style/shoelace/dist/components/dropdown/dropdown.js';
import '@shoelace-style/shoelace/dist/components/icon-button/icon-button.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';
import '@shoelace-style/shoelace/dist/components/input/input.js';
import '@shoelace-style/shoelace/dist/components/menu-item/menu-item.js';
import '@shoelace-style/shoelace/dist/components/menu/menu.js';
import '@shoelace-style/shoelace/dist/components/popup/popup.js';
import '@shoelace-style/shoelace/dist/components/radio/radio.js';
import '@shoelace-style/shoelace/dist/components/switch/switch.js';

import { setBasePath } from '@shoelace-style/shoelace/dist/utilities/base-path.js';
setBasePath("/shoelace/");

const locales = {
  "en": En,
  "es": Es,
  "pt": Pt,
  "de": De,
  "nl": Nl,
  "fr": Fr,
  "it": It,
  "ne": Ne,
  "hi": Hi,
  "id": Id
}

const getLocaleMessages = () => {
  const lang = navigator.language.slice(0,2);
  if (lang in locales) {
    return locales[lang];
  }
  return locales["en"]
}

async function init() {
  const response = await fetch('/config.json');
  const config = await response.json();
  const root = ReactDOM.createRoot(document.getElementById('root'));

  root.render(
    <React.StrictMode>
      <IntlProvider locale={navigator.language.slice(0,2)} messages={getLocaleMessages()}>
        <ErrorBoundary>
          <AuthProvider>
            <MapDataProvider>
              <ConfigProvider initialConfig={config}>
                <HashRouter>
                  <AppRoutes />
                </HashRouter>
              </ConfigProvider>
            </MapDataProvider>
          </AuthProvider>
        </ErrorBoundary>
      </IntlProvider>
    </React.StrictMode>
  );
}

init();

