import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe, ChevronDown, Check } from 'lucide-react';

const languages = [
  { code: 'uz', label: "O'zbek", short: 'UZ' },
  { code: 'ru', label: 'Русский', short: 'RU' },
  { code: 'en', label: 'English', short: 'EN' },
];

interface LanguageSwitcherProps {
  className?: string;
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({ className = '' }) => {
  const { i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentLang = languages.find((lang) => lang.code === i18n.language) || languages[0];

  const handleLanguageChange = (code: string) => {
    i18n.changeLanguage(code);
    localStorage.setItem('preferredLanguage', code);
    setIsOpen(false);
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent | TouchEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('touchstart', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  return (
    <div className={`relative inline-block text-left ${className}`} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label="Tilni tanlash"
        className="inline-flex items-center justify-center gap-2 px-3 py-1.5 min-h-[40px] text-xs font-bold font-montserrat text-white bg-[#2A3442] hover:bg-[#34495E] border-2 border-black rounded-xl shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] hover:-translate-x-[1px] hover:-translate-y-[1px] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all focus:outline-none focus:ring-2 focus:ring-[#38C9E6] cursor-pointer touch-manipulation relative z-50"
      >
        <Globe className="w-3.5 h-3.5 text-[#38C9E6]" />
        <span className="w-6 text-center font-ibm-plex-mono font-bold">{currentLang.short}</span>
        <ChevronDown
          className={`w-3.5 h-3.5 text-[#B0BEC5] transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {isOpen && (
        <>
          {/* Subtle backdrop overlay for outside-tap & mobile visual separation */}
          <div
            className="fixed inset-0 z-40 bg-black/20 sm:bg-transparent"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />
          <div
            role="listbox"
            className="absolute right-0 w-36 mt-2 origin-top-right bg-[#2A3442] border-2 border-black rounded-2xl shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] z-50 overflow-hidden p-1.5 animate-zoom-in"
          >
            <div className="flex flex-col gap-1">
              {languages.map((lang) => {
                const isSelected = i18n.language === lang.code;
                return (
                  <button
                    key={lang.code}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => handleLanguageChange(lang.code)}
                    className={`w-full text-left px-3 py-2 text-xs font-montserrat rounded-xl transition-all flex items-center justify-between cursor-pointer min-h-[38px] ${
                      isSelected
                        ? 'text-black bg-gradient-to-r from-[#38C9E6] to-[#43E8A0] font-black border border-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]'
                        : 'text-[#B0BEC5] hover:text-white hover:bg-[#34495E] font-bold'
                    }`}
                  >
                    <span>{lang.label}</span>
                    {isSelected && <Check className="w-3.5 h-3.5 text-black stroke-[3]" />}
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
export default LanguageSwitcher;
