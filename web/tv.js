(function () {
  const emptyState = document.querySelector("#empty-state");
  const hud = document.querySelector("#hud");
  const hudTitle = document.querySelector("#hud-title");
  const hudPages = document.querySelector("#hud-pages");
  const connection = document.querySelector("#connection");
  const settingsButton = document.querySelector("#tv-settings-button");
  const images = [document.querySelector("#spread-a"), document.querySelector("#spread-b")];
  let visibleIndex = 0;
  let currentUrl = "";
  const preloaded = new Set();
  let settingsOverlay = null;

  function absoluteUrl(url) {
    return new URL(url, window.location.href).href;
  }

  function preload(url) {
    const absolute = absoluteUrl(url);
    if (preloaded.has(absolute)) {
      return;
    }
    preloaded.add(absolute);
    const image = new Image();
    image.src = absolute;
  }

  function setConnection(status) {
    connection.textContent = status === "online" ? "Connected" : status === "offline" ? "Reconnecting" : "Connecting";
    connection.classList.toggle("online", status === "online");
    connection.classList.toggle("offline", status === "offline");
  }

  function showSpread(url) {
    const absolute = absoluteUrl(url);
    if (absolute === currentUrl) {
      return;
    }
    currentUrl = absolute;
    const nextIndex = visibleIndex === 0 ? 1 : 0;
    const next = images[nextIndex];
    const previous = images[visibleIndex];

    next.onload = () => {
      next.classList.add("visible");
      previous.classList.remove("visible");
      visibleIndex = nextIndex;
    };
    next.src = absolute;
  }

  function updateState(state) {
    if (settingsOverlay) {
      settingsOverlay.setState(state);
    }
    if (!state || state.status !== "ready") {
      emptyState.classList.remove("hidden");
      hud.classList.add("hidden");
      return;
    }

    emptyState.classList.add("hidden");
    hud.classList.remove("hidden");
    hudTitle.textContent = state.book.title;
    hudPages.textContent = state.page_label;
    for (const url of state.preload_urls || []) {
      preload(url);
    }
    showSpread(state.spread_url);
  }

  const client = new window.ReaderClient({
    onState: updateState,
    onConnection: setConnection,
  });

  settingsOverlay = new window.ReaderSettingsOverlay({
    client,
    showServer: true,
    trigger: settingsButton,
  });

  function command(name) {
    client.command(name);
  }

  window.tvReaderCommand = command;
  window.tvReaderOpenSettings = () => settingsOverlay.open();

  window.addEventListener("keydown", (event) => {
    if (!settingsOverlay.overlay.classList.contains("hidden")) {
      return;
    }
    if (["ArrowRight", " ", "Enter"].includes(event.key)) {
      event.preventDefault();
      command("right");
    } else if (["ArrowLeft", "Backspace"].includes(event.key)) {
      event.preventDefault();
      command("left");
    } else if (event.key.toLowerCase() === "s") {
      command("shift");
    } else if (event.key.toLowerCase() === "b") {
      command("beginning");
    }
  });

  window.addEventListener("click", (event) => {
    if (event.target.closest(".settings-overlay")) {
      return;
    }
    const rightHalf = event.clientX > window.innerWidth / 2;
    command(rightHalf ? "right" : "left");
  });

  client.start().catch((error) => {
    connection.textContent = error.message;
    connection.classList.add("offline");
  });
})();
