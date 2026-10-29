/**
 * Native reklam yeri. Kemal'in istediği yerler: ana sayfada üst barın altı ("home-top"), kategorilerin bitimi
 * ("home-categories"), alt kategori listelerinde her 4 üründe bir ("list"). AppLovin MAX native reklamı 8. adımda
 * buraya bağlanır; şimdilik yer tutmaz (hiçbir şey çizmez), böylece ekran düzeni şimdiden reklam yerlerini bilir.
 */
export type AdPlacement = 'home-top' | 'home-categories' | 'list';

export default function AdSlot(_: { placement: AdPlacement }) {
  return null;
}
