/* === Deploy Flow === */

document.addEventListener("DOMContentLoaded", () => {
  const deployBtn = document.getElementById("deployBtn");
  if (!deployBtn) return;

  deployBtn.addEventListener("click", async () => {
    // Immediate feedback while preflight runs
    const origText = deployBtn.textContent;
    deployBtn.disabled = true;
    deployBtn.textContent = "Checking...";

    let preflight;
    try {
      preflight = await apiGet("/api/deploy/preflight");
    } catch (err) {
      deployBtn.disabled = false;
      deployBtn.textContent = origText;
      showToast("Could not reach the server. Is the portfolio manager still running?", "error");
      return;
    }

    deployBtn.disabled = false;
    deployBtn.textContent = origText;

    if (!preflight.ready) {
      showPreflightErrorModal(preflight);
    } else {
      showDeployConfirmModal(preflight);
    }
  });
});

function showPreflightErrorModal(preflight) {
  let body = "";
  if (preflight.errors && preflight.errors.length) {
    body += preflight.errors
      .map(e => `<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;"><span style="color:#ef4444;font-size:18px;line-height:1;">&#x2716;</span><span>${escapeHtml(e)}</span></div>`)
      .join("");
  }
  if (preflight.warnings && preflight.warnings.length) {
    body += preflight.warnings
      .map(w => `<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;"><span style="color:#eab308;font-size:18px;line-height:1;">&#x26A0;</span><span>${escapeHtml(w)}</span></div>`)
      .join("");
  }
  showModal({
    title: "Cannot deploy",
    body: body,
    confirmText: "Close",
    showCancel: false,
  });
}

function showDeployConfirmModal(preflight) {
  let body = "";
  if (preflight.warnings && preflight.warnings.length) {
    body += preflight.warnings
      .map(w => `<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;"><span style="color:#eab308;font-size:18px;line-height:1;">&#x26A0;</span><span>${escapeHtml(w)}</span></div>`)
      .join("");
    body += '<hr style="margin:12px 0;border:none;border-top:1px solid #e5e7eb;">';
  }
  body += '<label for="deploy-commit-msg" style="display:block;margin-bottom:4px;">Commit message</label>';
  body += '<input id="deploy-commit-msg" type="text" placeholder="Update portfolio" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;font:inherit;box-sizing:border-box;">';

  const overlay = document.getElementById("modalOverlay");
  const modal = document.createElement("div");
  modal.className = "modal";

  const titleEl = document.createElement("h2");
  titleEl.className = "modal-title";
  titleEl.textContent = "Deploy to Website";

  const bodyEl = document.createElement("div");
  bodyEl.className = "modal-body";
  bodyEl.innerHTML = body;

  const actions = document.createElement("div");
  actions.className = "modal-actions";

  const cancelBtn = document.createElement("button");
  cancelBtn.className = "btn-cancel";
  cancelBtn.textContent = "Cancel";
  cancelBtn.addEventListener("click", closeModal);
  actions.appendChild(cancelBtn);

  const confirmBtn = document.createElement("button");
  confirmBtn.className = "btn-primary";
  confirmBtn.style.background = "#22c55e";
  confirmBtn.style.borderColor = "#22c55e";
  confirmBtn.textContent = "Deploy";
  confirmBtn.addEventListener("click", () => {
    const msgInput = document.getElementById("deploy-commit-msg");
    const message = (msgInput && msgInput.value.trim()) || "Update portfolio";
    startDeploy(message, overlay, modal);
  });
  actions.appendChild(confirmBtn);

  modal.appendChild(titleEl);
  modal.appendChild(bodyEl);
  modal.appendChild(actions);
  overlay.innerHTML = "";
  overlay.appendChild(modal);
  overlay.classList.add("active");

  function onKeydown(e) {
    if (e.key === "Escape") {
      closeModal();
    } else if (e.key === "Enter") {
      e.preventDefault();
      confirmBtn.click();
    }
  }
  document.addEventListener("keydown", onKeydown);
  overlay._keydownHandler = onKeydown;

  setTimeout(() => {
    const input = document.getElementById("deploy-commit-msg");
    if (input) input.focus();
  }, 50);
}

