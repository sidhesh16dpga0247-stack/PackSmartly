// static/dashboard.js

// Render saved trips onto the dashboard
document.addEventListener("DOMContentLoaded", () => {
    const tripsList = document.getElementById("tripsList");

    // clear existing (safety)
    tripsList.innerHTML = "";

    TRIPS_DATA.forEach((trip, index) => {
        const li = document.createElement("li");
        li.innerHTML = `
            <button class="btn-ghost" onclick="openTrip(${index})">
                ${escapeHtml(trip.destination)} (${escapeHtml(String(trip.duration))} days)
            </button>
            – ${escapeHtml(trip.created_at)}
        `;
        tripsList.appendChild(li);
    });
});

let CURRENT_TRIP = null;   // the object being edited
let CURRENT_INDEX = null;  // index in TRIPS_DATA for that trip

// Helper: escape HTML to avoid injection when injecting text
function escapeHtml(text) {
    if (text === null || text === undefined) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Open modal for a trip
function openTrip(index) {
    CURRENT_INDEX = index;
    // deep copy so edits don't immediately mutate TRIPS_DATA until saved
    CURRENT_TRIP = JSON.parse(JSON.stringify(TRIPS_DATA[index] || {}));

    // ensure items object exists
    if (!CURRENT_TRIP.items || typeof CURRENT_TRIP.items !== "object") {
        CURRENT_TRIP.items = {};
    }

    document.getElementById("modalTitle").innerText =
        `${CURRENT_TRIP.destination} (${CURRENT_TRIP.duration} days)`;

    renderItems();

    document.getElementById("tripModal").style.display = "flex";
    // clear any previous new item input
    document.getElementById("newItemInput").value = "";
}

// Close modal
document.getElementById("closeModal").onclick = () => {
    document.getElementById("tripModal").style.display = "none";
    CURRENT_TRIP = null;
    CURRENT_INDEX = null;
};

// Populate modal with items
function renderItems() {
    const container = document.getElementById("itemsContainer");
    container.innerHTML = "";

    // If no categories, show helpful hint
    if (!CURRENT_TRIP.items || Object.keys(CURRENT_TRIP.items).length === 0) {
        container.innerHTML = "<p class='muted'>No items in this list. Add custom items below.</p>";
        return;
    }

    for (let category in CURRENT_TRIP.items) {
        // skip non-own props (precaution)
        if (!CURRENT_TRIP.items.hasOwnProperty(category)) continue;

        const sec = document.createElement("div");
        sec.className = "category-section";
        sec.innerHTML = `<h4>${escapeHtml(category)}</h4>`;

        CURRENT_TRIP.items[category].forEach((item, idx) => {
            const row = document.createElement("div");
            row.className = "item-row";
            // build row safely
            row.innerHTML = `
                <span>${escapeHtml(item)}</span>
                <button class="btn-ghost small remove-btn" style="color:red"
                        onclick="removeItem('${escapeJsString(category)}', ${idx})">
                    Remove
                </button>
            `;
            sec.appendChild(row);
        });

        container.appendChild(sec);
    }
}

// Helper to escape category names inside JS string (for onclick inline)
function escapeJsString(s) {
    if (s === null || s === undefined) return "";
    return String(s).replace(/'/g, "\\'");
}

// Remove item
function removeItem(category, index) {
    if (!CURRENT_TRIP || !CURRENT_TRIP.items || !CURRENT_TRIP.items[category]) return;
    // remove the item
    CURRENT_TRIP.items[category].splice(index, 1);

    // if category is now empty, delete it
    if (CURRENT_TRIP.items[category].length === 0) {
        delete CURRENT_TRIP.items[category];
    }

    renderItems();
}

// Add custom item
document.getElementById("addItemBtn").onclick = () => {
    const input = document.getElementById("newItemInput");
    const newItem = input.value.trim();
    if (!newItem) {
        alert("Enter an item name before adding.");
        return;
    }

    if (!CURRENT_TRIP.items["Custom Items"]) {
        CURRENT_TRIP.items["Custom Items"] = [];
    }

    CURRENT_TRIP.items["Custom Items"].push(newItem);
    input.value = "";
    renderItems();
};

// Save updated trip to DB via API
document.getElementById("saveChangesBtn").onclick = async () => {
    if (!CURRENT_TRIP || CURRENT_INDEX === null) {
        alert("No trip to save.");
        return;
    }

    const saveBtn = document.getElementById("saveChangesBtn");
    saveBtn.disabled = true;
    saveBtn.innerText = "Saving...";

    try {
        // ensure payload contains id and items (server requires)
        const payload = {
            id: CURRENT_TRIP.id,
            items: CURRENT_TRIP.items,
            destination: CURRENT_TRIP.destination,
            duration: CURRENT_TRIP.duration,
            activities: CURRENT_TRIP.activities
        };

        const res = await fetch("/api/update-list", {
            method: "POST",
            credentials: "same-origin", // ensure cookies (session) are sent
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (res.ok && data.success) {
            // update the in-page TRIPS_DATA so future opens show saved data
            TRIPS_DATA[CURRENT_INDEX] = JSON.parse(JSON.stringify(CURRENT_TRIP));
            alert("Changes saved!");
            document.getElementById("tripModal").style.display = "none";
            CURRENT_TRIP = null;
            CURRENT_INDEX = null;
        } else {
            const msg = (data && data.error) ? data.error : "Error saving changes";
            alert("Save failed: " + msg);
        }
    } catch (err) {
        console.error(err);
        alert("Network error while saving changes.");
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerText = "Save Changes";
    }
};

// PDF download using jsPDF
document.getElementById("downloadPdfBtn").onclick = () => {
    if (!CURRENT_TRIP) {
        alert("No trip loaded.");
        return;
    }

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    let y = 15;
    doc.setFontSize(14);
    doc.text(`Packing List for ${CURRENT_TRIP.destination}`, 10, y);
    y += 8;
    doc.setFontSize(11);

    for (let category in CURRENT_TRIP.items) {
        if (!CURRENT_TRIP.items.hasOwnProperty(category)) continue;

        doc.text(category + ":", 10, y);
        y += 6;

        CURRENT_TRIP.items[category].forEach(item => {
            // small guard to handle page overflow
            if (y > 275) {
                doc.addPage();
                y = 20;
            }
            doc.text("- " + item, 14, y);
            y += 6;
        });

        y += 6;
    }

    // safe filename
    const safeName = (CURRENT_TRIP.destination || "trip").replace(/[^a-z0-9_\-]/gi, "_").toLowerCase();
    doc.save(`packing_list_${safeName}.pdf`);
};
