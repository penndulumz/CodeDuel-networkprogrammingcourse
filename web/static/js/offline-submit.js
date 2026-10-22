(() => {
  "use strict";

  const DATABASE_NAME = "codeduel-offline-submissions";
  const STORE_NAME = "submissions";
  const MAX_BOT_SIZE = 1024 * 1024;
  const form = document.getElementById("submissionForm");
  const fileInput = document.getElementById("botFile");
  const chooseFileButton = document.getElementById("chooseFileButton");
  const fileSelectionStatus = document.getElementById("fileSelectionStatus");
  const gameInput = document.getElementById("gameType");
  const list = document.getElementById("submissionList");
  const formStatus = document.getElementById("formStatus");
  const readiness = document.getElementById("offlineReady");
  const accountStatus = document.getElementById("accountStatus");
  const saveButton = document.getElementById("saveButton");
  const syncButton = document.getElementById("syncButton");
  const syncingIds = new Set();
  let database;
  let syncInProgress = false;

  async function fetchWithTimeout(url, options = {}, timeoutMs = 5000) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(url, { ...options, signal: controller.signal });
    } finally {
      window.clearTimeout(timeout);
    }
  }

  function openDatabase() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DATABASE_NAME, 1);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: "submissionId" });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("Could not open local storage"));
    });
  }

  function storeRequest(mode, action) {
    return new Promise((resolve, reject) => {
      const transaction = database.transaction(STORE_NAME, mode);
      const request = action(transaction.objectStore(STORE_NAME));
      transaction.oncomplete = () => resolve(request ? request.result : undefined);
      transaction.onerror = () => reject(transaction.error || new Error("Local save failed"));
      transaction.onabort = () => reject(transaction.error || new Error("Local save was cancelled"));
    });
  }

  const getAll = () => storeRequest("readonly", (store) => store.getAll());
  const saveRecord = (record) => storeRequest("readwrite", (store) => store.put(record));
  const removeRecord = (id) => storeRequest("readwrite", (store) => store.delete(id));
  const ACCOUNT_KEY = "codeduel-offline-account-v1";

  function readOfflineAccount() {
    try {
      return JSON.parse(localStorage.getItem(ACCOUNT_KEY) || "null");
    } catch (_) {
      return null;
    }
  }

  async function refreshOfflineAccount() {
    const savedAccount = readOfflineAccount();
    if (savedAccount) {
      accountStatus.textContent = `Tài khoản đã lưu trên thiết bị: ${savedAccount.username}.`;
    }
    if (navigator.onLine) {
      try {
        const response = await fetchWithTimeout("/api/auth/me", { credentials: "same-origin", cache: "no-store" }, 3000);
        if (response.ok) {
          const user = await response.json();
          const account = { id: user.id, username: user.username };
          localStorage.setItem(ACCOUNT_KEY, JSON.stringify(account));
          accountStatus.textContent = `Bài offline sẽ gắn với tài khoản ${account.username}.`;
          return account;
        }
      } catch (_) {
        // Use the account saved during an earlier online visit.
      }
    }
    const account = readOfflineAccount();
    accountStatus.textContent = account
      ? `Tài khoản đã lưu trên thiết bị: ${account.username}.`
      : "Chưa ghi nhận tài khoản. Hãy đăng nhập khi còn mạng, rồi mở lại trang này trước khi lưu bài offline.";
    return account;
  }

  function makeId() {
    if (crypto.randomUUID) return crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
      const random = Math.random() * 16 | 0;
      return (character === "x" ? random : (random & 3 | 8)).toString(16);
    });
  }

  function localDate(value) {
    return new Date(value).toLocaleString();
  }

  function createEntry(record) {
    const article = document.createElement("article");
    article.className = "entry";

    const head = document.createElement("div");
    head.className = "entry-head";
    const details = document.createElement("div");
    const title = document.createElement("div");
    title.className = "entry-title";
    title.textContent = record.filename;
    const meta = document.createElement("div");
    meta.className = "muted";
    meta.textContent = `${record.gameType} · Lưu trên thiết bị lúc ${localDate(record.savedAt)}`;
    details.append(title, meta);

    const badge = document.createElement("span");
    badge.className = `badge${record.state === "submitted" ? " sent" : ""}`;
    badge.textContent = record.state === "submitted" ? "Đã nhận · " + record.receipt : "Đang chờ gửi";
    head.append(details, badge);
    article.append(head);

    if (record.state === "submitted" && record.receivedAt) {
      const received = document.createElement("div");
      received.className = "muted";
      received.textContent = `Máy chủ xác nhận lúc ${localDate(record.receivedAt)}`;
      article.append(received);
    } else if (record.lastError) {
      const error = document.createElement("div");
      error.className = "muted error";
      error.textContent = record.lastError;
      article.append(error);
    }

    const actions = document.createElement("div");
    actions.className = "actions";
    const download = document.createElement("button");
    download.type = "button";
    download.className = "secondary";
    download.textContent = "Tải bản .py về máy";
    download.addEventListener("click", () => downloadBot(record));
    actions.append(download);

    if (record.state !== "submitted") {
      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "secondary";
      retry.textContent = "Gửi lại";
      retry.addEventListener("click", () => syncRecord(record));
      actions.append(retry);
    }

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "danger";
    remove.textContent = "Xóa bản lưu trên thiết bị";
    remove.addEventListener("click", async () => {
      await removeRecord(record.submissionId);
      await renderList();
    });
    actions.append(remove);
    article.append(actions);
    return article;
  }

  async function renderList() {
    const records = (await getAll()).sort((a, b) => b.savedAt.localeCompare(a.savedAt));
    list.replaceChildren();
    if (!records.length) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "Chưa có bản nộp nào được lưu trên thiết bị này.";
      list.append(empty);
      return;
    }
    records.forEach((record) => list.append(createEntry(record)));
  }

  function downloadBot(record) {
    const blob = new Blob([record.source], { type: "text/x-python;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = record.filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function syncRecord(record) {
    if (!navigator.onLine) {
      record.lastError = "Thiết bị đang offline; bài vẫn được lưu trên máy này.";
      await saveRecord(record);
      await renderList();
      return false;
    }
    if (syncingIds.has(record.submissionId)) return false;
    syncingIds.add(record.submissionId);

    try {
      const identityResponse = await fetchWithTimeout("/api/auth/me", {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (identityResponse.status === 401) {
        record.lastError = "Phiên đăng nhập hết hạn. Hãy đăng nhập lại đúng tài khoản rồi đồng bộ.";
        await saveRecord(record);
        return false;
      }
      if (!identityResponse.ok) throw new Error("Could not verify the signed-in account");
      const signedInUser = await identityResponse.json();
      if (record.ownerUserId && signedInUser.id !== record.ownerUserId) {
        record.lastError = `Bản này thuộc tài khoản ${record.ownerUsername}; hãy đăng nhập đúng tài khoản để đồng bộ.`;
        await saveRecord(record);
        return false;
      }
      if (!record.ownerUserId) {
        record.ownerUserId = signedInUser.id;
        record.ownerUsername = signedInUser.username;
        await saveRecord(record);
      }
      const formData = new FormData();
      formData.append("file", new File([record.source], record.filename, { type: "text/x-python" }));
      formData.append("game_type", record.gameType);
      formData.append("client_submission_id", record.submissionId);
      const response = await fetchWithTimeout("/api/bots/upload", {
        method: "POST",
        body: formData,
        credentials: "same-origin",
        cache: "no-store",
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        record.lastError = response.status === 401
          ? "Chưa đăng nhập hoặc phiên đăng nhập đã hết hạn. Hãy đăng nhập khi có mạng rồi đồng bộ lại."
          : (payload.detail || `Máy chủ từ chối bài (HTTP ${response.status}).`);
        await saveRecord(record);
        return false;
      }
      record.state = "submitted";
      record.receipt = payload.receipt || `CD-${payload.id}`;
      record.receivedAt = payload.received_at || payload.uploaded_at || new Date().toISOString();
      record.lastError = "";
      await saveRecord(record);
      formStatus.textContent = `Máy chủ đã nhận ${record.filename}. Biên nhận: ${record.receipt}.`;
      return true;
    } catch (error) {
      record.lastError = "Không kết nối được máy chủ; bài vẫn đang chờ trên thiết bị.";
      await saveRecord(record);
      return false;
    } finally {
      syncingIds.delete(record.submissionId);
      await renderList();
    }
  }

  async function syncPending() {
    // Retry while this page stays open: network connectivity may return before
    // the CodeDuel server is ready to accept submissions.
    if (syncInProgress || !database) return;
    syncInProgress = true;
    syncButton.disabled = true;
    try {
      const records = await getAll();
      const pending = records.filter((record) => record.state !== "submitted");
      if (!pending.length) formStatus.textContent = "Không có bài nào đang chờ gửi.";
      for (const record of pending) {
        if (!navigator.onLine) break;
        await syncRecord(record);
      }
    } catch (_) {
      formStatus.textContent = "Chưa thể đọc hàng đợi trên thiết bị. Hãy tải lại trang; các bản đã lưu vẫn nằm trong bộ nhớ trình duyệt.";
    } finally {
      syncButton.disabled = false;
      syncInProgress = false;
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = fileInput.files && fileInput.files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".py")) {
      formStatus.textContent = "Chỉ nhận file bot Python có đuôi .py.";
      return;
    }
    if (file.size > MAX_BOT_SIZE) {
      formStatus.textContent = "File bot vượt quá giới hạn 1 MB.";
      return;
    }

    saveButton.disabled = true;
    try {
      // Saving to this device must not depend on a live server session. If no
      // account was cached, syncRecord will bind this submission to the user
      // signed in when the server becomes reachable again.
      const account = readOfflineAccount();
      const bytes = await file.arrayBuffer();
      const source = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
      const record = {
        submissionId: makeId(),
        filename: file.name,
        gameType: gameInput.value,
        ownerUserId: account ? account.id : null,
        ownerUsername: account ? account.username : null,
        source,
        state: "pending",
        savedAt: new Date().toISOString(),
        lastError: "",
      };
      await saveRecord(record);
      fileInput.value = "";
      formStatus.textContent = account
        ? "Đã lưu bản nộp trên thiết bị này."
        : "Đã lưu bản nộp trên thiết bị này. Khi có kết nối, hãy đăng nhập tài khoản thi để đồng bộ.";
      await renderList();
      if (navigator.onLine) await syncRecord(record);
    } catch (error) {
      formStatus.textContent = error instanceof TypeError
        ? "File không phải UTF-8 hợp lệ. Hãy lưu bot ở định dạng UTF-8 rồi thử lại."
        : `Không lưu được trên thiết bị: ${error.message}`;
    } finally {
      saveButton.disabled = false;
    }
  });

  chooseFileButton.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    const file = fileInput.files && fileInput.files[0];
    fileSelectionStatus.textContent = file
      ? `Đã chọn ${file.name} (${(file.size / 1024).toFixed(1)} KB).`
      : "Chọn file .py đã lưu trên thiết bị này.";
  });

  syncButton.addEventListener("click", syncPending);
  window.addEventListener("online", syncPending);
  window.addEventListener("pageshow", () => {
    if (navigator.onLine) syncPending();
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && navigator.onLine) syncPending();
  });
  window.setInterval(() => {
    if (navigator.onLine) syncPending();
  }, 15000);
  window.addEventListener("offline", () => {
    readiness.textContent = "Đang offline. Bản nộp mới sẽ được lưu trên thiết bị và chờ gửi.";
    readiness.className = "status warn";
  });

  async function prepareOfflineMode() {
    if (!window.isSecureContext) {
      readiness.textContent = "Địa chỉ hiện tại không bảo mật (HTTP). Để mở trang lại khi offline, hãy dùng URL HTTPS trước khi mất mạng. Địa chỉ IP LAN dạng http://… thường không hỗ trợ Service Worker.";
      readiness.className = "status warn";
      return;
    }
    if (!("serviceWorker" in navigator)) {
      readiness.textContent = "Trình duyệt này không cung cấp Service Worker. Hãy thử Chrome, Edge hoặc Firefox mới nhất, hoặc dùng Starter Kit để tạo gói offline.";
      readiness.className = "status warn";
      return;
    }
    try {
      const existing = await navigator.serviceWorker.getRegistration("/static/");
      // On an offline reload, reuse the installed worker instead of trying to
      // fetch its script from the unavailable server.
      if (navigator.onLine || !existing || !existing.active) {
        await navigator.serviceWorker.register("/static/offline-sw.js", { scope: "/static/" });
      }
      await navigator.serviceWorker.ready;
      if (navigator.storage && navigator.storage.persist) await navigator.storage.persist();
      readiness.textContent = navigator.onLine
        ? "Đã chuẩn bị trang nộp offline trên thiết bị này. Hãy giữ trang này hoặc mở lại /static/offline-submit.html khi mất mạng."
        : "Đang offline. Trang đã sẵn sàng; bài sẽ lưu trên thiết bị và chờ kết nối để đồng bộ.";
      readiness.className = navigator.onLine ? "status good" : "status warn";
    } catch (error) {
      readiness.textContent = "Không thể chuẩn bị lưu trang offline. Hãy tải Starter Kit làm phương án dự phòng.";
      readiness.className = "status warn";
    }
  }

  (async () => {
    try {
      database = await openDatabase();
      await renderList();
      // The local form and queue must become usable without waiting for the
      // network. Some phones report online when Wi-Fi is connected but the
      // server itself is unreachable, leaving fetch() pending for a long time.
      const cachedAccount = readOfflineAccount();
      accountStatus.textContent = cachedAccount
        ? `Tài khoản đã lưu trên thiết bị: ${cachedAccount.username}.`
        : "Chưa lưu tài khoản trên thiết bị. Hãy đăng nhập khi còn kết nối tới máy chủ.";
      void prepareOfflineMode();
      void refreshOfflineAccount();
      if (navigator.onLine) void syncPending();
    } catch (error) {
      readiness.textContent = `Không thể mở bộ nhớ cục bộ của trình duyệt: ${error.message}`;
      readiness.className = "status warn";
      formStatus.textContent = "Hãy giữ file .py gốc và dùng pack_submission.py trong Starter Kit làm dự phòng.";
    }
  })();
})();
