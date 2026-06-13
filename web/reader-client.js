(function () {
  class ReaderClient {
    constructor(options) {
      this.onState = options.onState || function () {};
      this.onConnection = options.onConnection || function () {};
      this.socket = null;
      this.config = null;
      this.reconnectTimer = null;
      this.closed = false;
    }

    async start() {
      this.config = await this.loadConfig();
      await this.fetchState();
      this.connect();
    }

    async loadConfig() {
      const response = await fetch("/api/config", { cache: "no-store" });
      const payload = await response.json();
      return payload.config || {};
    }

    websocketUrl() {
      if (this.config.public_ws_url) {
        return this.config.public_ws_url;
      }
      const params = new URLSearchParams(window.location.search);
      if (params.has("ws")) {
        return params.get("ws");
      }
      const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
      if (window.location.protocol === "https:") {
        return `${scheme}//${window.location.host}/ws`;
      }
      const wsPort = params.get("wsPort") || this.config.ws_port || "55559";
      return `${scheme}//${window.location.hostname}:${wsPort}`;
    }

    renderSize() {
      return this.config.render_size || "1920x1080";
    }

    connect() {
      if (this.closed) {
        return;
      }
      this.setConnection("connecting");
      this.socket = new WebSocket(this.websocketUrl());

      this.socket.addEventListener("open", () => {
        this.setConnection("online");
        this.send({ type: "state" });
      });

      this.socket.addEventListener("message", (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type === "state") {
          this.onState(payload.state);
        }
      });

      this.socket.addEventListener("close", () => {
        this.setConnection("offline");
        this.reconnectLater();
      });

      this.socket.addEventListener("error", () => {
        this.setConnection("offline");
      });
    }

    reconnectLater() {
      if (this.closed || this.reconnectTimer) {
        return;
      }
      this.reconnectTimer = window.setTimeout(() => {
        this.reconnectTimer = null;
        this.connect();
      }, 1400);
    }

    setConnection(status) {
      this.onConnection(status);
    }

    send(payload) {
      const message = {
        ...payload,
        size: this.renderSize(),
      };
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify(message));
        return true;
      }
      return false;
    }

    async fetchState() {
      const response = await fetch(`/api/state?size=${encodeURIComponent(this.renderSize())}`, {
        cache: "no-store",
      });
      const payload = await response.json();
      this.onState(payload.state);
      return payload.state;
    }

    async settings() {
      const response = await fetch("/api/settings", { cache: "no-store" });
      const payload = await response.json();
      return payload.settings || {};
    }

    async updateSettings(settings) {
      if (this.send({ type: "settings", settings })) {
        return null;
      }
      const response = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ settings, size: this.renderSize() }),
      });
      const payload = await response.json();
      if (payload.state) {
        this.onState(payload.state);
      }
      return payload.settings || (payload.state && payload.state.settings) || {};
    }

    async command(command) {
      if (this.send({ type: "command", command })) {
        return null;
      }
      const response = await fetch("/api/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command, size: this.renderSize() }),
      });
      const payload = await response.json();
      this.onState(payload.state);
      return payload.state;
    }

    async openBook(bookId) {
      if (this.send({ type: "open", book_id: bookId })) {
        return null;
      }
      const response = await fetch("/api/open", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ book_id: bookId, size: this.renderSize() }),
      });
      const payload = await response.json();
      this.onState(payload.state);
      return payload.state;
    }

    async books() {
      const response = await fetch("/api/books", { cache: "no-store" });
      const payload = await response.json();
      return payload.books || [];
    }
  }

  window.ReaderClient = ReaderClient;
})();
