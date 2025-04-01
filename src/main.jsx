import React from 'react';
import ReactDOM from 'react-dom/client';
import './styles/hot.css';
import './styles/hot-font-face.css';
import './styles/main.css'
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import { IntlProvider } from 'react-intl';

const getLocaleMessages = async () => {
  const lang = navigator.language.slice(0,2);
  if (lang === "es") {
    return (await import('./int/es')).default;
  } else if (lang === "pt") {
    return (await import('./int/pt')).default;
  }
  return (await import('./int/en')).default;
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


