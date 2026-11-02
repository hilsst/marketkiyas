import { ACCOUNT_REASON_TEXT, accountRedirect, isGuest } from '@/lib/guest';
import type { User } from '@/lib/api';

const user = (over: Partial<User> = {}): User => ({ id: 1, email: 'a@b.co', full_name: null, has_password: true, is_guest: false, ...over });
const guest = user({ email: null, has_password: false, is_guest: true });

describe('guest start', () => {
  it('knows who is a guest', () => {
    expect(isGuest(guest)).toBe(true);
    expect(isGuest(user())).toBe(false);
    expect(isGuest(null)).toBe(false);
  });

  it('asks a guest to open an account at save and share moments, keeping the reason', () => {
    for (const reason of ['share', 'join', 'family', 'save', 'plan'] as const) {
      expect(accountRedirect(guest, reason)).toEqual({ pathname: '/login', params: { upgrade: '1', reason } });
      expect(ACCOUNT_REASON_TEXT[reason]).toMatch(/hesap/i);
    }
  });

  it('never interrupts a registered user', () => {
    expect(accountRedirect(user(), 'save')).toBeNull();
    expect(accountRedirect(user(), 'share')).toBeNull();
  });

  it('sends a signed-out (offline) user to the normal login', () => {
    expect(accountRedirect(null, 'save')).toEqual({ pathname: '/login', params: { reason: 'save' } });
  });
});
