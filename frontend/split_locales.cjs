const fs = require('fs');

const content = fs.readFileSync('/home/farrukh/.gemini/antigravity-cli/brain/ff186a67-5cbe-4229-8dd6-61d6213dadef/scratch/i18n_input.ts', 'utf8');

// The file looks like:
// const resources = {
//   en: { translation: { ... } },
//   ru: { translation: { ... } },
//   uz: { translation: { ... } }
// };

// I will extract them using regex or eval
try {
  // strip imports
  const code = content.replace(/import .*/g, '').replace(/export default .*/g, '').replace(/i18n\s*\.use.*/gs, '').replace(/const savedLanguage.*/g, '');
  
  // We can just eval the resources object
  const sandbox = {};
  eval(code + '\n sandbox.resources = resources;');
  
  fs.writeFileSync('src/shared/lib/i18n/locales/en.ts', 'export const en = ' + JSON.stringify(sandbox.resources.en.translation, null, 2) + ';\n');
  fs.writeFileSync('src/shared/lib/i18n/locales/ru.ts', 'export const ru = ' + JSON.stringify(sandbox.resources.ru.translation, null, 2) + ';\n');
  fs.writeFileSync('src/shared/lib/i18n/locales/uz.ts', 'export const uz = ' + JSON.stringify(sandbox.resources.uz.translation, null, 2) + ';\n');
  console.log("Successfully extracted and wrote all locales!");
} catch (err) {
  console.error("Failed to eval:", err);
}
