/* === API Client === */

async function apiGet(url) {
  const response = await fetch(url);
  if (!response.ok) {
    let msg = response.statusText;
    try {
      const data = await response.json();
      if (data.error) msg = data.error;
    } catch (e) {}
    throw new Error(msg);
  }
  return response.json();
}

async function apiPost(url, data) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    let msg = response.statusText;
    try {
      const body = await response.json();
      if (body.error) msg = body.error;
    } catch (e) {}
    throw new Error(msg);
  }
  return response.json();
}

async function apiPut(url, data) {
  const response = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    let msg = response.statusText;
    try {
      const body = await response.json();
      if (body.error) msg = body.error;
    } catch (e) {}
    throw new Error(msg);
  }
  return response.json();
}

async function apiDelete(url, data) {
  const opts = { method: "DELETE" };
  if (data !== undefined) {
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(data);
  }
  const response = await fetch(url, opts);
  if (!response.ok) {
    let msg = response.statusText;
    try {
      const body = await response.json();
      if (body.error) msg = body.error;
    } catch (e) {}
    throw new Error(msg);
  }
  return response.json();
}

async function apiUpload(url, formData) {
  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    let msg = response.statusText;
    try {
      const body = await response.json();
      if (body.error) msg = body.error;
    } catch (e) {}
    throw new Error(msg);
  }
  return response.json();
}

/* === Modal System === */

function showModal({ title, body, confirmText = "OK", cancelText = "Cancel", onConfirm, showCancel = true, isDanger = false }) {
  const overlay = document.getElementById("modalOverlay");
  const modal = document.createElement("div");
  modal.className = "modal";

  const titleEl = document.createElement("h2");
  titleEl.className = "modal-title";
  titleEl.textContent = title;

  const bodyEl = document.createElement("div");
  bodyEl.className = "modal-body";
  bodyEl.innerHTML = body;

  const actions = document.createElement("div");
  actions.className = "modal-actions";

  if (showCancel) {
    const cancelBtn = document.createElement("button");
    cancelBtn.className = "btn-cancel";
    cancelBtn.textContent = cancelText;
    cancelBtn.addEventListener("click", closeModal);
    actions.appendChild(cancelBtn);
  }

  const confirmBtn = document.createElement("button");
  confirmBtn.className = isDanger ? "btn-danger" : "btn-primary";
  confirmBtn.textContent = confirmText;
  confirmBtn.addEventListener("click", () => {
    if (onConfirm) onConfirm();
    closeModal();
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
      if (onConfirm) onConfirm();
      closeModal();
    }
  }
  document.addEventListener("keydown", onKeydown);
  overlay._keydownHandler = onKeydown;
}

function closeModal() {
  const overlay = document.getElementById("modalOverlay");
  if (overlay._keydownHandler) {
    document.removeEventListener("keydown", overlay._keydownHandler);
    overlay._keydownHandler = null;
  }
  overlay.innerHTML = "";
  overlay.classList.remove("active");
}

function showPromptModal({ title, label, placeholder, value = "", onConfirm }) {
  const inputId = "prompt-modal-input";
  const body = `<label for="${inputId}" style="display:block;margin-bottom:8px;">${label}</label>` +
    `<input id="${inputId}" type="text" placeholder="${placeholder || ""}" value="${value}" ` +
    `style="width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;font:inherit;box-sizing:border-box;">`;
  showModal({
    title,
    body,
    confirmText: "OK",
    showCancel: true,
    onConfirm: () => {
      const input = document.getElementById(inputId);
      if (onConfirm) onConfirm(input ? input.value : "");
    },
  });
  // Focus the input after the modal is shown
  const input = document.getElementById(inputId);
  if (input) input.focus();
}

/* === Inline Editing === */

function makeEditable(element, onSave) {
  element.addEventListener("dblclick", startEdit);
  if (element.classList.contains("editable")) {
    element.addEventListener("click", startEdit);
  }

  function startEdit(e) {
    if (element.querySelector(".editable-input")) return;
    e.stopPropagation();
    e.preventDefault();
    const originalText = element.textContent;

    // Block navigation on the parent anchor while editing
    const parentLink = element.closest("a");
    function blockNav(evt) { evt.preventDefault(); }
    if (parentLink) parentLink.addEventListener("click", blockNav);

    const input = document.createElement("input");
    input.type = "text";
    input.className = "editable-input";
    input.value = originalText;
    element.textContent = "";
    element.appendChild(input);
    input.focus();
    input.select();

    let saving = false;

    async function save() {
      if (saving) return;
      saving = true;
      if (parentLink) parentLink.removeEventListener("click", blockNav);
      const newValue = input.value;
      try {
        await onSave(newValue);
        element.textContent = newValue;
      } catch (err) {
        element.textContent = originalText;
        showToast(err.message || "Save failed", "error");
      }
    }

    function cancel() {
      if (parentLink) parentLink.removeEventListener("click", blockNav);
      element.textContent = originalText;
    }

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        save();
      } else if (e.key === "Escape") {
        e.preventDefault();
        cancel();
      }
    });

    input.addEventListener("blur", () => {
      if (!saving) save();
    });
  }
}

