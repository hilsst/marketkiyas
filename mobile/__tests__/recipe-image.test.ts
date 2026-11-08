import { resolveImageUrl } from '@/components/RecipeImage';
import { API_URL } from '@/lib/api';

describe('resolveImageUrl', () => {
  it('tam adresi olduğu gibi bırakır', () => {
    expect(resolveImageUrl('https://cdn.example.com/a.jpg')).toBe('https://cdn.example.com/a.jpg');
  });
  it('göreli yolu API adresine ekler', () => {
    expect(resolveImageUrl('/media/recipes/x.jpg')).toBe(`${API_URL}/media/recipes/x.jpg`);
  });
});
