import { useEffect, ReactNode } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg';
}

const widthStyles = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
};

export function Modal({ isOpen, onClose, title, children, maxWidth = 'sm' }: ModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-xs transition-all duration-200"
      onClick={onClose}
    >
      <div
        className={`w-full ${widthStyles[maxWidth]} bg-[#2A3442] border-2 border-black rounded-3xl p-4 sm:p-6 sm:p-8
                    shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-4 max-h-[85vh] sm:max-h-[90vh] overflow-y-auto animate-zoom-in`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-center justify-between border-b-2 border-black pb-3 sm:pb-4 gap-2">
          <h3 className="text-lg sm:text-xl font-extrabold text-white font-montserrat tracking-tight truncate mr-2">
            {title}
          </h3>
          <button
            onClick={onClose}
            className="min-h-[44px] min-w-[44px] flex items-center justify-center text-[#B0BEC5] hover:text-black hover:bg-[#FF9B9B] border-2 border-transparent hover:border-black transition-all p-2 rounded-xl cursor-pointer shrink-0"
            aria-label="Yopish"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="py-2 text-sm text-[#B0BEC5] font-ibm-plex-mono">{children}</div>
      </div>
    </div>
  );
}
export default Modal;
