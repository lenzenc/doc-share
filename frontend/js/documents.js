const form = document.getElementById("lookup-form");
const tableWrap = document.getElementById("table-wrap");

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso) {
  return new Date(iso).toLocaleString();
}

function renderDocuments(docs) {
  if (docs.length === 0) {
    tableWrap.innerHTML = `<p class="empty-state">No documents found for this household yet.</p>`;
    return;
  }

  const rows = docs
    .map(
      (doc) => `
      <tr>
        <td>${escapeHtml(doc.original_filename)}</td>
        <td>${formatSize(doc.size_bytes)}</td>
        <td>${formatDate(doc.uploaded_at)}</td>
        <td><a href="/api/documents/${doc.id}/download" target="_blank" rel="noopener">Download</a></td>
      </tr>`
    )
    .join("");

  tableWrap.innerHTML = `
    <table>
      <thead>
        <tr><th>File</th><th>Size</th><th>Uploaded</th><th></th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const householdId = document.getElementById("household_id").value.trim();
  if (!householdId) return;

  tableWrap.innerHTML = `<p class="empty-state">Loading...</p>`;

  try {
    const response = await fetch(`/api/documents?household_id=${encodeURIComponent(householdId)}`);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      tableWrap.innerHTML = `<p class="empty-state">${escapeHtml(body.detail || response.statusText)}</p>`;
      return;
    }
    const docs = await response.json();
    renderDocuments(docs);
  } catch (err) {
    tableWrap.innerHTML = `<p class="empty-state">${escapeHtml(err.message)}</p>`;
  }
});
