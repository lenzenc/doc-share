const form = document.getElementById("lookup-form");
const tableWrap = document.getElementById("table-wrap");

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function formatDate(iso) {
  return new Date(iso).toLocaleString();
}

function shortHash(hash) {
  return hash ? hash.slice(0, 10) : "—";
}

function renderEvents(events) {
  if (events.length === 0) {
    tableWrap.innerHTML = `<p class="empty-state">No audit events found for this household yet.</p>`;
    return;
  }

  const rows = events
    .map((event) => {
      const outcomeClass = event.outcome === "success" ? "success" : "error";
      const actor = [event.actor_ip, event.actor_user_agent].filter(Boolean).join(" — ");
      return `
      <tr>
        <td>${event.seq}</td>
        <td>${formatDate(event.occurred_at)}</td>
        <td>${escapeHtml(event.action)}</td>
        <td><span class="badge outcome-${outcomeClass}">${escapeHtml(event.outcome)}</span></td>
        <td>${escapeHtml(event.detail || "—")}</td>
        <td class="mono" title="${escapeHtml(actor)}">${escapeHtml(actor || "—")}</td>
        <td class="mono" title="${escapeHtml(event.hash)}">${shortHash(event.hash)}</td>
      </tr>`;
    })
    .join("");

  tableWrap.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Seq</th><th>Occurred</th><th>Action</th><th>Outcome</th>
          <th>Detail</th><th>Actor</th><th>Hash</th>
        </tr>
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
    const response = await fetch(`/api/audit?household_id=${encodeURIComponent(householdId)}`);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      tableWrap.innerHTML = `<p class="empty-state">${escapeHtml(body.detail || response.statusText)}</p>`;
      return;
    }
    const events = await response.json();
    renderEvents(events);
  } catch (err) {
    tableWrap.innerHTML = `<p class="empty-state">${escapeHtml(err.message)}</p>`;
  }
});