/* === Toast Notifications === */

function showToast(message, type = "success", duration = 3000) {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = "opacity 0.3s ease";
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/* === Nav Reorder === */

async function handleNavReorder(evt) {
  const menuEl = evt.from;
  const navItems = menuEl.querySelectorAll(".nav-item");
  const newOrder = Array.from(navItems).map((el) => parseInt(el.dataset.index, 10));
  try {
    await apiPut("/api/navigation/reorder", { order: newOrder });
    window.location.reload();
  } catch (err) {
    showToast(err.message || "Failed to reorder navigation", "error");
    window.location.reload();
  }
}

/* === Initialization === */

document.addEventListener("DOMContentLoaded", () => {
  // Initialize inline editing on all .editable elements
  document.querySelectorAll(".editable").forEach((el) => {
    makeEditable(el, async (newValue) => {
      console.log("Editable save:", el.dataset.name, "->", newValue);
    });
  });

  // Wire up nav edit buttons
  document.querySelectorAll(".nav-edit-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const index = btn.dataset.index;
      const navItem = document.querySelector(`.nav-item[data-index="${index}"]`);
      if (!navItem || navItem.classList.contains("editing")) return;

      let files = [];
      try { files = await apiGet("/api/files"); } catch (e) {}

      const originalLabel = navItem.textContent;
      const originalUrl = navItem.getAttribute("href");
      navItem.classList.add("editing");

      // Prevent anchor navigation while editing
      function preventNavClick(e) {
        e.preventDefault();
      }
      navItem.addEventListener("click", preventNavClick);

      // Build inline edit form
      const form = document.createElement("span");
      form.className = "nav-edit-form";

      const labelInput = document.createElement("input");
      labelInput.type = "text";
      labelInput.value = originalLabel;
      labelInput.placeholder = "Label";

      const urlSelect = document.createElement("select");
      const placeholderOpt = document.createElement("option");
      placeholderOpt.value = "";
      placeholderOpt.textContent = "-- Select file --";
      urlSelect.appendChild(placeholderOpt);
      // Add "/" (site root) as first real option
      const rootOpt = document.createElement("option");
      rootOpt.value = "/";
      rootOpt.textContent = "/ (site root)";
      if (originalUrl === "/") rootOpt.selected = true;
      urlSelect.appendChild(rootOpt);
      files.forEach(f => {
        const opt = document.createElement("option");
        opt.value = f;
        opt.textContent = f;
        if (f === originalUrl) opt.selected = true;
        urlSelect.appendChild(opt);
      });
      // If current URL isn't in the file list, add it as an option
      if (originalUrl && !files.includes(originalUrl)) {
        const opt = document.createElement("option");
        opt.value = originalUrl;
        opt.textContent = originalUrl;
        opt.selected = true;
        urlSelect.insertBefore(opt, urlSelect.children[1]);
      }

      const saveBtn = document.createElement("button");
      saveBtn.className = "btn-save";
      saveBtn.textContent = "\u2713";
      saveBtn.title = "Save";

      const cancelBtn = document.createElement("button");
      cancelBtn.className = "btn-cancel";
      cancelBtn.textContent = "\u2717";
      cancelBtn.title = "Cancel";

      form.appendChild(labelInput);
      form.appendChild(urlSelect);
      form.appendChild(saveBtn);
      form.appendChild(cancelBtn);

      // Replace the <a> content with the form
      navItem.textContent = "";
      navItem.appendChild(form);
      btn.style.display = "none";
      const deleteBtn = document.querySelector(`.nav-delete-btn[data-index="${index}"]`);
      if (deleteBtn) deleteBtn.style.display = "none";
      labelInput.focus();

      function restoreOriginal() {
        navItem.textContent = originalLabel;
        navItem.setAttribute("href", originalUrl);
        navItem.classList.remove("editing");
        navItem.removeEventListener("click", preventNavClick);
        btn.style.display = "";
        if (deleteBtn) deleteBtn.style.display = "";
      }

      cancelBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        e.preventDefault();
        restoreOriginal();
      });

      saveBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        e.preventDefault();
        const newLabel = labelInput.value.trim();
        const newUrl = urlSelect.value;
        if (!newLabel || !newUrl) {
          showToast("Label and file cannot be empty", "error");
          return;
        }
        try {
          await apiPut(`/api/navigation/${index}`, { label: newLabel, url: newUrl });
          navItem.textContent = newLabel;
          navItem.setAttribute("href", newUrl);
          navItem.classList.remove("editing");
          navItem.removeEventListener("click", preventNavClick);
          btn.style.display = "";
          if (deleteBtn) deleteBtn.style.display = "";
          showToast("Navigation item updated", "success");
        } catch (err) {
          showToast(err.message || "Failed to update nav item", "error");
          restoreOriginal();
        }
      });

      // Handle Enter/Escape in inputs
      [labelInput, urlSelect].forEach((input) => {
        input.addEventListener("keydown", (e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            saveBtn.click();
          } else if (e.key === "Escape") {
            e.preventDefault();
            restoreOriginal();
          }
        });
      });
    });
  });

  // Wire up nav delete buttons
  document.querySelectorAll(".nav-delete-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      e.preventDefault();
      const index = btn.dataset.index;
      const navItem = document.querySelector(`.nav-item[data-index="${index}"]`);
      const label = navItem ? navItem.textContent : "this item";
      showModal({
        title: "Delete Navigation Item",
        body: `<p>Are you sure you want to delete "<strong>${label}</strong>"?</p>`,
        confirmText: "Delete",
        isDanger: true,
        onConfirm: async () => {
          try {
            await apiDelete(`/api/navigation/${index}`);
            // Remove the nav item, edit button, and delete button from the DOM
            if (navItem) navItem.remove();
            const editBtn = document.querySelector(`.nav-edit-btn[data-index="${index}"]`);
            if (editBtn) editBtn.remove();
            btn.remove();
            showToast("Navigation item deleted", "success");
          } catch (err) {
            showToast(err.message || "Failed to delete nav item", "error");
          }
        },
      });
    });
  });

  // Wire up add nav button
  const addNavBtn = document.getElementById("addNavBtn");
  if (addNavBtn) {
    addNavBtn.addEventListener("click", async () => {
      let files = [];
      try {
        files = await apiGet("/api/files");
      } catch (e) {}

      const overlay = document.getElementById("modalOverlay");
      const modal = document.createElement("div");
      modal.className = "modal";

      const titleEl = document.createElement("h2");
      titleEl.className = "modal-title";
      titleEl.textContent = "Add Navigation Item";

      const bodyEl = document.createElement("div");
      bodyEl.className = "modal-body";

      const lbl1 = document.createElement("label");
      lbl1.textContent = "Label";
      lbl1.style.cssText = "display:block;margin-bottom:4px;";
      const input1 = document.createElement("input");
      input1.type = "text";
      input1.placeholder = "e.g. Blog";
      input1.style.cssText = "width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;font:inherit;box-sizing:border-box;margin-bottom:12px;";

      const lbl2 = document.createElement("label");
      lbl2.textContent = "Link to file";
      lbl2.style.cssText = "display:block;margin-bottom:4px;";
      const select = document.createElement("select");
      select.style.cssText = "width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;font:inherit;box-sizing:border-box;";
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "-- Select a file --";
      select.appendChild(placeholder);
      // Add "/" (site root) as first real option
      const rootOpt = document.createElement("option");
      rootOpt.value = "/";
      rootOpt.textContent = "/ (site root)";
      select.appendChild(rootOpt);
      files.forEach(f => {
        const opt = document.createElement("option");
        opt.value = f;
        opt.textContent = f;
        select.appendChild(opt);
      });

      const errorEl = document.createElement("div");
      errorEl.style.cssText = "color:#e53e3e;font-size:13px;margin-top:8px;display:none;";

      bodyEl.appendChild(lbl1);
      bodyEl.appendChild(input1);
      bodyEl.appendChild(lbl2);
      bodyEl.appendChild(select);
      bodyEl.appendChild(errorEl);

      const actions = document.createElement("div");
      actions.className = "modal-actions";

      const cancelBtn = document.createElement("button");
      cancelBtn.className = "btn-cancel";
      cancelBtn.textContent = "Cancel";
      cancelBtn.addEventListener("click", closeModal);
      actions.appendChild(cancelBtn);

      const confirmBtn = document.createElement("button");
      confirmBtn.className = "btn-primary";
      confirmBtn.textContent = "OK";
      confirmBtn.addEventListener("click", async () => {
        const label = input1.value.trim();
        const url = select.value;
        if (!label || !url) {
          errorEl.textContent = "Both fields are required.";
          errorEl.style.display = "block";
          return;
        }
        try {
          await apiPost("/api/navigation", { label, url });
          window.location.reload();
        } catch (err) {
          showToast(err.message || "Failed to add nav item", "error");
        }
        closeModal();
      });
      actions.appendChild(confirmBtn);

      modal.appendChild(titleEl);
      modal.appendChild(bodyEl);
      modal.appendChild(actions);
      overlay.innerHTML = "";
      overlay.appendChild(modal);
      overlay.classList.add("active");

      function onKeydown(e) {
        if (e.key === "Escape") closeModal();
        else if (e.key === "Enter") { e.preventDefault(); confirmBtn.click(); }
      }
      document.addEventListener("keydown", onKeydown);
      overlay._keydownHandler = onKeydown;
      input1.focus();
    });
  }

  // Initialize SortableJS on the nav menu for drag-and-drop reordering
  const menuEl = document.querySelector(".menu");
  if (menuEl) {
    new Sortable(menuEl, {
      animation: 150,
      draggable: ".nav-group",
      filter: ".add-nav-btn, .nav-edit-btn, .nav-delete-btn",
      preventOnFilter: false,
      onEnd: handleNavReorder,
    });
  }

  // Wire up settings button
  const settingsBtn = document.getElementById("settingsBtn");
  if (settingsBtn) {
    settingsBtn.addEventListener("click", async () => {
      let config;
      try {
        config = await apiGet("/api/config");
      } catch (err) {
        showToast(err.message || "Failed to load settings", "error");
        return;
      }

      const overlay = document.getElementById("modalOverlay");
      const modal = document.createElement("div");
      modal.className = "modal";

      const titleEl = document.createElement("h2");
      titleEl.className = "modal-title";
      titleEl.textContent = "Settings";

      const bodyEl = document.createElement("div");
      bodyEl.className = "modal-body";

      const lbl1 = document.createElement("label");
      lbl1.textContent = "Site Name";
      lbl1.style.cssText = "display:block;margin-bottom:4px;";
      const siteNameInput = document.createElement("input");
      siteNameInput.type = "text";
      siteNameInput.value = config.site_name || "";
      siteNameInput.style.cssText = "width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;font:inherit;box-sizing:border-box;margin-bottom:12px;";

      const lbl2 = document.createElement("label");
      lbl2.textContent = "Footer Copyright";
      lbl2.style.cssText = "display:block;margin-bottom:4px;";
      const footerInput = document.createElement("input");
      footerInput.type = "text";
      footerInput.value = (config.footer && config.footer.copyright) || "";
      footerInput.style.cssText = "width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;font:inherit;box-sizing:border-box;";

      const errorEl = document.createElement("div");
      errorEl.style.cssText = "color:#e53e3e;font-size:13px;margin-top:8px;display:none;";

      bodyEl.appendChild(lbl1);
      bodyEl.appendChild(siteNameInput);
      bodyEl.appendChild(lbl2);
      bodyEl.appendChild(footerInput);
      bodyEl.appendChild(errorEl);

      const actions = document.createElement("div");
      actions.className = "modal-actions";

      const cancelBtn = document.createElement("button");
      cancelBtn.className = "btn-cancel";
      cancelBtn.textContent = "Cancel";
      cancelBtn.addEventListener("click", closeModal);
      actions.appendChild(cancelBtn);

      const saveBtn = document.createElement("button");
      saveBtn.className = "btn-primary";
      saveBtn.textContent = "Save";
      saveBtn.addEventListener("click", async () => {
        const newName = siteNameInput.value.trim();
        const newFooter = footerInput.value.trim();
        if (!newName) {
          errorEl.textContent = "Site name cannot be empty.";
          errorEl.style.display = "block";
          return;
        }
        try {
          await apiPut("/api/config/site-name", { value: newName });
          await apiPut("/api/config/footer", { value: newFooter });
          // Update DOM elements
          const brandEl = document.querySelector(".brand");
          if (brandEl) brandEl.textContent = newName;
          const footerEl = document.querySelector("footer .editable");
          if (footerEl) footerEl.textContent = newFooter;
          showToast("Settings saved", "success");
          closeModal();
        } catch (err) {
          errorEl.textContent = err.message || "Failed to save settings";
          errorEl.style.display = "block";
          showToast(err.message || "Failed to save settings", "error");
        }
      });
      actions.appendChild(saveBtn);

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
          saveBtn.click();
        }
      }
      document.addEventListener("keydown", onKeydown);
      overlay._keydownHandler = onKeydown;

      siteNameInput.focus();
    });
  }

  // Deploy button is wired up in deploy.js
});
