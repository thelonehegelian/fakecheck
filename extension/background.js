// background.js

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'pClicked') {
    const text = message.text;
    // Send the text to the backend
    sendTextToBackend(text).then(responseData => {
      // Optional: You can handle response or send a reply to the content script
      sendResponse({ status: 'ok', data: responseData });
    }).catch(error => {
      console.error('Error sending text to backend:', error);
      sendResponse({ status: 'error', error: error.message });
    });

    // Must return true to indicate asynchronous sendResponse
    return true;
  }
});

async function sendTextToBackend(text) {
  const testNews = "Democrats are trying to pass a bill that: 1 Provides a pathway to citizenship for more than 15 MILLION illegal aliens - including aliens who were previously deported during the Trump Admin. 15 17 423 1.1K Ill 38K Chad Wol @ChadFWol - Aug 20 **• 2. Requires taxpayers to pay for previously deported illegal aliens to be brought back to the U.S. @ 18. ［し405 1K ill 37K ① Chad Wol @ChadFWol - Aug 20) 2. Excludes the ability to remove alienswith felony records."
  // Replace with your backend endpoint
  const backendUrl = 'http://0.0.0.0:8000/check-fake';

  const response = await fetch(backendUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ news: testNews })
  });

  if (!response.ok) {
    throw new Error(`Backend returned status ${response.status}`);
  }

  

  return response.json();
}
