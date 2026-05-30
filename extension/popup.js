// DOM Elements
const textInput = document.getElementById('textInput');
const checkBtn = document.getElementById('checkBtn');
const loading = document.getElementById('loading');
const results = document.getElementById('results');
const error = document.getElementById('error');
const errorMessage = document.getElementById('errorMessage');
const retryBtn = document.getElementById('retryBtn');
const newCheckBtn = document.getElementById('newCheckBtn');
const settingsBtn = document.getElementById('settingsBtn');
const settingsPanel = document.getElementById('settingsPanel');
const settingsError = document.getElementById('settingsError');
const apiUrlInput = document.getElementById('apiUrlInput');
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
const closeSettingsBtn = document.getElementById('closeSettingsBtn');

// Rating mapping
const ratingMap = {
  1: { text: 'True ✅', class: 'rating-1' },
  2: { text: 'Likely True 🟢', class: 'rating-2' },
  3: { text: 'Unverified / Mixed 🟡', class: 'rating-3' },
  4: { text: 'Likely Fake 🔴', class: 'rating-4' },
  5: { text: 'Fake ❌', class: 'rating-5' }
};

// Complexity mapping
const complexityMap = {
  'easy': 'Easy',
  'medium': 'Medium',
  'hard': 'Hard'
};

// Format analysis text with proper HTML formatting
function formatAnalysisText(text) {
  if (!text) return 'No analysis available.';

  // Split by lines
  let lines = text.split('\n');
  let formattedHtml = '';
  let inList = false;

  lines.forEach(line => {
    line = line.trim();
    if (!line) {
      // Empty line - close list if open and add paragraph break
      if (inList) {
        formattedHtml += '</ul>';
        inList = false;
      }
      formattedHtml += '<br>';
      return;
    }

    // Check if line starts with a bullet point (-, *, •, or numbered)
    if (line.match(/^[-*•]\s/) || line.match(/^\d+\.\s/)) {
      if (!inList) {
        formattedHtml += '<ul>';
        inList = true;
      }
      // Remove the bullet/number and add as list item
      const content = line.replace(/^[-*•]\s/, '').replace(/^\d+\.\s/, '');
      formattedHtml += `<li>${escapeHtml(content)}</li>`;
    } else {
      // Regular text
      if (inList) {
        formattedHtml += '</ul>';
        inList = false;
      }
      formattedHtml += `<p>${escapeHtml(line)}</p>`;
    }
  });

  // Close list if still open
  if (inList) {
    formattedHtml += '</ul>';
  }

  return formattedHtml || escapeHtml(text);
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  // Check if there's text from context menu
  chrome.storage.local.get(['selectedText'], (data) => {
    if (data.selectedText) {
      textInput.value = data.selectedText;
      // Clear the storage
      chrome.storage.local.remove(['selectedText']);
      // Auto-check if text is present
      if (data.selectedText.trim()) {
        checkClaim(data.selectedText);
      }
    }
  });

  // Button event listeners
  checkBtn.addEventListener('click', () => {
    const text = textInput.value.trim();
    if (text) {
      checkClaim(text);
    }
  });

  retryBtn.addEventListener('click', resetUI);
  newCheckBtn.addEventListener('click', resetUI);

  // Enter key to submit
  textInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      checkBtn.click();
    }
  });

  // Settings toggle
  settingsBtn.addEventListener('click', () => {
    chrome.storage.local.get(['apiUrl'], (data) => {
      apiUrlInput.value = data.apiUrl || 'https://backend-production-2f0a.up.railway.app';
      settingsPanel.classList.toggle('hidden');
      clearSettingsError();
    });
  });

  // Save Settings
  saveSettingsBtn.addEventListener('click', () => {
    let url = apiUrlInput.value.trim();
    if (!url) {
      url = 'https://backend-production-2f0a.up.railway.app';
    }
    // Remove trailing slash if present
    if (url.endsWith('/')) {
      url = url.slice(0, -1);
    }

    // Strictly validate URL to mitigate security risks (B2)
    try {
      const parsedUrl = new URL(url);
      const protocol = parsedUrl.protocol;
      const hostname = parsedUrl.hostname;

      if (protocol === 'http:') {
        // Restrict HTTP only to localhost and 127.0.0.1 loopbacks
        if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
          showSettingsError('HTTP is only allowed for localhost development. Use HTTPS for remote backends.');
          return;
        }
      } else if (protocol !== 'https:') {
        showSettingsError('Only HTTP (localhost only) or HTTPS protocols are supported.');
        return;
      }
    } catch (e) {
      showSettingsError('Please enter a valid absolute URL (e.g. http://localhost:8000 or https://your-app.up.railway.app).');
      return;
    }

    chrome.storage.local.set({ apiUrl: url }, () => {
      settingsPanel.classList.add('hidden');
      clearSettingsError();
    });
  });

  // Close Settings
  closeSettingsBtn.addEventListener('click', () => {
    settingsPanel.classList.add('hidden');
    clearSettingsError();
  });

  // Helpers to manage settings error display
  function showSettingsError(message) {
    settingsError.textContent = message;
    settingsError.classList.remove('hidden');
  }

  function clearSettingsError() {
    settingsError.textContent = '';
    settingsError.classList.add('hidden');
  }
});

