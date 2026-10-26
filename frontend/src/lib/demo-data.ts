export type MarketSlug = "bim" | "a101" | "sok" | "file";
export interface Market { slug: MarketSlug; name: string; color: string; }
export interface ProductGroup { id: number; name: string; category: string;
  unit: string; unitValue: number; display: string; emoji: string; }
export interface Product { id: number; groupId: number; market: MarketSlug;
  brand: string; price: number; oldPrice?: number; isPromo: boolean; inStock: boolean; }
export interface ListItem { id: number; groupId: number; quantity: number;
  isChecked: boolean; preferredMarket?: MarketSlug; preferredProductId?: number; }
export interface ShoppingList { id: number; name: string; items: ListItem[]; }

export const MARKETS: Market[] = [
  { slug: "bim",  name: "BİM",  color: "#dc2626" },
  { slug: "a101", name: "A101", color: "#0284c7" },
  { slug: "sok",  name: "Şok",  color: "#ea580c" },
  { slug: "file", name: "File", color: "#4338ca" },
];
export const MARKET_MAP: Record<MarketSlug, Market> =
  Object.fromEntries(MARKETS.map(m => [m.slug, m])) as any;

export const CATEGORIES = ["Tümü","Süt Ürünleri","Ekmek & Fırın","Temizlik","Yağ & Bakliyat"];

export const GROUPS: ProductGroup[] = [
  { id: 1,  name: "Tam Yağlı Süt 1L",        category: "Süt Ürünleri",  unit: "ml",  unitValue: 1000, display: "1 L",  emoji: "🥛" },
  { id: 2,  name: "Yarım Yağlı Süt 1L",      category: "Süt Ürünleri",  unit: "ml",  unitValue: 1000, display: "1 L",  emoji: "🥛" },
  { id: 3,  name: "Yumurta 15'li",           category: "Süt Ürünleri",  unit: "adet", unitValue: 15,  display: "15'li", emoji: "🥚" },
  { id: 4,  name: "Beyaz Ekmek 200g",        category: "Ekmek & Fırın", unit: "g",   unitValue: 200,  display: "200 g", emoji: "🍞" },
  { id: 5,  name: "Tam Buğday Ekmek",        category: "Ekmek & Fırın", unit: "g",   unitValue: 350,  display: "350 g", emoji: "🍞" },
  { id: 6,  name: "Sıvı Bulaşık Det. 750ml", category: "Temizlik",      unit: "ml",  unitValue: 750,  display: "750 ml", emoji: "🧴" },
  { id: 7,  name: "Çamaşır Det. 3L",         category: "Temizlik",      unit: "ml",  unitValue: 3000, display: "3 L",  emoji: "🧺" },
  { id: 8,  name: "Ayçiçek Yağı 1L",         category: "Yağ & Bakliyat", unit: "ml", unitValue: 1000, display: "1 L",  emoji: "🌻" },
  { id: 9,  name: "Pirinç 1kg",              category: "Yağ & Bakliyat", unit: "g",  unitValue: 1000, display: "1 kg", emoji: "🍚" },
  { id: 10, name: "Makarna 500g",            category: "Yağ & Bakliyat", unit: "g",  unitValue: 500,  display: "500 g", emoji: "🍝" },
];

