import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { uz } from './locales/uz';
import { ru } from './locales/ru';
import { en } from './locales/en';

const resources = {
  uz: { translation: uz },
  ru: { translation: ru },
  en: { translation: en },
};

const savedLanguage = localStorage.getItem('preferredLanguage') || 'uz';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    lng: savedLanguage,
    fallbackLng: 'uz',
    interpolation: {
      escapeValue: false, // react already safes from xss
    },
  });

export default i18n;
