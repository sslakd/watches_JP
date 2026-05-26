import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://tokeimonogatari.com',
  outDir: './dist',
  build: { format: 'file' }
});
