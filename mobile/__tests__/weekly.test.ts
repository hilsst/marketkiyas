jest.mock('expo-secure-store', () => ({ getItemAsync: jest.fn(), setItemAsync: jest.fn(), deleteItemAsync: jest.fn() }));

import { weeklyContent, WEEKLY_HOUR, WEEKLY_WEEKDAY } from '@/lib/weekly';

describe('weekly menu notification', () => {
  it('shows last plan cost when known', () => {
    const c = weeklyContent(1240.4);
    expect(c.body).toMatch(/^Bu haftanın menüsü hazır: 1\.240 TL$/);
    expect(c.data).toEqual({ url: '/meals' });
  });

  it('falls back to an invitation when no plan cost is known', () => {
    for (const total of [null, undefined, 0]) {
      expect(weeklyContent(total).body).toMatch(/^Bu haftanın menüsünü kur/);
    }
  });

  it('fires on Sunday morning', () => {
    expect(WEEKLY_WEEKDAY).toBe(1); // expo-notifications: Pazar = 1
    expect(WEEKLY_HOUR).toBe(11);
  });
});
