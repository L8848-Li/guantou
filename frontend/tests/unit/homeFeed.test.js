import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/services/guantou', () => ({
  getCan: vi.fn(),
  getDiscovery: vi.fn(),
  listCans: vi.fn(),
}));

import { getCan, getDiscovery, listCans } from '@/services/guantou';
import {
  getNameplatePreview,
  getTodayCan,
  listHomeFeed,
  resolveDefaultTab,
} from '@/services/homeFeed';

function setupStorage() {
  const store = {};
  globalThis.uni = {
    getStorageSync: vi.fn((key) => (Object.prototype.hasOwnProperty.call(store, key) ? store[key] : '')),
    setStorageSync: vi.fn((key, value) => {
      store[key] = value;
    }),
    removeStorageSync: vi.fn((key) => {
      delete store[key];
    }),
  };
  globalThis.getApp = vi.fn(() => ({ globalData: {} }));
  return store;
}

describe('homeFeed service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listHomeFeed', () => {
    it('maps the four tabs to feed params with page_size 8', () => {
      listHomeFeed('dialect', 2);
      expect(listCans).toHaveBeenCalledWith({ feed: 'dialect', page: 2, page_size: 8 });

      listHomeFeed('following', 1);
      expect(listCans).toHaveBeenCalledWith({ feed: 'following', page: 1, page_size: 8 });

      listHomeFeed('recommended', 3);
      expect(listCans).toHaveBeenCalledWith({ feed: 'recommended', page: 3, page_size: 8 });

      listHomeFeed('unknown-tab', 1);
      expect(listCans).toHaveBeenCalledWith({ feed: 'recommended', page: 1, page_size: 8 });
    });
  });

  describe('getNameplatePreview', () => {
    it('prefers the list-provided previews and trims to 3', async () => {
      const can = {
        id: 5,
        nameplate_previews: [1, 2, 3, 4, 5].map((id) => ({ id })),
        nameplate_total: 5,
      };

      const result = await getNameplatePreview(5, can);

      expect(result.previews.map((plate) => plate.id)).toEqual([1, 2, 3]);
      expect(result.total).toBe(5);
      expect(getCan).not.toHaveBeenCalled();
    });

    it('falls back to getCan, keeps only active plates sorted by weight', async () => {
      setupStorage();
      getCan.mockResolvedValue({
        nameplates: [
          { id: 1, status: 'active', weight: 3 },
          { id: 2, status: 'rejected', weight: 99 },
          { id: 3, status: 'active', weight: 9 },
          { id: 4, status: 'active', weight: 6 },
          { id: 5, status: 'active', weight: 1 },
        ],
      });

      const result = await getNameplatePreview(9);

      expect(result.previews.map((plate) => plate.id)).toEqual([3, 4, 1]);
      expect(result.total).toBe(4);

      // 第二次命中缓存，不再请求详情
      await getNameplatePreview(9);
      expect(getCan).toHaveBeenCalledTimes(1);
    });
  });

  describe('getTodayCan', () => {
    it('rotates deterministically by day serial and caches per day', async () => {
      const store = setupStorage();
      const hotCans = [{ id: 1 }, { id: 2 }, { id: 3 }];
      getDiscovery.mockResolvedValue({ hot_cans: hotCans });

      const first = await getTodayCan();
      const daySerial = Math.floor(Date.now() / 86400000);
      expect(first).toEqual(hotCans[daySerial % hotCans.length]);
      expect(store.home_today_can).toBeTruthy();

      // 同一天内直接命中缓存
      const again = await getTodayCan();
      expect(again).toEqual(first);
      expect(getDiscovery).toHaveBeenCalledTimes(1);
    });

    it('picks a different can on the next day', async () => {
      setupStorage();
      const hotCans = [{ id: 1 }, { id: 2 }];
      getDiscovery.mockResolvedValue({ hot_cans: hotCans });
      const baseSerial = Math.floor(Date.now() / 86400000);
      const expectedToday = hotCans[baseSerial % 2];
      const expectedTomorrow = hotCans[(baseSerial + 1) % 2];

      const first = await getTodayCan();
      expect(first).toEqual(expectedToday);

      // 模拟跨天：清掉当日缓存，并把 Date.now 拨到第二天
      uni.removeStorageSync('home_today_can');
      const nowSpy = vi.spyOn(Date, 'now').mockReturnValue((baseSerial + 1) * 86400000);
      try {
        const next = await getTodayCan();
        expect(next).toEqual(expectedTomorrow);
      } finally {
        nowSpy.mockRestore();
      }
    });

    it('falls back to the first recommended can when discovery fails', async () => {
      setupStorage();
      getDiscovery.mockRejectedValue(new Error('discovery down'));
      listCans.mockResolvedValue({ results: [{ id: 42 }] });

      const can = await getTodayCan();

      expect(can).toEqual({ id: 42 });
      expect(listCans).toHaveBeenCalledWith({ feed: 'recommended', page: 1, page_size: 1 });
    });
  });

  describe('resolveDefaultTab', () => {
    it('returns dialect when a primary dialect is set', () => {
      expect(resolveDefaultTab({ primary_dialect: { id: 1 } })).toBe('dialect');
    });

    it('returns recommended for users without a primary dialect', () => {
      expect(resolveDefaultTab({})).toBe('recommended');
      expect(resolveDefaultTab(null)).toBe('recommended');
    });

    it('reads getApp globalData when no argument is given', () => {
      globalThis.getApp = vi.fn(() => ({
        globalData: { userInfo: { primary_dialect: { id: 2 } } },
      }));
      expect(resolveDefaultTab()).toBe('dialect');

      globalThis.getApp = vi.fn(() => ({ globalData: {} }));
      expect(resolveDefaultTab()).toBe('recommended');
    });
  });
});
