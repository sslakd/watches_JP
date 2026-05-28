import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://tokeimonogatari.com',
  outDir: './dist',
  build: { format: 'file' },
  integrations: [sitemap()]
});
