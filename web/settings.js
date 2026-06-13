(function () {
  class ReaderSettingsOverlay {
    constructor(options) {
      this.client = options.client;
      this.showServer = Boolean(options.showServer);
      this.settings = {
        page_mode: "spread",
        epub_font_size: 16,
        epub_font_size_min: 10,
        epub_font_size_max: 32,
      };
      this.bridge = this.showServer ? window.AndroidTvReader : null;
      this.overlay = this.build();
      document.body.append(this.overlay);

      if (options.trigger) {
        options.trigger.addEventListener("click", () => this.open());
      }
    }

    build() {
      const overlay = document.createElement("section");
      overlay.className = "settings-overlay hidden";
      overlay.setAttribute("role", "dialog");
      overlay.setAttribute("aria-modal", "true");
      overlay.innerHTML = `
        <div class="settings-panel">
          <header class="settings-header">
            <div>
              <span class="label">Settings</span>
              <h2>Reader options</h2>
            </div>
            <button class="settings-close" type="button" aria-label="Close settings">Close</button>
          </header>
          <label class="settings-row server-setting hidden">
            <span>Server URL</span>
            <input class="settings-server" type="url" inputmode="url" autocomplete="url">
          </label>
          <label class="settings-row settings-toggle">
            <span>Single page view</span>
            <input class="settings-single-page" type="checkbox">
          </label>
          <div class="settings-row settings-stepper">
            <span>EPUB font size</span>
            <div>
              <button class="settings-font-down" type="button" aria-label="Decrease EPUB font size">-</button>
              <output class="settings-font-value">16 pt</output>
              <button class="settings-font-up" type="button" aria-label="Increase EPUB font size">+</button>
            </div>
          </div>
          <footer class="settings-actions">
            <button class="settings-save" type="button">Save</button>
          </footer>
        </div>
      `;
      overlay.addEventListener("click", (event) => {
        if (event.target === overlay) {
          this.close();
        }
      });
      overlay.addEventListener("keydown", (event) => {
        if (event.key === "Escape" || event.key === "Backspace") {
          event.preventDefault();
          this.close();
        }
      });
      overlay.querySelector(".settings-close").addEventListener("click", () => this.close());
      overlay.querySelector(".settings-save").addEventListener("click", () => this.save());
      overlay.querySelector(".settings-font-down").addEventListener("click", () => this.changeFont(-1));
      overlay.querySelector(".settings-font-up").addEventListener("click", () => this.changeFont(1));
      return overlay;
    }

    setState(state) {
      if (state && state.settings) {
        this.settings = { ...this.settings, ...state.settings };
        this.syncValues();
      }
    }

    async open() {
      try {
        this.settings = { ...this.settings, ...(await this.client.settings()) };
      } catch (_error) {
        // Keep the last known settings if the server is momentarily unavailable.
      }
      this.syncValues();
      this.overlay.classList.remove("hidden");
      this.overlay.querySelector(".settings-save").focus();
    }

    close() {
      this.overlay.classList.add("hidden");
    }

    syncValues() {
      this.overlay.querySelector(".settings-single-page").checked = this.settings.page_mode === "single";
      this.overlay.querySelector(".settings-font-value").textContent = `${this.settings.epub_font_size} pt`;

      const serverRow = this.overlay.querySelector(".server-setting");
      const serverInput = this.overlay.querySelector(".settings-server");
      if (this.bridge && typeof this.bridge.getServerUrl === "function") {
        serverRow.classList.remove("hidden");
        try {
          serverInput.value = this.bridge.getServerUrl() || "";
        } catch (_error) {
          serverInput.value = "";
        }
      } else {
        serverRow.classList.add("hidden");
      }
    }

    changeFont(delta) {
      const min = Number(this.settings.epub_font_size_min || 10);
      const max = Number(this.settings.epub_font_size_max || 32);
      const next = Math.max(min, Math.min(max, Number(this.settings.epub_font_size || 16) + delta));
      this.settings.epub_font_size = next;
      this.syncValues();
    }

    async save() {
      const settings = {
        page_mode: this.overlay.querySelector(".settings-single-page").checked ? "single" : "spread",
        epub_font_size: Number(this.settings.epub_font_size || 16),
      };
      await this.client.updateSettings(settings);

      if (this.bridge && typeof this.bridge.setServerUrl === "function") {
        const serverUrl = this.overlay.querySelector(".settings-server").value.trim();
        try {
          if (serverUrl && serverUrl !== this.bridge.getServerUrl()) {
            this.bridge.setServerUrl(serverUrl);
          }
        } catch (_error) {
          this.bridge.setServerUrl(serverUrl);
        }
      }
      this.close();
    }
  }

  window.ReaderSettingsOverlay = ReaderSettingsOverlay;
})();
