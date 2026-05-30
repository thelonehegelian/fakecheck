const DEFAULT_API_URL = 'http://localhost:8000';

/**
 * Resolves the configured API base URL from Chrome storage.
 * @returns {Promise<string>}
 */
async function getApiUrl() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['apiUrl'], (data) => {
      resolve(data.apiUrl || DEFAULT_API_URL);
    });
  });
}
