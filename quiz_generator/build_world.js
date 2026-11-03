// world-atlas JSON faylini brauzer o'qiy oladigan world.js ga aylantiradi (file:// da fetch ishlamaydi)
const fs = require('fs'), path = require('path');
const src = path.join(__dirname, 'node_modules/world-atlas/countries-50m.json');
const dst = path.join(__dirname, 'node_modules/world-atlas/world.js');
fs.writeFileSync(dst, 'window.WORLD=' + fs.readFileSync(src, 'utf8') + ';');
console.log('world.js tayyor');
