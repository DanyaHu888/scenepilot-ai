(function () {
  "use strict";

  const form = document.getElementById("plan-form");
  const sceneField = document.getElementById("scene-description");
  const charCount = document.getElementById("char-count");
  const sceneError = document.getElementById("scene-error");
  const sampleButton = document.getElementById("sample-button");
  const generateButton = document.getElementById("generate-button");
  const errorState = document.getElementById("error-state");
  const errorMessage = document.getElementById("error-message");
  const retryButton = document.getElementById("retry-button");
  const workflowStatus = document.getElementById("workflow-status");
  const workflowIntro = document.getElementById("workflow-intro");
  const stages = Array.from(document.querySelectorAll(".stage"));
  const results = document.getElementById("results");
  const sampleScene =
    "At 5:30 a.m., Mara waits alone at a rural bus stop as fog lifts off the road. A bus arrives, but she stays seated until she notices a child's red scarf caught on the rear gate. She runs after it. The mood is quiet and tense, with a small turn toward hope at the end.";
  let stageTimers = [];
  let lastPayload = null;

  const breakdownLabels = {
    cast: "Cast",
    props: "Props",
    location: "Location",
    lighting: "Lighting",
    production_risks: "Production risks",
  };

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function asArray(value) {
    if (Array.isArray(value))
      return value.filter(function (item) {
        return (
          item !== null && item !== undefined && String(item).trim() !== ""
        );
      });
    if (value === null || value === undefined || String(value).trim() === "")
      return [];
    return [value];
  }

  function displayText(value, fallback) {
    const text = value === null || value === undefined ? "" : String(value);
    return text.trim() || fallback || "Not provided";
  }

  function formatMoney(value) {
    if (value === null || value === undefined || value === "") return "—";
    if (typeof value === "string" && value.includes("$")) return value;
    const number = Number(String(value).replace(/[^0-9.-]/g, ""));
    if (Number.isNaN(number)) return displayText(value, "—");
    return "$" + number.toLocaleString("en-US", { maximumFractionDigits: 0 });
  }

  function formatMinutes(value) {
    if (value === null || value === undefined || value === "") return "—";
    if (typeof value === "string" && /hour|min/i.test(value)) return value;
    const number = Number(value);
    if (Number.isNaN(number)) return String(value);
    if (number >= 60) {
      const hours = Math.floor(number / 60);
      const minutes = number % 60;
      return minutes ? hours + "h " + minutes + "m" : hours + "h";
    }
    return number + " min";
  }

  function updateCharCount() {
    const count = sceneField.value.length;
    charCount.textContent = count.toLocaleString("en-US") + " / 2,000";
    charCount.style.color = count > 2000 ? "var(--red)" : "";
  }

  function clearTimers() {
    stageTimers.forEach(function (timer) {
      window.clearTimeout(timer);
    });
    stageTimers = [];
  }

  function setStageState(activeIndex, completeAll) {
    stages.forEach(function (stage, index) {
      stage.classList.toggle(
        "is-active",
        !completeAll && index === activeIndex,
      );
      stage.classList.toggle("is-complete", completeAll || index < activeIndex);
    });
  }

  function startWorkflow() {
    clearTimers();
    setStageState(0, false);
    workflowStatus.textContent = "In progress";
    workflowStatus.className = "workflow-status is-running";
    workflowIntro.textContent =
      "Building a plan against your brief and day limits.";
    [1, 2, 3].forEach(function (index) {
      stageTimers.push(
        window.setTimeout(function () {
          setStageState(index, false);
        }, index * 950),
      );
    });
  }

  function completeWorkflow() {
    clearTimers();
    setStageState(0, true);
    workflowStatus.textContent = "Plan ready";
    workflowStatus.className = "workflow-status is-complete";
    workflowIntro.textContent =
      "The returned plan is ready for a practical production review.";
  }

  function showWorkflowError() {
    clearTimers();
    stages.forEach(function (stage) {
      stage.classList.remove("is-active", "is-complete");
    });
    workflowStatus.textContent = "Needs attention";
    workflowStatus.className = "workflow-status is-error";
    workflowIntro.textContent =
      "The plan could not be completed. Your brief is still here to retry.";
  }

  function setLoading(isLoading) {
    generateButton.disabled = isLoading;
    generateButton.classList.toggle("is-loading", isLoading);
    generateButton.querySelector(".button-label").textContent = isLoading
      ? "Building plan"
      : "Generate shoot plan";
    generateButton.querySelector(".button-arrow").style.display = isLoading
      ? "none"
      : "";
    form.setAttribute("aria-busy", String(isLoading));
  }

  function validate() {
    const value = sceneField.value.trim();
    if (!value) {
      sceneError.textContent =
        "Add a scene description before generating a plan.";
      sceneField.setAttribute("aria-invalid", "true");
      sceneField.focus();
      return false;
    }
    if (value.length > 2000) {
      sceneError.textContent =
        "Keep the scene description under 2,000 characters.";
      sceneField.setAttribute("aria-invalid", "true");
      sceneField.focus();
      return false;
    }
    sceneError.textContent = "";
    sceneField.removeAttribute("aria-invalid");
    return true;
  }

  function showError(message) {
    errorMessage.textContent =
      message || "Check your connection and try again.";
    errorState.classList.add("is-visible");
  }

  function hideError() {
    errorState.classList.remove("is-visible");
  }

  function renderList(value, emptyElement, listElement) {
    const values = asArray(value);
    listElement.innerHTML = values
      .map(function (item) {
        const text =
          typeof item === "object"
            ? displayText(item.message, JSON.stringify(item))
            : item;
        return "<li>" + escapeHtml(text) + "</li>";
      })
      .join("");
    emptyElement.hidden = values.length > 0;
    listElement.hidden = values.length === 0;
  }

  function renderCostBreakdown(breakdown) {
    const card = document.getElementById("cost-breakdown-card");
    const grid = document.getElementById("cost-breakdown-grid");
    const source = breakdown || {};

    const items = [
      ["labour", "Labour"],
      ["location_and_permits", "Location & permits"],
      ["transport", "Transport"],
      ["meals", "Meals"],
      ["props_and_consumables", "Props & consumables"],
      ["contingency", "Contingency"],
      ["total", "Production total"],
    ];

    const availableItems = items.filter(function (item) {
      return source[item[0]] !== undefined;
    });

    grid.innerHTML = availableItems
      .map(function (item) {
        const key = item[0];
        const label = item[1];
        const totalClass = key === "total" ? " is-total" : "";

        return (
          '<div class="cost-item' +
          totalClass +
          '">' +
          "<span>" +
          escapeHtml(label) +
          "</span>" +
          "<strong>" +
          escapeHtml(formatMoney(source[key])) +
          "</strong>" +
          "</div>"
        );
      })
      .join("");

    card.hidden = availableItems.length === 0;
  }

  function renderBreakdown(breakdown) {
    const source = breakdown || {};
    const keys = Object.keys(breakdownLabels);
    document.getElementById("breakdown-grid").innerHTML = keys
      .map(function (key) {
        const values = asArray(source[key]);
        const content = values.length
          ? '<ul class="detail-list">' +
            values
              .map(function (item) {
                return (
                  "<li>" +
                  escapeHtml(
                    typeof item === "object" ? JSON.stringify(item) : item,
                  ) +
                  "</li>"
                );
              })
              .join("") +
            "</ul>"
          : '<p class="detail-empty">Not provided</p>';
        return (
          '<article class="result-card breakdown-card"><h3>' +
          breakdownLabels[key] +
          "</h3>" +
          content +
          "</article>"
        );
      })
      .join("");
  }

  function renderShots(shots) {
    const body = document.getElementById("shot-table-body");
    const empty = document.getElementById("shot-empty");
    const values = Array.isArray(shots) ? shots : [];
    document.getElementById("shot-count").textContent =
      values.length + (values.length === 1 ? " shot" : " shots");
    body.innerHTML = values
      .map(function (shot, index) {
        const number = displayText(shot.shot_number, index + 1);
        return (
          "<tr>" +
          "<td>" +
          escapeHtml(number) +
          "</td>" +
          "<td><strong>" +
          escapeHtml(displayText(shot.shot_type, "Coverage")) +
          "</strong><small>" +
          escapeHtml(displayText(shot.description, "No description")) +
          "</small></td>" +
          "<td>" +
          escapeHtml(displayText(shot.equipment, "—")) +
          "</td>" +
          "<td>" +
          escapeHtml(displayText(shot.crew_required, "—")) +
          "</td>" +
          "<td>" +
          escapeHtml(formatMinutes(shot.estimated_minutes)) +
          "</td>" +
          "<td>" +
          escapeHtml(formatMoney(shot.estimated_cost)) +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
    empty.hidden = values.length > 0;
  }

  function renderSchedule(schedule) {
    const list = document.getElementById("schedule-list");
    const empty = document.getElementById("schedule-empty");
    const values = Array.isArray(schedule) ? schedule : [];
    list.innerHTML = values
      .map(function (item, index) {
        const shotLabel =
          item.shot_number !== undefined
            ? "Shot " + item.shot_number
            : "Shot " + (index + 1);
        const time = [item.start_time, item.end_time]
          .filter(Boolean)
          .join(" — ");
        return (
          '<li class="schedule-item">' +
          '<span class="schedule-time">' +
          escapeHtml(time || "Timing pending") +
          "</span>" +
          '<span class="schedule-shot">' +
          escapeHtml(shotLabel) +
          "<span>" +
          escapeHtml(displayText(item.description, "Coverage")) +
          "</span></span>" +
          "</li>"
        );
      })
      .join("");
    empty.hidden = values.length > 0;
    list.hidden = values.length === 0;
  }

  function renderPlan(plan) {
    document.getElementById("initial-empty").hidden = true;
    document.getElementById("scene-summary").textContent = displayText(
      plan.scene_summary,
      "No scene summary returned.",
    );
    document.getElementById("total-time").textContent = formatMinutes(
      plan.total_estimated_time,
    );
    document.getElementById("total-cost").textContent = formatMoney(
      plan.total_estimated_cost,
    );
    const status = document.getElementById("constraint-status");
    const statusText = displayText(plan.constraint_status, "Not provided");
    status.textContent = statusText;
    status.className = "constraint-ok";
    if (/fail|over|risk|exceed|warning/i.test(statusText))
      status.classList.add("is-warning");
    if (/not met|invalid|critical/i.test(statusText))
      status.classList.add("is-alert");
    renderCostBreakdown(plan.cost_breakdown);
    renderBreakdown(plan.scene_breakdown);
    renderShots(plan.shot_list);
    renderSchedule(plan.shooting_schedule);
    renderList(
      plan.warnings,
      document.getElementById("warnings-empty"),
      document.getElementById("warnings-list"),
    );
    renderList(
      plan.adaptations_made,
      document.getElementById("adaptations-empty"),
      document.getElementById("adaptations-list"),
    );
    const shotCount = Array.isArray(plan.shot_list) ? plan.shot_list.length : 0;
    document.getElementById("result-meta").textContent =
      (plan.generation_source === "gemini" ? "Gemini · " : "Fallback · ") +
      (shotCount
        ? shotCount +
          " planned coverage " +
          (shotCount === 1 ? "shot" : "shots")
        : "Generated from your scene brief");
    results.hidden = false;
  }

  async function requestPlan() {
    if (!validate()) return;
    hideError();
    setLoading(true);
    startWorkflow();
    lastPayload = {
      scene_description: sceneField.value.trim(),
      budget: Number(document.getElementById("budget").value),
      crew_size: Number(document.getElementById("crew-size").value),
      shooting_hours: Number(document.getElementById("shooting-hours").value),
      equipment: document.getElementById("equipment").value.trim(),
      location_type: document.getElementById("location-type").value,
    };

    try {
      const response = await fetch("/generate-plan", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(lastPayload),
      });
      let data = {};
      try {
        data = await response.json();
      } catch (parseError) {
        data = {};
      }
      if (!response.ok) {
        throw new Error(
          data.detail ||
            data.error ||
            "The planning service returned an error.",
        );
      }
      completeWorkflow();
      renderPlan(data);
      window.setTimeout(function () {
        results.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 90);
    } catch (error) {
      showWorkflowError();
      showError(error.message);
    } finally {
      setLoading(false);
    }
  }

  sceneField.addEventListener("input", updateCharCount);
  sceneField.addEventListener("input", function () {
    if (sceneError.textContent && sceneField.value.trim()) {
      sceneError.textContent = "";
      sceneField.removeAttribute("aria-invalid");
    }
  });
  sampleButton.addEventListener("click", function () {
    sceneField.value = sampleScene;
    document.getElementById("budget").value = "3000";
    document.getElementById("crew-size").value = "6";
    document.getElementById("shooting-hours").value = "6";
    document.getElementById("location-type").value = "outdoor";
    document.getElementById("equipment").value =
      "Cinema camera, tripod, LED kit, sound recorder";
    updateCharCount();
    sceneField.focus();
    sceneField.setSelectionRange(
      sceneField.value.length,
      sceneField.value.length,
    );
  });
  document.querySelectorAll(".equipment-chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      document.getElementById("equipment").value =
        chip.getAttribute("data-equipment") || "";
      document.querySelectorAll(".equipment-chip").forEach(function (other) {
        other.classList.toggle("is-selected", other === chip);
      });
      document.getElementById("equipment").focus();
    });
  });
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    requestPlan();
  });
  retryButton.addEventListener("click", function () {
    if (lastPayload) requestPlan();
    else form.requestSubmit();
  });
  updateCharCount();
})();
