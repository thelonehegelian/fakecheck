// Content script - runs on all web pages
// This script can be used for future enhancements like:
// - Highlighting suspicious claims on pages
// - Auto-detecting fact-checkable content
// - Showing inline fact-check results

// For now, it's a placeholder for future features
console.log('FakeCheck extension loaded');

// Listen for messages from the popup or background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getSelectedText') {
    const selectedText = window.getSelection().toString().trim();
    sendResponse({ text: selectedText });
  }
});

// Future enhancement: Could add keyboard shortcuts
// Future enhancement: Could add visual indicators for suspicious content
// Future enhancement: Could integrate with specific news sites
