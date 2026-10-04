const fs = require('fs');
const path = require('path');

const localesDir = path.join(__dirname, 'src/shared/lib/i18n/locales');
const langs = ['uz', 'ru', 'en'];

langs.forEach(lang => {
  const filePath = path.join(localesDir, `${lang}.ts`);
  const content = fs.readFileSync(filePath, 'utf8');
  
  // Extract the exported object
  const sandbox = {};
  // The file has "export const uz = { ... };"
  // We'll replace "export const uz =" with "sandbox.obj ="
  const code = content.replace(new RegExp(`export const ${lang} =`), 'sandbox.obj =');
  eval(code);
  
  const dict = sandbox.obj;
  const langDir = path.join(localesDir, lang);
  if (!fs.existsSync(langDir)) {
    fs.mkdirSync(langDir);
  }
  
  let indexContent = '';
  let exportObj = 'export const ' + lang + ' = {\n';
  
  for (const [key, value] of Object.entries(dict)) {
    const featureFilePath = path.join(langDir, `${key}.ts`);
    const featureContent = `export default ${JSON.stringify(value, null, 2)};\n`;
    fs.writeFileSync(featureFilePath, featureContent);
    
    indexContent += `import ${key} from './${key}';\n`;
    exportObj += `  ${key},\n`;
  }
  
  exportObj += '};\n';
  fs.writeFileSync(path.join(langDir, 'index.ts'), indexContent + '\n' + exportObj);
  
  // Delete the old monolithic file
  fs.unlinkSync(filePath);
});

console.log("Successfully split all locales into feature-based files!");
