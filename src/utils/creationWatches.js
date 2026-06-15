const CREATION_WATCHES_SEARCH = 'https://www.creationwatches.com/products/ja/search';

export function creationWatchesSearchUrl(sku) {
  const keyword = String(sku || '').trim();
  if (!keyword) throw new Error('CreationWatches links require a SKU');

  return `${CREATION_WATCHES_SEARCH}?keyword=${encodeURIComponent(keyword)}`;
}