// Reset UI to initial state
function resetUI() {
  hideAll();
  document.querySelector('.input-section').style.display = 'block';
  textInput.value = '';
  textInput.focus();
}

// Hide all sections
function hideAll() {
  document.querySelector('.input-section').style.display = 'none';
  loading.classList.add('hidden');
  results.classList.add('hidden');
  error.classList.add('hidden');
}

// Show loading state
function showLoading() {
  hideAll();
  loading.classList.remove('hidden');
}

// Show error state
function showError(message) {
  hideAll();
  error.classList.remove('hidden');
  errorMessage.textContent = message;
}

// Show results
function showResults(data) {
  hideAll();
  results.classList.remove('hidden');

  // Display rating
  const rating = data.fake_news_rating || 3;
  const ratingBadge = document.getElementById('ratingBadge');
  const ratingInfo = ratingMap[rating] || ratingMap[3];
  ratingBadge.textContent = ratingInfo.text;
  ratingBadge.className = `rating-badge ${ratingInfo.class}`;

  // Display confidence
  const confidence = data.confidence_score || 0;
  document.getElementById('confidence').textContent = `Confidence: ${(confidence * 100).toFixed(0)}%`;

  // Display analysis
  const analysis = data.fake_news_explanation || data.true_news_explanation || 'No analysis available.';
  document.getElementById('analysis').innerHTML = formatAnalysisText(analysis);

  // Display risk factors
  const riskFactors = data.risk_factors || [];
  const riskSection = document.getElementById('riskSection');
  const riskList = document.getElementById('riskFactors');
  if (riskFactors.length > 0) {
    riskSection.style.display = 'block';
    riskList.innerHTML = riskFactors.map(factor => `<li>${escapeHtml(factor)}</li>`).join('');
  } else {
    riskSection.style.display = 'none';
  }

  // Display sources
  const citations = data.citations || [];
  const sourcesSection = document.getElementById('sourcesSection');
  const sourcesList = document.getElementById('sources');
  if (citations.length > 0) {
    sourcesSection.style.display = 'block';
    sourcesList.innerHTML = citations.map((cite, i) => {
      if (typeof cite === 'string') {
        return `<div class="source-item">${i + 1}. ${escapeHtml(cite)}</div>`;
      } else if (cite.url) {
        const safeUrl = cite.url.startsWith('http') ? cite.url : '#';
        return `<div class="source-item">${i + 1}. <a href="${safeUrl}" target="_blank">${escapeHtml(cite.title || 'Source')}</a></div>`;
      }
      return '';
    }).join('');
  } else {
    sourcesSection.style.display = 'none';
  }

  // Display verification steps
  const steps = data.verification_steps || [];
  const stepsSection = document.getElementById('stepsSection');
  const stepsList = document.getElementById('verificationSteps');
  if (steps.length > 0) {
    stepsSection.style.display = 'block';
    stepsList.innerHTML = steps.map((step, i) => {
      const complexity = step.complexity || 'medium';
      const complexityLabel = complexityMap[complexity.toLowerCase()] || complexity;
      const stepText = step.step || step.description || (typeof step === 'string' ? step : '');
      const time = step.estimated_time || '';
      return `
        <div class="step-item">
          <strong>${i + 1}. ${escapeHtml(stepText)}</strong>
          <span class="step-complexity complexity-${complexity.toLowerCase()}">${escapeHtml(complexityLabel)}</span>
          ${time ? `<div style="font-size: 12px; color: #666; margin-top: 4px;">⏱️ ${escapeHtml(time)}</div>` : ''}
        </div>
      `;
    }).join('');
  } else {
    stepsSection.style.display = 'none';
  }
}

// Main function to check claim
async function checkClaim(text) {
  showLoading();

  let baseUrl = DEFAULT_API_URL;
  try {
    baseUrl = await getApiUrl();
    const response = await fetch(`${baseUrl}/v1/check-fake`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ news: text })
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Check if there's an error in the response
    if (data.error) {
      throw new Error(data.error);
    }

    showResults(data);

  } catch (err) {
    console.error('Error checking claim:', err);
    let message = 'Failed to check claim. ';

    if (err.message.includes('Failed to fetch')) {
      message += `Make sure the FakeCheck API is running on ${baseUrl}`;
    } else {
      message += err.message;
    }

    showError(message);
  }
}
