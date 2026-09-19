const counter = document.querySelector('#counter');
const increment = document.querySelector('#increment');
const status = document.querySelector('#status');

async function refresh() {
  const stored = await chrome.storage.local.get({ probeCounter: 0 });
  counter.value = String(Number(stored.probeCounter) || 0);
}

increment.addEventListener('click', async () => {
  status.textContent = '';
  try {
    const response = await chrome.runtime.sendMessage({ type: 'increment-counter' });
    if (response?.error) {
      throw new Error(response.error);
    }
    counter.value = String(response.value);
    status.textContent = 'Stored in this profile.';
  } catch (error) {
    status.textContent = `Probe failed: ${String(error)}`;
  }
});

refresh().catch((error) => {
  status.textContent = `Probe failed: ${String(error)}`;
});
