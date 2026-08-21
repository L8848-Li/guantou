import { expect, test } from '@playwright/test';

/** 生成 0.5s 单声道 WAV 的 data URI，保证 H5 播放断言不依赖外网资源 */
function tinyWavDataUri() {
  const sampleRate = 8000;
  const samples = 4000;
  const data = Buffer.alloc(samples * 2);
  for (let i = 0; i < samples; i += 1) {
    data.writeInt16LE(Math.round(Math.sin(i / 8) * 3000), i * 2);
  }
  const header = Buffer.alloc(44);
  header.write('RIFF', 0);
  header.writeUInt32LE(36 + data.length, 4);
  header.write('WAVE', 8);
  header.write('fmt ', 12);
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);
  header.writeUInt16LE(1, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(sampleRate * 2, 28);
  header.writeUInt16LE(2, 32);
  header.writeUInt16LE(16, 34);
  header.write('data', 36);
  header.writeUInt32LE(data.length, 40);
  return `data:audio/wav;base64,${Buffer.concat([header, data]).toString('base64')}`;
}

test('guest browses immersive feed, plays audio, and opens search', async ({ page }) => {
  const canItem = {
    id: 11,
    audio_url: tinyWavDataUri(),
    concept_text: '舒服',
    duration_ms: 3200,
    nameplate_count: 3,
    nameplate_total: 3,
    nameplate_previews: [
      {
        id: 21,
        display_text: '巴适',
        definition: '安逸、舒服',
        weight: 5,
        support_count: 12,
        supported_by_current_user: false,
      },
      {
        id: 22,
        display_text: '巴适得板',
        definition: '非常舒服',
        weight: 3,
        support_count: 8,
        supported_by_current_user: false,
      },
      {
        id: 23,
        display_text: '安逸得很',
        definition: '舒适惬意',
        weight: 2,
        support_count: 5,
        supported_by_current_user: false,
      },
    ],
    primary_nameplate: { display_text: '巴适' },
    recorder: { id: 3, username: 'guest_author', nickname: '乡友老张', avatar: '' },
    submitted_dialect: { qualified_code: '西南官话.四川' },
    status: 'verified',
    like_count: 2,
    comment_count: 1,
    use_count: 0,
    liked_by_me: false,
    views: 8,
  };

  await page.route('**/search/hot/**', async (route) => {
    await route.fulfill({ json: [{ keyword: '月亮', rank: 1 }] });
  });
  await page.route('**/search/suggest/**', async (route) => {
    await route.fulfill({
      json: {
        keyword: '月亮',
        suggestions: [{ type: 'flavor', id: 21, text: '月亮', sub: '义项' }],
      },
    });
  });
  await page.route(/\/search\/?(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      json: {
        keyword: '月亮',
        flavors: [{
          id: 21,
          name: '月亮义项',
          definition: '地球的天然卫星',
          pronunciations: [],
          package_links: [],
        }],
        packages: [],
        cans: [],
      },
    });
  });
  await page.route('**/discovery/**', async (route) => {
    await route.fulfill({
      json: {
        // 与 DiscoveryView 实际契约对齐：hot_cans/hot_flavors/daily_flavor/topics
        hot_cans: [canItem],
        hot_flavors: [],
        daily_flavor: null,
        topics: [],
      },
    });
  });
  await page.route('**/cans/**', async (route) => {
    await route.fulfill({
      json: {
        count: 1,
        next: null,
        previous: null,
        results: [canItem],
      },
    });
  });
  /*
   * Playwright route 后注册先匹配：
   * 这条更精确的 /cans/11/ 详情路由必须注册在 **\/cans/** 通配之后，
   * 否则会先被通配规则拦截。
   */
  await page.route('**/cans/11/**', async (route) => {
    await route.fulfill({
      json: {
        ...canItem,
        nameplates: [{
          id: 21,
          display_text: '巴适',
          definition: '安逸、舒服',
          weight: 5,
          support_count: 12,
          supported_by_current_user: false,
          status: 'active',
        }],
        comments: [],
      },
    });
  });

  await page.goto('/');
  /* 铭牌写法和释义是首页权威内容，concept_text 只保留为旧数据兜底。 */
  await expect(page.getByRole('tab', { name: '推荐', selected: true })).toBeVisible();
  await expect(page.getByText('巴适', { exact: true })).toBeVisible();
  await expect(page.getByText('安逸、舒服', { exact: true })).toBeVisible();
  /* 副铭牌以紧凑形态与主铭牌同屏展示 */
  await expect(page.getByText('巴适得板', { exact: true })).toBeVisible();
  await expect(page.getByText('安逸得很', { exact: true })).toBeVisible();
  await expect(page.getByText('支持 12')).toBeVisible();
  /* Issue #218：副铭牌紧凑形态保留操作条，三张铭牌均有 支持/评论/立论 */
  await expect(page.getByText('支持 8')).toBeVisible();
  await expect(page.getByText('支持 5')).toBeVisible();
  const debateButtons = page.locator('.plate-card__action--debate');
  await expect(debateButtons).toHaveCount(3);
  for (let i = 0; i < 3; i += 1) {
    await expect(debateButtons.nth(i)).toBeVisible();
  }
  /* 副铭牌仍为紧凑形态：来源行收进详情页，不参与首屏展示 */
  await expect(page.locator('.plate-card__source').nth(1)).toBeHidden();
  await expect(page.locator('.plate-card__source').nth(2)).toBeHidden();
  /* 布局验收：第三张（最后一张副）铭牌的操作条完整落在 TabBar 之上 */
  const lastPlateActions = await page
    .locator('.plate-card')
    .nth(2)
    .locator('.plate-card__actions')
    .boundingBox();
  const tabBar = await page.locator('.home-tab-bar').boundingBox();
  expect(lastPlateActions).not.toBeNull();
  expect(tabBar).not.toBeNull();
  expect(lastPlateActions.y + lastPlateActions.height).toBeLessThanOrEqual(tabBar.y);
  if (process.env.E2E_SCREENSHOT_DIR) {
    await page.screenshot({
      path: `${process.env.E2E_SCREENSHOT_DIR}/guest-home.png`,
    });
  }

  /* 播放：不再断言 toast（沉浸流播放器不弹「正在播放...」），改断言播放态与波形动画 */
  await page.locator('.play-button').click();
  await expect(page.locator('.play-button--playing')).toBeVisible();
  await expect(page.locator('.audio-wave--playing')).toBeVisible();
  await expect(page).toHaveURL(/\/$/);

  /* 搜索入口改为顶部搜索图标 */
  await page.locator('.home-search-entry').click();
  await expect(page).toHaveURL(/\/pages\/search$/);
  await expect(page.getByRole('searchbox')).toBeVisible();
  await expect(page.getByText('月亮', { exact: true })).toBeVisible();

  await page.getByRole('searchbox').fill('月亮');
  await page.locator('.search-button').click();
  await expect(page.getByText('月亮义项')).toBeVisible();
});
