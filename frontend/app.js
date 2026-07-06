const API_URL = "https://onepiece-character-match.onrender.com";

const imageInput = document.getElementById("imageInput");
const dropZone = document.getElementById("dropZone");
const preview = document.getElementById("preview");
const uploadText = document.getElementById("uploadText");
const analyzeBtn = document.getElementById("analyzeBtn");
const loading = document.getElementById("loading");
const resultSection = document.getElementById("resultSection");
const resultCards = document.getElementById("resultCards");
const copyBtn = document.getElementById("copyBtn");

let selectedFile = null;
window.lastShareUrl = "";

function showPreview(file) {
  selectedFile = file;

  const url = URL.createObjectURL(file);
  preview.src = url;
  preview.classList.remove("hidden");
  uploadText.classList.add("hidden");
  analyzeBtn.disabled = false;
}

imageInput.addEventListener("change", () => {
  const file = imageInput.files[0];
  if (file) showPreview(file);
});

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");

  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith("image/")) {
    showPreview(file);
  }
});

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function makeShareUrl(results) {
  const payload = { results };
  const encoded = btoa(unescape(encodeURIComponent(JSON.stringify(payload))));
  return `${window.location.origin}/result.html?data=${encoded}`;
}

function renderResults(results) {
  resultCards.innerHTML = "";

  results.forEach((item, index) => {
    const medal = ["🥇", "🥈", "🥉"][index] || "⭐";

    const card = document.createElement("div");
    card.className = "result-card";

    card.innerHTML = `
      <div class="rank">${medal} ${item.name}</div>
      <img src="${item.image_url}" alt="${item.name}" />
      <div class="score">${item.score}% 닮음</div>
      <p class="reason">${item.reason}</p>
    `;

    resultCards.appendChild(card);
  });

  resultSection.classList.remove("hidden");
}

analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  loading.classList.remove("hidden");
  resultSection.classList.add("hidden");
  analyzeBtn.disabled = true;

  try {
    const imageBase64 = await fileToBase64(selectedFile);

    const response = await fetch(`${API_URL}/match`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        image_base64: imageBase64
      })
    });

    if (!response.ok) {
      throw new Error("API 호출 실패");
    }

    const data = await response.json();

    renderResults(data.results);

    window.lastShareUrl = makeShareUrl(data.results);

  } catch (error) {
    alert("분석 실패 😭 백엔드 연결 후 다시 테스트해줘.");
    console.error(error);
  } finally {
    loading.classList.add("hidden");
    analyzeBtn.disabled = false;
  }
});

copyBtn.addEventListener("click", async () => {
  await navigator.clipboard.writeText(window.lastShareUrl || window.location.href);
  alert("결과 링크가 복사됐어!");
});
