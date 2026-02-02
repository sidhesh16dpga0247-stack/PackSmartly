// ===============================
// DASHBOARD.JS (FIXED & CLEAN)
// ===============================

let CURRENT_TRIP = null;
let CURRENT_INDEX = null;

// -------------------------------
// Escape helpers
// -------------------------------
function escapeHtml(text) {
  if (text === null || text === undefined) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeJsString(s) {
  if (s === null || s === undefined) return "";
  return String(s).replace(/'/g, "\\'");
}

// -------------------------------
// Populate trip list
// -------------------------------
document.addEventListener("DOMContentLoaded", () => {
  const tripsList = document.getElementById("tripsList");
  tripsList.innerHTML = "";

  TRIPS_DATA.forEach((trip, index) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <button class="btn-ghost" onclick="openTrip(${index})">
        ${escapeHtml(trip.destination)} (${escapeHtml(trip.duration)} days)
      </button>
      – ${escapeHtml(trip.created_at)}
    `;
    tripsList.appendChild(li);
  });
});

// -------------------------------
// Open modal
// -------------------------------
function openTrip(index) {
  CURRENT_INDEX = index;
  CURRENT_TRIP = JSON.parse(JSON.stringify(TRIPS_DATA[index]));

  if (!CURRENT_TRIP.items) CURRENT_TRIP.items = {};

  document.getElementById("modalTitle").innerText =
    `${CURRENT_TRIP.destination} (${CURRENT_TRIP.duration} days)`;

  renderItems();
  document.getElementById("tripModal").style.display = "flex";
  document.getElementById("newItemInput").value = "";
}

// -------------------------------
// Close modal
// -------------------------------
document.getElementById("closeModal").onclick = () => {
  document.getElementById("tripModal").style.display = "none";
  CURRENT_TRIP = null;
  CURRENT_INDEX = null;
};

// -------------------------------
// Render checklist items
// -------------------------------
function renderItems() {
  const container = document.getElementById("itemsContainer");
  container.innerHTML = "";

  if (!CURRENT_TRIP || !CURRENT_TRIP.items || Object.keys(CURRENT_TRIP.items).length === 0) {
    container.innerHTML = "<p class='muted'>No items yet. Add some below.</p>";
    return;
  }

  Object.entries(CURRENT_TRIP.items).forEach(([category, items]) => {
    const h4 = document.createElement("h4");
    h4.textContent = category;
    h4.style.marginTop = "18px";
    container.appendChild(h4);

    items.forEach((item, idx) => {
      const label = document.createElement("label");
      label.className = "check-item";

     label.innerHTML = `
      <input type="checkbox"
        ${item.checked ? "checked" : ""}
        onchange="toggleItem('${escapeJsString(category)}', ${idx}, this.checked)">

      <span class="check-text">${escapeHtml(item.name)}</span>

      <button class="btn-ghost"
        onclick="renameItem('${escapeJsString(category)}', ${idx})">
        Rename
      </button>

      <button class="btn-ghost"
        onclick="deleteItem('${escapeJsString(category)}', ${idx})">
        Delete
      </button>
    `;


      container.appendChild(label);
    });
  });
}

// -------------------------------
// Toggle checkbox (local only)
// -------------------------------
function toggleItem(category, index, checked) {
  if (!CURRENT_TRIP || !CURRENT_TRIP.items[category]) return;
  CURRENT_TRIP.items[category][index].checked = checked;
}

// -------------------------------
// Add custom item
// -------------------------------
document.getElementById("addItemBtn").onclick = () => {
  const input = document.getElementById("newItemInput");
  const value = input.value.trim();
  if (!value) return alert("Enter an item name.");

  if (!CURRENT_TRIP.items["Custom Items"]) {
    CURRENT_TRIP.items["Custom Items"] = [];
  }

  CURRENT_TRIP.items["Custom Items"].push({
    name: value,
    checked: false
  });

  input.value = "";
  renderItems();
};

// -------------------------------
// Save changes to backend
// -------------------------------
document.getElementById("saveChangesBtn").onclick = async () => {
  if (!CURRENT_TRIP) return;

  const btn = document.getElementById("saveChangesBtn");
  btn.disabled = true;
  btn.innerText = "Saving...";

  try {
    const res = await fetch("/api/update-list", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: CURRENT_TRIP.id,
        items: CURRENT_TRIP.items
      })
    });

    const data = await res.json();

    if (res.ok && data.success) {
      TRIPS_DATA[CURRENT_INDEX] = JSON.parse(JSON.stringify(CURRENT_TRIP));
      alert("Checklist saved!");
      document.getElementById("tripModal").style.display = "none";
    } else {
      alert("Save failed.");
    }
  } catch (e) {
    console.error(e);
    alert("Network error.");
  } finally {
    btn.disabled = false;
    btn.innerText = "Save Changes";
  }
};

// -------------------------------
// PDF Export (checklist-aware)
// -------------------------------
document.getElementById("downloadPdfBtn").onclick = () => {
  if (!CURRENT_TRIP) return;

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();
  let y = 15;

  doc.setFontSize(14);
  doc.text(`Packing List – ${CURRENT_TRIP.destination}`, 10, y);
  y += 10;
  doc.setFontSize(11);

  Object.entries(CURRENT_TRIP.items).forEach(([category, items]) => {
    doc.text(category + ":", 10, y);
    y += 6;

    items.forEach(item => {
      if (y > 275) {
        doc.addPage();
        y = 20;
      }
      const mark = item.checked ? "[x]" : "[ ]";
      doc.text(`${mark} ${item.name}`, 14, y);
      y += 6;
    });

    y += 6;
  });

  const safeName = CURRENT_TRIP.destination.replace(/[^a-z0-9]/gi, "_").toLowerCase();
  doc.save(`packing_list_${safeName}.pdf`);
};

document.getElementById("renameTripBtn").onclick = async () => {
  if (!CURRENT_TRIP) return;

  const newName = prompt(
    "Enter new destination name:",
    CURRENT_TRIP.destination
  );

  if (!newName || newName.trim() === "") return;

  try {
    const res = await fetch("/api/rename-list", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: CURRENT_TRIP.id,
        destination: newName.trim()
      })
    });

    const data = await res.json();

    if (res.ok && data.success) {
      CURRENT_TRIP.destination = newName.trim();
      TRIPS_DATA[CURRENT_INDEX].destination = newName.trim();

      document.getElementById("modalTitle").innerText =
        `${CURRENT_TRIP.destination} (${CURRENT_TRIP.duration} days)`;

      alert("Trip renamed successfully!");
      location.reload(); // simple + safe for IA
    } else {
      alert("Rename failed.");
    }
  } catch (err) {
    alert("Network error.");
  }
};

document.getElementById("deleteTripBtn").onclick = async () => {
  if (!CURRENT_TRIP) return;

  const confirmDelete = confirm(
    "Are you sure you want to delete this packing list? This action cannot be undone."
  );

  if (!confirmDelete) return;

  try {
    const res = await fetch("/api/delete-list", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: CURRENT_TRIP.id
      })
    });

    const data = await res.json();

    if (res.ok && data.success) {
      alert("Packing list deleted.");
      location.reload();
    } else {
      alert("Delete failed.");
    }
  } catch (err) {
    alert("Network error.");
  }
};

function renameItem(category, index) {
  const item = CURRENT_TRIP.items[category][index];

  const newName = prompt("Rename item:", item.name);
  if (!newName || newName.trim() === "") return;

  item.name = newName.trim();
  renderItems();
}

function deleteItem(category, index) {
  const confirmDelete = confirm("Delete this item?");
  if (!confirmDelete) return;

  CURRENT_TRIP.items[category].splice(index, 1);

  // If category becomes empty, remove it
  if (CURRENT_TRIP.items[category].length === 0) {
    delete CURRENT_TRIP.items[category];
  }

  renderItems();
}
