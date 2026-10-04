const fs = require('fs');

const enKeys = {
  reload: 'Reload',
  profile: {
    student: 'Student',
    coreProgram: 'Core Program',
    levelProgress: 'Level Progress',
  },
  stats: {
    coalition: 'Coalition',
    noCoalition: 'No Coalition',
    peerPoints: 'Peer Points',
    experience: 'Experience',
    location: 'Location',
    offline: 'Offline',
  },
  schedule: {
    title: 'My Schedule',
    viewAll: 'View All',
    empty: 'No scheduled slots yet',
    addSlot: 'Create Slot',
    reviewer: 'Reviewer',
    reviewee: 'Reviewee',
    statusOpen: 'Open',
    statusBooked: 'Booked',
    statusActive: 'Active',
  },
};

const uzKeys = {
  reload: 'Qayta yuklash',
  profile: {
    student: 'Talaba',
    coreProgram: 'Asosiy dastur',
    levelProgress: 'Daraja o\'sishi',
  },
  stats: {
    coalition: 'Koalitsiya',
    noCoalition: 'Koalitsiya yo\'q',
    peerPoints: 'Peer ballari',
    experience: 'Tajriba',
    location: 'Joylashuv',
    offline: 'Oflayn',
  },
  schedule: {
    title: 'Mening jadvalim',
    viewAll: 'Barchasini ko\'rish',
    empty: 'Hali rejalashtirilgan slotlar yo\'q',
    addSlot: 'Slot yaratish',
    reviewer: 'Reviewer',
    reviewee: 'Reviewee',
    statusOpen: 'Ochiq',
    statusBooked: 'Band qilingan',
    statusActive: 'Faol',
  },
};

const ruKeys = {
  reload: 'Обновить',
  profile: {
    student: 'Студент',
    coreProgram: 'Основная программа',
    levelProgress: 'Прогресс уровня',
  },
  stats: {
    coalition: 'Коалиция',
    noCoalition: 'Без коалиции',
    peerPoints: 'Пир Поинты',
    experience: 'Опыт',
    location: 'Локация',
    offline: 'Офлайн',
  },
  schedule: {
    title: 'Мое расписание',
    viewAll: 'Смотреть все',
    empty: 'Пока нет запланированных слотов',
    addSlot: 'Создать слот',
    reviewer: 'Ревьюер',
    reviewee: 'Ревьюи',
    statusOpen: 'Открыт',
    statusBooked: 'Забронирован',
    statusActive: 'Активен',
  },
};

function injectKeys(filePath, keys) {
  let content = fs.readFileSync(filePath, 'utf8');
  // Find "dashboard: {" and insert the stringified keys right after
  let keysStr = JSON.stringify(keys, null, 2);
  // strip outer {}
  keysStr = keysStr.substring(1, keysStr.length - 1) + ',';
  
  content = content.replace(/dashboard:\s*\{/, "dashboard: {" + keysStr);
  fs.writeFileSync(filePath, content);
}

injectKeys('src/shared/lib/i18n/locales/uz.ts', uzKeys);
injectKeys('src/shared/lib/i18n/locales/en.ts', enKeys);
injectKeys('src/shared/lib/i18n/locales/ru.ts', ruKeys);

