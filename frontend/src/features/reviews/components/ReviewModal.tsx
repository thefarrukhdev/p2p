import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useReviews } from '@/features/reviews/hooks';
import { Button, Modal } from '@/shared/ui';
import { triggerToast } from '@/shared/stores/toast';
import { ThumbsUp, ThumbsDown, Send } from 'lucide-react';

const reviewSchema = z.object({
  comment: z.string().max(500, 'Fikr-mulohaza 500 ta belgidan oshmasligi kerak').optional(),
});

type FormValues = z.infer<typeof reviewSchema>;

interface ReviewModalProps {
  slotId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function ReviewModal({ slotId, isOpen, onClose }: ReviewModalProps) {
  const { createReview, isCreatingReview } = useReviews();
  const [isPositive, setIsPositive] = useState<boolean>(true);

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(reviewSchema),
    defaultValues: {
      comment: '',
    },
  });

  const commentVal = watch('comment') || '';

  const onFormSubmit = async (values: FormValues) => {
    if (!slotId) {
      triggerToast('Fikr bildirish uchun slot identifikatori talab qilinadi!', 'error');
      return;
    }

    try {
      await createReview({
        slot_id: slotId,
        is_positive: isPositive,
        comment: values.comment || '',
      });
      reset();
      setIsPositive(true);
      onClose();
    } catch (e) {
      // already caught inside useReviews triggering toast
    }
  };

  const handleClose = () => {
    reset();
    setIsPositive(true);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Fikr-Mulohaza Qoldirish">
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-1.5 border-b-2 border-black pb-4">
          <span className="text-[10px] text-[#38C9E6] font-black tracking-widest uppercase font-montserrat">
            DARS YAKUNIY FIKR-MULOHAZASI
          </span>
          <p className="text-xs text-[#B0BEC5] leading-relaxed mt-1">
            Dars jarayoni mobaynida qilingan tekshiruv, loyiha muhokamasi va sherigingizning ko'rsatgan yordami yuzasidan xolis fikringizni bildiring.
          </p>
        </div>

        <form onSubmit={handleSubmit(onFormSubmit)} className="flex flex-col gap-6">
          {/* Choice selector */}
          <div className="flex flex-col gap-3">
            <label className="text-xs uppercase tracking-wider font-extrabold text-[#B0BEC5] font-montserrat">
              Dars o'tish sifati va ishtiroki
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              <button
                type="button"
                onClick={() => setIsPositive(true)}
                className={`p-3 sm:p-4 min-h-[48px] rounded-2xl border-2 border-black flex flex-row sm:flex-col items-center justify-center gap-2 font-black text-xs transition-all select-none cursor-pointer font-montserrat tracking-wider
                  ${
                    isPositive
                      ? 'bg-[#263E33] text-[#43E8A0] shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]'
                      : 'bg-[#34495E] text-[#B0BEC5] hover:text-white hover:bg-gray-600/30'
                  }
                `}
              >
                <ThumbsUp className="h-5 w-5 shrink-0" />
                <span>IJOBIY (A'LO)</span>
              </button>
              <button
                type="button"
                onClick={() => setIsPositive(false)}
                className={`p-3 sm:p-4 min-h-[48px] rounded-2xl border-2 border-black flex flex-row sm:flex-col items-center justify-center gap-2 font-black text-xs transition-all select-none cursor-pointer font-montserrat tracking-wider
                  ${
                    !isPositive
                      ? 'bg-[#4A2D2D] text-[#FF9B9B] shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]'
                      : 'bg-[#34495E] text-[#B0BEC5] hover:text-white hover:bg-gray-600/30'
                  }
                `}
              >
                <ThumbsDown className="h-5 w-5 shrink-0" />
                <span>SALBIY (YOMON)</span>
              </button>
            </div>
          </div>

          {/* Comment text block */}
          <div className="flex flex-col gap-2 w-full">
            <label className="text-xs uppercase tracking-wider font-extrabold text-[#B0BEC5] flex flex-wrap justify-between items-center gap-1 font-montserrat">
              <span>Fikr-mulohaza (Ixtiyoriy)</span>
              <span className="font-ibm-plex-mono text-xs">{commentVal.length} / 500 ta belgi</span>
            </label>
            <textarea
              className="min-h-[120px] w-full rounded-2xl bg-[#34495E] border-2 border-black p-4 text-sm text-white placeholder:text-[#B0BEC5]/60 focus:outline-none focus:border-[#38C9E6] transition-all duration-150 disabled:opacity-50 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
              placeholder="Sherigingizning ijobiy tomonlari yoki tuzatilishi shart bo'lgan mezonlar haqida batafsil yozib qoldiring..."
              maxLength={500}
              disabled={isCreatingReview}
              {...register('comment')}
            />
            {errors.comment && <span className="text-xs text-[#FF9B9B] mt-0.5 font-bold">{errors.comment.message}</span>}
          </div>

          <Button type="submit" variant="primary" className="w-full mt-2 font-montserrat uppercase tracking-wider font-extrabold" disabled={isCreatingReview}>
            <Send className="h-4 w-4 text-black" /> {isCreatingReview ? 'Yuborilmoqda...' : 'Fikrni yuborish'}
          </Button>
        </form>
      </div>
    </Modal>
  );
}
