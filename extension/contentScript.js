// contentScript.js
(function() {
  // Create a toast container in the page:
  const toastContainer = document.createElement('div');
  toastContainer.id = 'my-extension-toast-container';
  document.body.appendChild(toastContainer);
  
  function attachListenersToParagraphs() {
    const paragraphs = document.querySelectorAll('p');
    paragraphs.forEach(p => {
      p.style.cursor = 'pointer';  // Indicate clickable
      p.addEventListener('click', handleParagraphClick);
    });
  }

  function handleParagraphClick(event) {
    const textContent = event.target.textContent.trim();
    console.log('Text clicked:', textContent);
    if (textContent) {
      chrome.runtime.sendMessage({ action: 'pClicked', text: textContent }, response => {
        if (response && response.status === 'ok') {
          console.log(`Text "${textContent}" copied and sent to backend successfully.`);
          showToast(`Text copied and sent: "${textContent}"`);
        } else {
          console.error('Failed to send text to backend:', response ? response.error : 'No response');
          showToast('Failed to send text', true);
        }
      });
    }
  }

  function showToast(message, isError = false) {
    const toast = document.createElement('div');
    toast.className = `my-extension-toast ${isError ? 'error' : ''}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 3000); // Toast disappears after 3 seconds
  }

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    attachListenersToParagraphs();
  } else {
    document.addEventListener('DOMContentLoaded', attachListenersToParagraphs);
  }
})();
