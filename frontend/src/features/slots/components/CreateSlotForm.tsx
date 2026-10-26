import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Project, SlotCreate } from '@/shared/types/api';
import { Button, Input, Select } from '@/shared/ui';
import { triggerToast } from '@/shared/stores/toast';

interface CreateSlotFormProps {
  teachableProjects: Project[];
  userCampus?: string | null;
  onSubmit: (data: SlotCreate) => Promise<void>;
  isSubmitting?: boolean;
  initialStartTime?: string;
}

const slotSchema = z.object({
  reviewer_project: z.string().min(1, 'Loyiha nomini tanlash majburiy'),
  start_time: z.string().min(1, 'Boshlanish vaqtini tanlash majburiy'),
  is_online: z.boolean(),
});

type FormValues = z.infer<typeof slotSchema>;

export function CreateSlotForm({
  teachableProjects,
  userCampus,
  onSubmit,
  isSubmitting = false,
  initialStartTime,
}: CreateSlotFormProps) {
  const isTashkent = userCampus?.toLowerCase() === 'tashkent';

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(slotSchema),
    defaultValues: {
      reviewer_project: '',
      start_time: initialStartTime || '',
      is_online: isTashkent ? true : false,
    },
  });

  // Prefill initialStartTime inside useEffect when it changes
  useEffect(() => {
    if (initialStartTime) {
      setValue('start_time', initialStartTime);
    }
  }, [initialStartTime, setValue]);

  // Force is_online true for Tashkent campus
  useEffect(() => {
    if (isTashkent) {
      setValue('is_online', true);
    }
  }, [isTashkent, setValue]);

  const onFormSubmit = async (values: FormValues) => {
    try {
      const startDt = new Date(values.start_time);
      if (isNaN(startDt.getTime())) {
        triggerToast("Boshlanish vaqti noto'g'ri kiritilgan", 'error');
        return;
      }
      if (startDt.getTime() < Date.now()) {
        triggerToast("Boshlanish vaqti o'tib ketgan bo'lishi mumkin emas", 'error');
        return;
      }
      const endDt = new Date(startDt.getTime() + 60 * 60 * 1000);

      await onSubmit({
        reviewer_project: values.reviewer_project,
        start_time: startDt.toISOString(),
        end_time: endDt.toISOString(),
        is_online: values.is_online,
      });
    } catch (_e) {
      // Handled
    }
  };

  return (
    <form onSubmit={handleSubmit(onFormSubmit)}>
      <fieldset disabled={isSubmitting} className="flex flex-col gap-4 sm:gap-5 disabled:opacity-60 transition-opacity">
        {/* Project selector */}
        <Select
          label="Siz o'rgata oladigan loyiha"
          error={errors.reviewer_project?.message}
          {...register('reviewer_project')}
        >
          <option value="" disabled className="bg-[#1E2A38]">-- Tanlang --</option>
          {teachableProjects.map((proj) => (
            <option key={proj.id || proj.title} value={proj.title} className="bg-[#34495E]">
              {proj.title}
            </option>
          ))}
        </Select>

        {/* Start Date Selection */}
        <Input
          type="datetime-local"
          label="Dars boshlanish vaqti"
          error={errors.start_time?.message}
          placeholder="Vaqtni tanlang"
          {...register('start_time')}
        />

        {/* Online/Offline Toggle */}
        <div className="flex flex-col gap-1.5 p-3 rounded-xl bg-[#1E2A38] border-2 border-black">
          <label className="flex items-center gap-3 cursor-pointer select-none min-h-[44px]">
            <input
              type="checkbox"
              disabled={isTashkent || isSubmitting}
              className="h-5 w-5 rounded border-black text-[#38C9E6] accent-[#38C9E6] cursor-pointer flex-shrink-0"
              {...register('is_online')}
            />
            <div className="flex flex-col">
              <span className="text-sm font-semibold text-[#FFFFFF]">Onlayn dars</span>
              <span className="text-[10px] text-[#B0BEC5]">Masofaviy yoki telegram orqali P2P dars</span>
            </div>
          </label>
          {isTashkent && (
            <span className="text-[10px] text-[#38C9E6] uppercase tracking-wider font-semibold font-mono mt-1">
              * Tashkent campusi faqat onlayn rejimlarni qo'llab-quvvatlaydi.
            </span>
          )}
        </div>

        <div className="pt-2">
          <Button type="submit" variant="primary" className="w-full min-h-[44px]" disabled={isSubmitting}>
            {isSubmitting ? 'Yaratilmoqda...' : 'Slotni tasdiqlash'}
          </Button>
        </div>
      </fieldset>
    </form>
  );
}
export default CreateSlotForm;
