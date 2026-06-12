(function () {
  const connection = document.querySelector("#connection");
  const bookTitle = document.querySelector("#book-title");
  const pageLabel = document.querySelector("#page-label");
  const bookList = document.querySelector("#book-list");
  const filter = document.querySelector("#book-filter");
  const refresh = document.querySelector("#refresh-books");
  let books = [];
  let activeBookId = null;

  function setConnection(status) {
    connection.textContent = status === "online" ? "Connected to TV" : status === "offline" ? "Reconnecting..." : "Connecting...";
  }

  function updateState(state) {
    if (!state || state.status !== "ready") {
      activeBookId = null;
      bookTitle.textContent = "No book open";
      pageLabel.textContent = "Open a book below.";
      renderBooks();
      return;
    }

    activeBookId = state.book.id;
    bookTitle.textContent = state.book.title;
    pageLabel.textContent = state.page_label;
    renderBooks();
  }

  const client = new window.ReaderClient({
    onState: updateState,
    onConnection: setConnection,
  });

  async function loadBooks() {
    bookList.innerHTML = "<p>Loading books...</p>";
    books = await client.books();
    renderBooks();
  }

  function renderBooks() {
    const query = filter.value.trim().toLowerCase();
    const visible = books.filter((book) => book.title.toLowerCase().includes(query));
    if (visible.length === 0) {
      bookList.innerHTML = "<p>No books found.</p>";
      return;
    }
    bookList.innerHTML = "";
    for (const book of visible) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "book-button";
      button.dataset.bookId = book.id;
      if (book.id === activeBookId) {
        button.classList.add("active");
      }
      button.innerHTML = `<strong></strong><span></span>`;
      button.querySelector("strong").textContent = book.title;
      button.querySelector("span").textContent = `${book.extension.toUpperCase()} · ${formatBytes(book.size)}`;
      button.addEventListener("click", () => client.openBook(book.id));
      bookList.append(button);
    }
  }

  function formatBytes(size) {
    if (!size) {
      return "0 B";
    }
    const units = ["B", "KB", "MB", "GB"];
    let value = size;
    let index = 0;
    while (value >= 1024 && index < units.length - 1) {
      value /= 1024;
      index += 1;
    }
    return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
  }

  document.querySelector("#left-button").addEventListener("click", () => client.command("left"));
  document.querySelector("#right-button").addEventListener("click", () => client.command("right"));
  document.querySelector("#shift-button").addEventListener("click", () => client.command("shift"));
  document.querySelector("#beginning-button").addEventListener("click", () => client.command("beginning"));
  refresh.addEventListener("click", loadBooks);
  filter.addEventListener("input", renderBooks);

  client.start()
    .then(loadBooks)
    .catch((error) => {
      connection.textContent = error.message;
    });
})();
