import fs from 'fs';
import path from 'path';

import { AD_EVERY, AD_FREE_SCREENS, adsEnabled, interleaveAds } from '@/lib/ads';

const root = path.resolve(__dirname, '..');
const read = (rel: string) => fs.readFileSync(path.join(root, rel), 'utf8');

describe('interleaveAds', () => {
  const items = Array.from({ length: 20 }, (_, i) => i);

  it('puts one ad after every 8 products, never at the end of the list', () => {
    const out = interleaveAds(items, 8, true);
    const adPositions = out.map((r, i) => (r.kind === 'ad' ? i : -1)).filter(i => i >= 0);
    expect(adPositions).toEqual([8, 17]); // 8 ürün, reklam, 8 ürün, reklam, 4 ürün
    expect(out.filter(r => r.kind === 'item')).toHaveLength(20);
    expect(interleaveAds([1, 2, 3, 4, 5, 6, 7, 8], 8, true).some(r => r.kind === 'ad')).toBe(false);
  });

  it('defaults to every 8 and gives each ad a stable unique key', () => {
    expect(AD_EVERY).toBe(8);
    const keys = interleaveAds(items, undefined, true).flatMap(r => (r.kind === 'ad' ? [r.key] : []));
    expect(new Set(keys).size).toBe(keys.length);
  });

  it('adds nothing when ads are off', () => {
    expect(interleaveAds(items, 8, false).every(r => r.kind === 'item')).toBe(true);
  });
});

describe('adsEnabled', () => {
  it('is on by default (test ads) and off with EXPO_PUBLIC_ADS=off', () => {
    expect(adsEnabled(undefined)).toBe(true);
    expect(adsEnabled('test')).toBe(true);
    expect(adsEnabled('off')).toBe(false);
    expect(adsEnabled('OFF')).toBe(false);
  });
});

describe('ad-free core flow', () => {
  // AdSlot'u doğrudan ya da ortak bileşen (ProductRow, ListPicker...) üzerinden çeken ekran olmamalı
  const adUsers = (): string[] => {
    const dirs = ['app', 'components'];
    const files: string[] = [];
    const walk = (d: string) => fs.readdirSync(path.join(root, d), { withFileTypes: true }).forEach(e => {
      const rel = path.join(d, e.name);
      if (e.isDirectory()) walk(rel); else if (/\.tsx?$/.test(e.name)) files.push(rel);
    });
    dirs.forEach(walk);
    return files.filter(f => /AdSlot|@\/lib\/ads/.test(read(f)) && f !== 'components/AdSlot.tsx');
  };

  it.each([...AD_FREE_SCREENS])('%s does not import the ad component or ad helpers', file => {
    expect(fs.existsSync(path.join(root, file))).toBe(true);
    expect(read(file)).not.toMatch(/AdSlot|@\/lib\/ads/);
  });

  it('ad components are used only on home and product-list screens', () => {
    expect(adUsers().sort()).toEqual(['app/(tabs)/index.tsx', 'app/category/[id].tsx', 'app/search.tsx'].sort());
  });

  it('shared components imported by core screens never pull in ads', () => {
    const shared = fs.readdirSync(path.join(root, 'components')).filter(f => f !== 'AdSlot.tsx');
    shared.forEach(f => expect(read(path.join('components', f))).not.toMatch(/AdSlot|@\/lib\/ads/));
  });

  it('uses only the two approved placements', () => {
    const used = new Set<string>();
    adUsers().forEach(f => [...read(f).matchAll(/placement="([\w-]+)"/g)].forEach(m => used.add(m[1])));
    expect([...used].sort()).toEqual(['home-top', 'product-list']);
  });
});