export const PRODUCTS: Product[] = [
  { id:101, groupId:1,  market:"bim",  brand:"Dost",       price:31.90, isPromo:false, inStock:true },
  { id:102, groupId:1,  market:"a101", brand:"Sütaş",      price:32.50, isPromo:false, inStock:true },
  { id:103, groupId:1,  market:"sok",  brand:"Pınar",      price:34.00, isPromo:false, inStock:true },
  { id:104, groupId:1,  market:"file", brand:"İçim",       price:36.75, isPromo:false, inStock:true },
  { id:201, groupId:2,  market:"bim",  brand:"Dost",       price:30.50, isPromo:false, inStock:true },
  { id:202, groupId:2,  market:"a101", brand:"Sütaş",      price:31.00, isPromo:false, inStock:true },
  { id:203, groupId:2,  market:"sok",  brand:"Pınar",      price:32.50, isPromo:false, inStock:true },
  { id:301, groupId:3,  market:"bim",  brand:"Keskinoğlu", price:42.50, isPromo:false, inStock:true },
  { id:302, groupId:3,  market:"a101", brand:"Yumurta",    price:43.90, isPromo:false, inStock:true },
  { id:303, groupId:3,  market:"sok",  brand:"Ceyhan",     price:45.00, isPromo:false, inStock:true },
  { id:304, groupId:3,  market:"file", brand:"Güres",      price:48.00, isPromo:false, inStock:true },
  { id:401, groupId:4,  market:"bim",  brand:"Uno",        price:12.50, isPromo:false, inStock:true },
  { id:402, groupId:4,  market:"a101", brand:"Uno",        price:12.00, isPromo:false, inStock:true },
  { id:403, groupId:4,  market:"sok",  brand:"Halk",       price:12.50, isPromo:false, inStock:true },
  { id:404, groupId:4,  market:"file", brand:"Uno",        price:14.00, isPromo:false, inStock:true },
  { id:501, groupId:5,  market:"bim",  brand:"Uno",        price:18.50, isPromo:false, inStock:true },
  { id:502, groupId:5,  market:"a101", brand:"Eti",        price:17.90, isPromo:false, inStock:true },
  { id:503, groupId:5,  market:"file", brand:"Uno",        price:21.00, isPromo:false, inStock:true },
  { id:601, groupId:6,  market:"bim",  brand:"Fairy",      price:65.00, isPromo:false, inStock:true },
  { id:602, groupId:6,  market:"a101", brand:"Finish",     price:58.90, oldPrice:72.00, isPromo:true, inStock:true },
  { id:603, groupId:6,  market:"sok",  brand:"Pril",       price:62.00, isPromo:false, inStock:true },
  { id:604, groupId:6,  market:"file", brand:"Fairy",      price:69.90, isPromo:false, inStock:true },
  { id:701, groupId:7,  market:"bim",  brand:"Omo",        price:189.00, isPromo:false, inStock:true },
  { id:702, groupId:7,  market:"a101", brand:"Persil",     price:175.00, oldPrice:210.00, isPromo:true, inStock:true },
  { id:703, groupId:7,  market:"sok",  brand:"Ariel",      price:199.90, isPromo:false, inStock:true },
  { id:704, groupId:7,  market:"file", brand:"Omo",        price:210.00, isPromo:false, inStock:true },
  { id:801, groupId:8,  market:"bim",  brand:"Yudum",      price:89.50, isPromo:false, inStock:true },
  { id:802, groupId:8,  market:"a101", brand:"Kırlangıç",  price:85.00, isPromo:false, inStock:true },
  { id:803, groupId:8,  market:"sok",  brand:"Bizim",      price:88.00, isPromo:false, inStock:true },
  { id:804, groupId:8,  market:"file", brand:"Torku",      price:92.00, isPromo:false, inStock:true },
  { id:901, groupId:9,  market:"bim",  brand:"Duru",       price:42.00, isPromo:false, inStock:true },
  { id:902, groupId:9,  market:"a101", brand:"Torku",      price:40.50, isPromo:false, inStock:true },
  { id:903, groupId:9,  market:"sok",  brand:"Reis",       price:43.00, isPromo:false, inStock:true },
  { id:904, groupId:9,  market:"file", brand:"Duru",       price:45.00, isPromo:false, inStock:true },
  { id:1001,groupId:10, market:"bim",  brand:"Filiz",      price:8.90,  isPromo:false, inStock:true },
  { id:1002,groupId:10, market:"a101", brand:"Filiz",      price:8.50,  isPromo:false, inStock:true },
  { id:1003,groupId:10, market:"sok",  brand:"Barilla",    price:9.00,  isPromo:false, inStock:true },
  { id:1004,groupId:10, market:"file", brand:"Filiz",      price:10.50, isPromo:false, inStock:true },
];

export function priceHistory(productId: number, basePrice: number): number[] {
  const arr: number[] = [];
  for (let i = 0; i < 30; i++) {
    const wobble = Math.sin((productId + i) * 0.7) * (basePrice * 0.05);
    const trend  = (i / 30) * (basePrice * 0.03);
    arr.push(Math.max(basePrice * 0.85, basePrice - wobble + trend));
  }
  arr[29] = basePrice;
  return arr;
}

export const SEED_LISTS: ShoppingList[] = [
  { id: 1, name: "Haftalık Alışveriş", items: [
    { id:1, groupId:1,  quantity:1, isChecked:false },
    { id:2, groupId:3,  quantity:2, isChecked:false },
    { id:3, groupId:4,  quantity:1, isChecked:false },
    { id:4, groupId:6,  quantity:1, isChecked:false },
    { id:5, groupId:7,  quantity:1, isChecked:false },
    { id:6, groupId:8,  quantity:1, isChecked:false },
    { id:7, groupId:9,  quantity:1, isChecked:false },
    { id:8, groupId:10, quantity:2, isChecked:false },
  ]},
  { id: 2, name: "Hafta Sonu", items: [
    { id:9,  groupId:2, quantity:1, isChecked:false },
    { id:10, groupId:5, quantity:1, isChecked:false },
    { id:11, groupId:10,quantity:1, isChecked:false },
  ]},
];
