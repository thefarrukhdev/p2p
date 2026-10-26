import { create } from 'zustand';

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info';
  text: string;
}

interface ToastState {
  toasts: ToastMessage[];
  addToast: (text: string, type?: 'success' | 'error' | 'info') => void;
  removeToast: (id: string) => void;
}

const toastTimers = new Map<string, ReturnType<typeof setTimeout>>();

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  addToast: (text, type = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    
    // Auto-remove timer
    const timer = setTimeout(() => {
      toastTimers.delete(id);
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      }));
    }, 4000);
    
    toastTimers.set(id, timer);

    set((state) => {
      // Keep maximum of 3 concurrent toasts
      const updated = [...state.toasts, { id, type, text }];
      if (updated.length > 3) {
        const removed = updated.shift();
        if (removed && toastTimers.has(removed.id)) {
          clearTimeout(toastTimers.get(removed.id));
          toastTimers.delete(removed.id);
        }
      }
      return { toasts: updated };
    });
  },
  removeToast: (id) => {
    const timer = toastTimers.get(id);
    if (timer) {
      clearTimeout(timer);
      toastTimers.delete(id);
    }
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },
}));

export const triggerToast = (text: string, type?: 'success' | 'error' | 'info') => {
  useToastStore.getState().addToast(text, type);
};
