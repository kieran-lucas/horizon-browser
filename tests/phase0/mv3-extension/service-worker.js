const COUNTER_KEY = 'probeCounter';
const MENU_ID = 'phase0-increment';

async function readCounter() {
  const stored = await chrome.storage.local.get({ [COUNTER_KEY]: 0 });
  return Number(stored[COUNTER_KEY]) || 0;
}

async function writeCounter(value) {
  await chrome.storage.local.set({ [COUNTER_KEY]: value });
  await chrome.action.setBadgeText({ text: String(value) });
  await chrome.action.setBadgeBackgroundColor({ color: '#3D70EA' });
}

chrome.runtime.onInstalled.addListener(async () => {
  chrome.contextMenus.create({
    id: MENU_ID,
    title: 'Increment Phase 0 profile counter',
    contexts: ['page']
  });
  await writeCounter(await readCounter());
});

chrome.runtime.onStartup.addListener(async () => {
  await writeCounter(await readCounter());
});

chrome.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId === MENU_ID) {
    await writeCounter((await readCounter()) + 1);
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== 'increment-counter') {
    return false;
  }
  readCounter()
    .then((value) => writeCounter(value + 1))
    .then(readCounter)
    .then((value) => sendResponse({ value }))
    .catch((error) => sendResponse({ error: String(error) }));
  return true;
});
