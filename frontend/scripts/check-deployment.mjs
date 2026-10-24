import { readFileSync } from 'node:fs';

const config = JSON.parse(readFileSync(new URL('../vercel.json', import.meta.url), 'utf8'));
const route = config.rewrites.find(entry => entry.source === '/api/:path*');
const target = route && new URL(route.destination);
if (!target || target.protocol !== 'https:' || target.hostname.endsWith('.invalid')
    || target.hostname === 'localhost' || target.username || target.password
    || target.pathname !== '/api/:path*' || target.search || target.hash) {
  console.error('Configure the Oracle HTTPS origin first: python scripts/configure_vercel.py https://YOUR_BACKEND_HOST (from the repository root).');
  process.exit(1);
}
console.log('Vercel API proxy configuration is valid. Live connectivity is checked after deployment.');
