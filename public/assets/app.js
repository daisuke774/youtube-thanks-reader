const state = {
  items: [],
  meta: {},
  current: 0,
};

const els = {
  title: document.querySelector("[data-title]"),
  meta: document.querySelector("[data-meta]"),
  list: document.querySelector("[data-list]"),
  openReader: document.querySelector("[data-open-reader]"),
  reader: document.querySelector("[data-reader]"),
  closeReader: document.querySelector("[data-close-reader]"),
  prev: document.querySelector("[data-prev]"),
  next: document.querySelector("[data-next]"),
  count: document.querySelector("[data-count]"),
  readerCard: document.querySelector("[data-reader-card]"),
  readerTime: document.querySelector("[data-reader-time]"),
  readerKind: document.querySelector("[data-reader-kind]"),
  readerAuthor: document.querySelector("[data-reader-author]"),
  readerAmount: document.querySelector("[data-reader-amount]"),
  readerMessage: document.querySelector("[data-reader-message]"),
};

const kindLabels = {
  super_chat: "Super Chat",
  super_sticker: "Super Sticker",
  milestone: "Membership Milestone",
};

const kindMarks = {
  super_chat: "■",
  super_sticker: "◆",
  milestone: "★",
};

function text(value, fallback = "") {
  return value === undefined || value === null || value === "" ? fallback : String(value);
}

function moneyLabel(item) {
  if (item.amount_text) return item.amount_text;
  if (item.amount && item.currency) return `${item.currency} ${item.amount}`;
  return "";
}

function eventClass(item) {
  const classes = ["event-card", item.kind || "super_chat"];
  const amount = Number(item.amount || 0);
  if (item.kind === "super_chat" && amount >= 10000) classes.push("amount-high");
  if (item.kind === "super_chat" && amount >= 1000 && amount < 10000) classes.push("amount-mid");
  return classes.join(" ");
}

function formatMeta(meta, count) {
  const parts = [];
  if (meta.video_title) parts.push(meta.video_title);
  if (meta.created_at) parts.push(`生成 ${new Date(meta.created_at).toLocaleString("ja-JP")}`);
  parts.push(`${count}件`);
  return parts.join(" / ");
}

function renderList() {
  els.list.innerHTML = "";
  if (!state.items.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "対象データがありません";
    els.list.append(empty);
    els.openReader.disabled = true;
    return;
  }

  const fragment = document.createDocumentFragment();
  state.items.forEach((item, index) => {
    const card = document.createElement("article");
    card.className = eventClass(item);
    card.tabIndex = 0;
    card.addEventListener("click", () => openReader(index));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter") openReader(index);
    });

    const time = document.createElement("div");
    time.className = "time";
    time.textContent = text(item.time, "--:--");

    const body = document.createElement("div");
    const kindLine = document.createElement("div");
    kindLine.className = "kind-line";

    const badge = document.createElement("span");
    badge.className = `kind-badge ${item.kind || "super_chat"}`;
    badge.textContent = `${kindMarks[item.kind] || "■"} ${kindLabels[item.kind] || "Super Chat"}`;
    kindLine.append(badge);

    const amount = moneyLabel(item);
    if (amount) {
      const amountEl = document.createElement("span");
      amountEl.className = "amount";
      amountEl.textContent = amount;
      kindLine.append(amountEl);
    }

    const author = document.createElement("p");
    author.className = "author";
    author.textContent = text(item.author_name, "ユーザー名");

    const message = document.createElement("p");
    message.className = "message";
    message.textContent = text(item.message, "");

    body.append(kindLine, author, message);
    card.append(time, body);
    fragment.append(card);
  });

  els.list.append(fragment);
}

function renderReader() {
  const item = state.items[state.current];
  if (!item) return;
  const kind = item.kind || "super_chat";
  els.readerCard.className = `reader-card ${kind}`;
  els.readerTime.textContent = text(item.time, "--:--");
  els.readerKind.textContent = kindLabels[kind] || "Super Chat";
  els.readerAuthor.textContent = text(item.author_name, "ユーザー名");
  els.readerAmount.textContent = moneyLabel(item);
  els.readerMessage.textContent = text(item.message, "");
  els.count.textContent = `${state.current + 1} / ${state.items.length}`;
  els.prev.disabled = state.current === 0;
  els.next.disabled = state.current === state.items.length - 1;
}

function openReader(index = 0) {
  if (!state.items.length) return;
  state.current = Math.max(0, Math.min(index, state.items.length - 1));
  renderReader();
  els.reader.classList.add("active");
  els.reader.setAttribute("aria-hidden", "false");
  document.body.classList.add("reader-open");
  els.next.focus();
}

function closeReader() {
  els.reader.classList.remove("active");
  els.reader.setAttribute("aria-hidden", "true");
  document.body.classList.remove("reader-open");
  els.openReader.focus();
}

function move(delta) {
  if (!els.reader.classList.contains("active")) return;
  const nextIndex = state.current + delta;
  if (nextIndex < 0 || nextIndex >= state.items.length) return;
  state.current = nextIndex;
  renderReader();
}

function sortItems(items) {
  return [...items].sort((a, b) => {
    const at = Date.parse(a.sent_at || "") || 0;
    const bt = Date.parse(b.sent_at || "") || 0;
    if (at !== bt) return at - bt;
    return (a.time || "").localeCompare(b.time || "");
  });
}

async function load() {
  const response = await fetch("data.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`data.json: ${response.status}`);
  const data = await response.json();
  state.meta = data.meta || {};
  state.items = sortItems(data.items || []);
  els.title.textContent = state.meta.page_title || "Thanks Reader";
  els.meta.textContent = formatMeta(state.meta, state.items.length);
  document.title = `${els.title.textContent} | Thanks Reader`;
  renderList();
}

els.openReader.addEventListener("click", () => openReader(0));
els.closeReader.addEventListener("click", closeReader);
els.prev.addEventListener("click", () => move(-1));
els.next.addEventListener("click", () => move(1));

document.addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft") move(-1);
  if (event.key === "ArrowRight") move(1);
  if (event.key === "Escape" && els.reader.classList.contains("active")) closeReader();
});

load().catch((error) => {
  els.title.textContent = "Thanks Reader";
  els.meta.textContent = "読み込みエラー";
  els.list.innerHTML = "";
  const empty = document.createElement("div");
  empty.className = "empty";
  empty.textContent = error.message;
  els.list.append(empty);
  els.openReader.disabled = true;
});
