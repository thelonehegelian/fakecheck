// content.js

console.log("FakeCheck Content Script Loaded.");

// Example of detecting certain keywords or patterns for fake news
const keywords = ["fake", "hoax", "misleading", "unverified"];

function checkForKeywords() {
  const bodyText = document.body.innerText;
  keywords.forEach((keyword) => {
    if (bodyText.toLowerCase().includes(keyword)) {
      alert(`Warning: This page may contain ${keyword} information.`);
    }
  });
}

checkForKeywords();
