// world-atlas JSON faylini brauzer o'qiy oladigan world.js ga aylantiradi (file:// da fetch ishlamaydi)
const fs = require('fs'), path = require('path');
const src = path.join(__dirname, 'node_modules/world-atlas/countries-50m.json');
const dst = path.join(__dirname, 'node_modules/world-atlas/world.js');
fs.writeFileSync(dst, 'window.WORLD=' + fs.readFileSync(src, 'utf8') + ';');
fs.writeFileSync(path.join(__dirname, 'node_modules/world-atlas/world110.js'),
  'window.WORLD110=' + fs.readFileSync(path.join(__dirname, 'node_modules/world-atlas/land-110m.json'), 'utf8') + ';');
console.log('world.js tayyor');
