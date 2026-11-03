import * as Location from 'expo-location';

import { distanceKm, formatKm, getCoords, inTurkey } from '@/lib/location';

jest.mock('expo-location', () => ({
  getForegroundPermissionsAsync: jest.fn(),
  requestForegroundPermissionsAsync: jest.fn(),
  getLastKnownPositionAsync: jest.fn(),
  getCurrentPositionAsync: jest.fn(),
  Accuracy: { Balanced: 3 },
}));
const mocked = Location as unknown as Record<string, jest.Mock>;

describe('location', () => {
  beforeEach(() => jest.resetAllMocks());

  it('inTurkey sunucunun kabul ettiği sınırlarla aynı', () => {
    expect(inTurkey({ lat: 40.98, lon: 29.02 })).toBe(true);
    expect(inTurkey({ lat: 37.4, lon: -122 })).toBe(false);
  });

  it('izin verilmezse denied döner ve konum istenmez', async () => {
    mocked.getForegroundPermissionsAsync.mockResolvedValue({ granted: false, canAskAgain: true });
    mocked.requestForegroundPermissionsAsync.mockResolvedValue({ granted: false, canAskAgain: false });
    expect(await getCoords()).toEqual({ coords: null, reason: 'denied' });
    expect(mocked.getLastKnownPositionAsync).not.toHaveBeenCalled();
  });

  it('Türkiye dışı konum (örn. emülatör) outside döner', async () => {
    mocked.getForegroundPermissionsAsync.mockResolvedValue({ granted: true, canAskAgain: true });
    mocked.getLastKnownPositionAsync.mockResolvedValue({ coords: { latitude: 37.4, longitude: -122 } });
    expect(await getCoords()).toEqual({ coords: null, reason: 'outside' });
  });

  it('izin varsa son bilinen konumu verir', async () => {
    mocked.getForegroundPermissionsAsync.mockResolvedValue({ granted: true, canAskAgain: true });
    mocked.getLastKnownPositionAsync.mockResolvedValue({ coords: { latitude: 40.98, longitude: 29.02 } });
    expect(await getCoords()).toEqual({ coords: { lat: 40.98, lon: 29.02 } });
  });
});

describe('distanceKm', () => {
  it('ölçülü mesafe verir', () => {
    expect(distanceKm({ lat: 41, lon: 29 }, { lat: 41, lon: 29 })).toBeCloseTo(0, 5);
    expect(distanceKm({ lat: 41, lon: 29 }, { lat: 42, lon: 29 })).toBeCloseTo(111.2, 0);
  });
  it('biçimlendirir', () => {
    expect(formatKm(0.42)).toBe('0,4 km');
    expect(formatKm(12.4)).toBe('12 km');
  });
});
