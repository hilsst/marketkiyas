import { NEW_LOOK } from '@/constants/Look';

// Ucuzu tasarım belirteçleri: derin zümrüt yeşil, turuncu yalnız indirim/fırsat için.
const brand = '#0B7C56';

const classic = {
  light: {
    text: '#0F1F19',
    textMuted: '#55645D',
    background: '#F5F8F6',
    card: '#FFFFFF',
    border: '#E6ECE8',
    tint: brand,
    tintDark: '#085C40',
    tintSoft: '#E4F5EC',
    accent: '#B94E05',
    accentSoft: '#FFF0E3',
    accentText: '#8A4A12',
    tabIconDefault: '#6B7A73',
    tabIconSelected: brand,
    danger: '#C62828',
    onTint: '#FFFFFF',
    info: '#075985',
    shadow: '#0F1F19',
    sage: '#0B7C56',
    sageText: '#FFFFFF',
    celebrate: '#047857',
  },
  dark: {
    text: '#F2F7F4',
    textMuted: '#93A39B',
    background: '#0B120F',
    card: '#141D18',
    border: '#24312A',
    tint: '#34D399',
    tintDark: '#6EE7B7',
    tintSoft: '#12302440',
    accent: '#B94E05',
    accentSoft: '#3A2410',
    accentText: '#FFB878',
    tabIconDefault: '#8EA097',
    tabIconSelected: '#34D399',
    danger: '#F87171',
    onTint: '#04251A',
    info: '#7DD3FC',
    shadow: '#000000',
    sage: '#34D399',
    sageText: '#04251A',
    celebrate: '#047857',
  },
};

const ink = '#2A2840';

const pastel = {
  light: {
    text: ink,
    textMuted: '#625F78',
    background: '#FFF8F0',
    card: '#FFFFFF',
    border: '#EDE4DA',
    tint: ink,
    tintDark: '#53479A',
    tintSoft: '#E1DCF8',
    accent: '#B94E05',
    accentSoft: '#FFDCCB',
    accentText: '#8A4A2F',
    tabIconDefault: '#7A7790',
    tabIconSelected: ink,
    danger: '#C62828',
    onTint: '#FFF8F0',
    info: '#2D5F86',
    shadow: ink,
    sage: '#D3EBDD',
    sageText: '#2F6B52',
    celebrate: '#53479A',
  },
  // Koyu tema: sıcak mor-lacivert zemin, pastel vurgular, bir kademe daha açık kartlar.
  dark: {
    text: '#F3F0FA',
    textMuted: '#B4B0C8',
    background: '#1C1A30',
    card: '#27253F',
    border: '#3A3758',
    tint: '#D9D2F8',
    tintDark: '#C9C0F5',
    tintSoft: '#3B3668',
    accent: '#D9692A',
    accentSoft: '#4A3128',
    accentText: '#FFC9A8',
    tabIconDefault: '#9C98B5',
    tabIconSelected: '#D9D2F8',
    danger: '#FF8A8A',
    onTint: '#1C1A30',
    info: '#9CCBF0',
    shadow: '#000000',
    sage: '#2B4A40',
    sageText: '#CDEFDD',
    celebrate: '#3B3668',
  },
};

// Eski zümrüt tema `classic` içinde duruyor; NEW_LOOK=false yapınca geri gelir.
export default NEW_LOOK ? pastel : classic;
