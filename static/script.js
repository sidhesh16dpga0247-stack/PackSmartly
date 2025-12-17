document.addEventListener("DOMContentLoaded", () => {
    const destinationInput = document.getElementById("destinationInput");
    const activityGrid = document.getElementById("activityGrid");

    let debounceTimer = null;

    destinationInput.addEventListener("input", () => {
        const destination = destinationInput.value.trim();

        // clear activities if destination is empty
        if (!destination) {
            activityGrid.innerHTML = "";
            return;
        }

        // debounce to avoid too many requests
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            fetchActivities(destination);
        }, 500);
    });

    function fetchActivities(destination) {
        fetch("/api/activities", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ destination })
        })
        .then(res => res.json())
        .then(data => {
            renderActivities(data.activities || []);
        })
        .catch(err => {
            console.error(err);
            activityGrid.innerHTML = "<p class='muted'>Could not load activities.</p>";
        });
    }

    function renderActivities(activities) {
        activityGrid.innerHTML = "";

        if (activities.length === 0) {
            activityGrid.innerHTML = "<p class='muted'>No suggested activities.</p>";
            return;
        }

        activities.forEach(activity => {
            const label = document.createElement("label");
            label.className = "activity-card";

            label.innerHTML = `
                <input type="checkbox" name="activities" value="${activity}">
                <span>${activity}</span>
            `;

            activityGrid.appendChild(label);
        });
    }
});
