const form = document.getElementById("upload-form");
const resultsEl = document.getElementById("results");
const submitBtn = document.getElementById("submit-btn");

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function renderResults(ack) {
  resultsEl.innerHTML = "";

  ack.uploaded.forEach((doc) => {
    const row = document.createElement("div");
    row.className = "result-row success";
    row.innerHTML = `<span>&#10003; ${escapeHtml(doc.original_filename)}</span><span>uploaded</span>`;
    resultsEl.appendChild(row);
  });

  ack.errors.forEach((err) => {
    const row = document.createElement("div");
    row.className = "result-row error";
    row.innerHTML = `<span>&#10007; ${escapeHtml(err.filename)}</span><span>${escapeHtml(err.detail)}</span>`;
    resultsEl.appendChild(row);
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const householdId = document.getElementById("household_id").value.trim();
  const fileInput = document.getElementById("files");

  if (!householdId || fileInput.files.length === 0) {
    return;
  }

  const formData = new FormData();
  formData.append("household_id", householdId);
  Array.from(fileInput.files).forEach((file) => formData.append("files", file));

  submitBtn.disabled = true;
  submitBtn.textContent = "Uploading...";
  resultsEl.innerHTML = "";

  try {
    const response = await fetch("/api/documents", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      resultsEl.innerHTML = `<div class="result-row error"><span>Upload failed</span><span>${escapeHtml(body.detail || response.statusText)}</span></div>`;
      return;
    }

    const ack = await response.json();
    renderResults(ack);
    form.reset();
  } catch (err) {
    resultsEl.innerHTML = `<div class="result-row error"><span>Upload failed</span><span>${escapeHtml(err.message)}</span></div>`;
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Upload";
  }
});
