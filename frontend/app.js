const API_URL = "https://onepiece-character-match.onrender.com";

const fileInput = document.getElementById("fileInput");
const dropZone = document.getElementById("dropZone");
const previewImage = document.getElementById("previewImage");
const analyzeBtn = document.getElementById("analyzeBtn");
const loading = document.getElementById("loading");
const resultSection = document.getElementById("resultSection");
const resultCards = document.getElementById("resultCards");
const copyBtn = document.getElementById("copyBtn");

let selectedBase64 = "";
window.lastShareUrl = "";

dropZone.addEventListener("click", () => {
  fileInput.click();
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
  if (file) {
    handleFile(file);
  }
});

fileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) {
    handleFile(file);
  }
});

function handleFile(file) {
  if (!file.type.startsWith("image/")) {
    alert("이미지 파일만 업로드할 수 있어!");
    return;
  }

  const reader = new FileReader();

  reader.onload = () => {
    selectedBase64 = reader.result;
    previewImage.src = selectedBase64;
    previewImage.classList.remove("hidden");
    analyzeBtn.disabled = false;
  };

  reader.readAsDataURL(file);
}

function makeShareUrl(results) {
  const payload = { results };

  const encoded = btoa(
    unescape(
      encodeURIComponent(JSON.stringify(payload))
    )
  );

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
  if (!selectedBase64) {
    alert("사진을 먼저 업로드해줘!");
    return;
  }

  analyzeBtn.disabled = true;
  loading.classList.remove("hidden");
  resultSection.classList.add("hidden");

  try {
    const response = await fetch(`${API_URL}/match`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        image_base64: selectedBase64
      })
    });

    if (!response.ok) {
      throw new Error("API 요청 실패");
    }

    const data = await response.json();

    if (!data.results || data.results.length === 0) {
      throw new Error("결과 없음");
    }

    renderResults(data.results);

    // 서버 저장 링크 대신 결과 데이터를 URL에 직접 넣음
    window.lastShareUrl = makeShareUrl(data.results);

  } catch (error) {
    console.error(error);
    alert("분석 실패 😭 백엔드 연결 후 다시 테스트해줘.");
  } finally {
    loading.classList.add("hidden");
    analyzeBtn.disabled = false;
  }
});

if (copyBtn) {
  copyBtn.addEventListener("click", async () => {
    const url = window.lastShareUrl || window.location.href;

    try {
      await navigator.clipboard.writeText(url);
      alert("결과 링크가 복사됐어!");
    } catch (err) {
      console.error(err);
      alert("복사 실패 😭");
    }
  });
}