function startDeploy(message, overlay, modal) {
  const deployBtn = document.getElementById("deployBtn");
  if (deployBtn) {
    deployBtn.disabled = true;
    deployBtn.textContent = "Deploying...";
  }

  const stepNames = [
    "Generating site",
    "Staging changes",
    "Checking for changes",
    "Committing",
    "Pushing",
  ];

  // Replace modal content with progress view
  modal.innerHTML = "";

  const titleEl = document.createElement("h2");
  titleEl.className = "modal-title";
  titleEl.textContent = "Deploying...";
  modal.appendChild(titleEl);

  const bannerEl = document.createElement("div");
  bannerEl.style.cssText = "display:none;padding:10px 14px;border-radius:6px;margin-bottom:12px;font-weight:600;";
  modal.appendChild(bannerEl);

  const stepsEl = document.createElement("div");
  stepsEl.className = "modal-body";
  stepsEl.style.cssText = "padding:0;";

  const stepEls = stepNames.map(name => {
    const row = document.createElement("div");
    row.style.cssText = "display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid #f3f4f6;";

    const icon = document.createElement("span");
    icon.style.cssText = "font-size:16px;line-height:1.4;flex-shrink:0;width:20px;text-align:center;";
    icon.innerHTML = '<span class="deploy-spinner" style="display:inline-block;width:14px;height:14px;border:2px solid #d1d5db;border-top-color:#6366f1;border-radius:50%;animation:deploySpin 0.6s linear infinite;"></span>';

    const content = document.createElement("div");
    content.style.cssText = "flex:1;min-width:0;";

    const label = document.createElement("div");
    label.textContent = name;
    content.appendChild(label);

    const errorPre = document.createElement("pre");
    errorPre.style.cssText = "display:none;margin:4px 0 0;padding:8px;background:#fef2f2;border:1px solid #fecaca;border-radius:4px;font-size:12px;max-height:200px;overflow:auto;white-space:pre-wrap;word-break:break-word;";
    content.appendChild(errorPre);

    row.appendChild(icon);
    row.appendChild(content);
    stepsEl.appendChild(row);

    return { row, icon, label, errorPre };
  });

  modal.appendChild(stepsEl);

  const actions = document.createElement("div");
  actions.className = "modal-actions";
  actions.style.display = "none";
  const closeBtn = document.createElement("button");
  closeBtn.className = "btn-cancel";
  closeBtn.textContent = "Close";
  closeBtn.addEventListener("click", () => {
    closeModal();
    if (deployBtn) {
      deployBtn.disabled = false;
      deployBtn.textContent = "Deploy to Website";
    }
  });
  actions.appendChild(closeBtn);
  modal.appendChild(actions);

  // Add spinner keyframes if not already present
  if (!document.getElementById("deploySpinStyle")) {
    const style = document.createElement("style");
    style.id = "deploySpinStyle";
    style.textContent = "@keyframes deploySpin { to { transform: rotate(360deg); } }";
    document.head.appendChild(style);
  }

  // Make the API call
  fetch("/api/deploy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  })
    .then(resp => resp.json())
    .then(result => {
      // Update each step icon based on results
      if (result.steps) {
        result.steps.forEach((step, i) => {
          if (i >= stepEls.length) return;
          const el = stepEls[i];
          if (step.success) {
            el.icon.innerHTML = '<span style="color:#22c55e;">&#x2714;</span>';
          } else if (step.skipped) {
            el.icon.innerHTML = '<span style="color:#9ca3af;">&mdash;</span>';
          } else {
            el.icon.innerHTML = '<span style="color:#ef4444;">&#x2716;</span>';
          }
          if (step.error) {
            el.errorPre.textContent = step.error;
            el.errorPre.style.display = "block";
          }
        });
      }

      // Show banner
      if (result.success) {
        titleEl.textContent = "Deploy Complete";
        bannerEl.textContent = "Site deployed successfully!";
        bannerEl.style.cssText += "display:block;background:#dcfce7;color:#166534;";
      } else {
        titleEl.textContent = "Deploy Failed";
        bannerEl.textContent = "Deploy failed" + (result.error ? ": " + result.error : "");
        bannerEl.style.cssText += "display:block;background:#fef2f2;color:#991b1b;";
      }

      actions.style.display = "";
    })
    .catch(() => {
      titleEl.textContent = "Deploy Failed";
      bannerEl.textContent = "Could not reach the server. Is the portfolio manager still running?";
      bannerEl.style.cssText += "display:block;background:#fef2f2;color:#991b1b;";
      // Mark all steps as failed
      stepEls.forEach(el => {
        el.icon.innerHTML = '<span style="color:#9ca3af;">&mdash;</span>';
      });
      actions.style.display = "";
    });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
