// Create context menu on installation
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'fakecheck',
    title: 'Fact-check this with FakeCheck',
    contexts: ['selection']
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'fakecheck' && info.selectionText) {
    // Store the selected text
    chrome.storage.local.set({ selectedText: info.selectionText });

    // Open the popup (or we could send it to check immediately)
    chrome.action.openPopup();
  }
});

// Listen for messages from popup or content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'checkClaim') {
    checkClaimWithAPI(request.text)
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Required for async sendResponse
  }
});

// Function to call the FakeCheck API
async function checkClaimWithAPI(text) {
  const API_URL = 'http://localhost:8000/v1/check-fake';

  const response = await fetch(API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ news: text })
  });

  if (!response.ok) {
    throw new Error(`API returned ${response.status}: ${response.statusText}`);
  }

  return await response.json();
}
