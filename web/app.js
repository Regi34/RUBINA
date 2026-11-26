const AGENT_AVATARS = {
  scriptwriter: "✍️",
  safety_guard: "🛡️",
  voice_actor: "🎙️",
  illustrator: "🎨",
  video_editor: "🎬",
  publisher: "📺",
};

const STORAGE_REPO_KEY = "kids_ai_office_repo";
const STORAGE_TOKEN_KEY = "kids_ai_office_pat";

function detectRepoFromLocation() {
  const host = window.location.hostname;
  const parts = window.location.pathname.split("/").filter(Boolean);
  if (host.endsWith(".github.io") && parts.length >= 1) {
    const owner = host.replace(".github.io", "");
    return `${owner}/${parts[0]}`;
  }
  return "";
}

function getConfig() {
  return {
    repo: localStorage.getItem(STORAGE_REPO_KEY) || detectRepoFromLocation(),
    token: localStorage.getItem(STORAGE_TOKEN_KEY) || "",
  };
}

function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 3500);
}

async function ghFetch(path, options = {}) {
  const { repo, token } = getConfig();
  if (!repo) throw new Error("Nama repository GitHub belum diatur di tab Setting.");

  const headers = {
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    ...(options.headers || {}),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const resp = await fetch(`https://api.github.com/repos/${repo}${path}`, {
    ...options,
    headers,
  });
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`GitHub API (${resp.status}): ${errText.slice(0, 140)}`);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

function parseIssueScript(body) {
  const match = (body || "").match(/<!-- SCRIPT_JSON_START -->\s*```json\s*([\s\S]*?)\s*```\s*<!-- SCRIPT_JSON_END -->/);
  if (!match) return null;
  try {
    return JSON.parse(match[1]);
  } catch {
    return null;
  }
}

function rebuildIssueBody(originalBody, updatedScript) {
  const jsonStr = JSON.stringify(updatedScript, null, 2);
  const replacement = `<!-- SCRIPT_JSON_START -->\n\`\`\`json\n${jsonStr}\n\`\`\`\n<!-- SCRIPT_JSON_END -->`;
  if (/<!-- SCRIPT_JSON_START -->[\s\S]*<!-- SCRIPT_JSON_END -->/.test(originalBody)) {
    return originalBody.replace(/<!-- SCRIPT_JSON_START -->[\s\S]*<!-- SCRIPT_JSON_END -->/, replacement);
  }
  return `${originalBody}\n\n${replacement}`;
}

function renderAgents(state) {
  const grid = document.getElementById("agentsGrid");
  const agents = state.agents || {};
  grid.innerHTML = "";

  const statusText = {
    idle: "Standby",
    working: "Bekerja",
    waiting: "Menunggu",
    done: "Selesai",
  };

  Object.entries(agents).forEach(([key, info]) => {
    const st = info.status || "idle";
    const card = document.createElement("div");
    card.className = `agent-desk ${st}`;
    card.innerHTML = `
      <div class="agent-top">
        <div class="agent-avatar">${AGENT_AVATARS[key] || "🤖"}</div>
        <span class="status-pill ${st}">${statusText[st] || st}</span>
      </div>
      <div class="agent-name">${escapeHtml(info.name || key)}</div>
      <div class="agent-role">${escapeHtml(info.role || "")}</div>
      <div class="agent-bubble">${escapeHtml(info.message || "")}</div>
    `;
    grid.appendChild(card);
  });

  document.getElementById("statScripts").textContent = state.stats?.total_scripts ?? 0;
  document.getElementById("statPublished").textContent = state.stats?.total_published ?? 0;
  document.getElementById("lastUpdated").textContent = state.updated_at
    ? new Date(state.updated_at).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })
    : "Live";
}

function renderBanner(state, activeRuns) {
  const banner = document.getElementById("liveBanner");
  const title = document.getElementById("officeStatusTitle");
  const sub = document.getElementById("officeStatusSub");
  banner.className = "live-banner";

  if (activeRuns.length > 0) {
    banner.classList.add("busy");
    title.textContent = `⚙️ Sedang Berjalan: ${activeRuns[0].name}`;
    sub.textContent = `Status GitHub Actions: ${activeRuns[0].status}`;
    return;
  }

  if (state.office_status === "waiting_approval") {
    banner.classList.add("waiting");
    title.textContent = "📝 Ada Script Menunggu Approval Anda";
    sub.textContent = state.active_episode?.title || "Buka tab Approval untuk review dari HP.";
    return;
  }

  banner.classList.add("idle");
  title.textContent = "🏡 Kantor Virtual Siap Beroperasi";
  sub.textContent = "Semua agent standby menunggu tugas baru.";
}

function renderApprovals(issues) {
  const container = document.getElementById("approvalList");
  const badge = document.getElementById("navBadge");
  document.getElementById("statPending").textContent = issues.length;

  if (issues.length > 0) {
    badge.textContent = issues.length;
    badge.classList.remove("hidden");
  } else {
    badge.classList.add("hidden");
  }

  if (issues.length === 0) {
    container.innerHTML = `
      <div class="card">
        <h3>Belum ada script menunggu approval 🎉</h3>
        <p class="hint">Masuk ke tab <strong>Kantor</strong> untuk menyuruh Pena (Scriptwriter) membuat ide baru.</p>
      </div>`;
    return;
  }

  container.innerHTML = "";
  issues.forEach((issue) => {
    const script = parseIssueScript(issue.body);
    const card = document.createElement("div");
    card.className = "card";

    if (!script) {
      card.innerHTML = `
        <h3>#${issue.number} ${escapeHtml(issue.title)}</h3>
        <p class="hint">Format JSON script tidak terbaca. Buka langsung di GitHub Issue.</p>
        <a class="btn-secondary" href="${issue.html_url}" target="_blank">Buka GitHub Issue</a>`;
      container.appendChild(card);
      return;
    }

    const scenesHtml = (script.scenes || [])
      .map(
        (s, idx) => `
      <div class="scene-edit-box">
        <strong>Adegan ${s.scene_number}</strong>
        <label style="font-size:0.75rem">Narasi Suara:</label>
        <textarea data-scene="${idx}" data-field="narration">${escapeHtml(s.narration)}</textarea>
        <label style="font-size:0.75rem; margin-top:6px; display:block;">Aksi Motorik Anak:</label>
        <input type="text" data-scene="${idx}" data-field="motoric_action" value="${escapeHtml(s.motoric_action)}" />
      </div>`
      )
      .join("");

    card.innerHTML = `
      <h3>#${issue.number} ${escapeHtml(script.title)}</h3>
      <p class="hint">🎯 ${escapeHtml(script.educational_goal || "")}</p>
      <div class="form-group">
        <label>Judul YouTube</label>
        <input type="text" class="edit-title" value="${escapeHtml(script.title)}" />
      </div>
      ${scenesHtml}
      <div class="form-group">
        <label>Privasi Upload</label>
        <select class="edit-privacy">
          <option value="private" ${script.privacy_status === "private" ? "selected" : ""}>🔒 Private</option>
          <option value="unlisted" ${script.privacy_status === "unlisted" ? "selected" : ""}>🔗 Unlisted</option>
          <option value="public" ${script.privacy_status === "public" ? "selected" : ""}>🌍 Public</option>
        </select>
      </div>
      <div class="form-group">
        <label>Catatan Revisi (jika ingin AI ubah ulang)</label>
        <input type="text" class="revise-note" placeholder="Contoh: Buat lebih lucu & tambahkan gerakan melompat" />
      </div>
      <div class="action-row">
        <button class="btn-revise">✏️ Revisi AI</button>
        <button class="btn-approve">✅ Approve & Produksi</button>
      </div>
    `;

    const collectUpdatedScript = () => {
      const copy = structuredClone(script);
      copy.title = card.querySelector(".edit-title").value.trim() || script.title;
      copy.privacy_status = card.querySelector(".edit-privacy").value;
      card.querySelectorAll("[data-scene]").forEach((el) => {
        const idx = Number(el.dataset.scene);
        const field = el.dataset.field;
        copy.scenes[idx][field] = el.value.trim();
      });
      return copy;
    };

    card.querySelector(".btn-approve").addEventListener("click", async () => {
      try {
        const updated = collectUpdatedScript();
        const newBody = rebuildIssueBody(issue.body, updated);
        await ghFetch(`/issues/${issue.number}`, {
          method: "PATCH",
          body: JSON.stringify({
            title: `[APPROVAL] ${updated.title}`,
            body: newBody,
            labels: ["approved"],
          }),
        });
        showToast("✅ Disetujui! Agent produksi mulai bekerja di GitHub.");
        await refreshAll();
      } catch (err) {
        showToast(err.message);
      }
    });

    card.querySelector(".btn-revise").addEventListener("click", async () => {
      try {
        const note = card.querySelector(".revise-note").value.trim();
        if (!note) {
          showToast("Isi dulu catatan revisinya ya.");
          return;
        }
        await ghFetch(`/issues/${issue.number}/comments`, {
          method: "POST",
          body: JSON.stringify({ body: note }),
        });
        await ghFetch(`/issues/${issue.number}`, {
          method: "PATCH",
          body: JSON.stringify({ labels: ["revise"] }),
        });
        showToast("✏️ Permintaan revisi dikirim ke Pena (Scriptwriter)!");
        await refreshAll();
      } catch (err) {
        showToast(err.message);
      }
    });

    container.appendChild(card);
  });
}

function renderVideos(state) {
  const container = document.getElementById("videosList");
  const videos = state.recent_videos || [];
  if (videos.length === 0) {
    container.innerHTML = `
      <div class="card">
        <h3>Belum ada video terbit</h3>
        <p class="hint">Video yang selesai diupload ke YouTube akan muncul otomatis di sini.</p>
      </div>`;
    return;
  }

  container.innerHTML = videos
    .map(
      (v) => `
    <div class="card">
      <h3>🎬 ${escapeHtml(v.title)}</h3>
      <p class="hint">Privasi: <strong>${escapeHtml(v.privacy_status)}</strong> • ${new Date(v.published_at).toLocaleString("id-ID")}</p>
      <a class="btn-primary full-width" href="${v.youtube_url}" target="_blank">▶️ Buka di YouTube</a>
    </div>`
    )
    .join("");
}

function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function loadStateData() {
  const { repo, token } = getConfig();
  // Jika ada token & repo, ambil state langsung dari GitHub Contents API agar selalu paling fresh
  if (repo && token) {
    const fileData = await ghFetch("/contents/state/office_state.json");
    const decoded = decodeURIComponent(escape(atob(fileData.content.replace(/\n/g, ""))));
    return JSON.parse(decoded);
  }
  // Fallback baca file lokal/Pages
  const resp = await fetch(`state/office_state.json?t=${Date.now()}`);
  return resp.json();
}

async function refreshAll() {
  try {
    const state = await loadStateData();
    renderAgents(state);
    renderVideos(state);

    const { repo } = getConfig();
    let activeRuns = [];
    let pendingIssues = [];
    if (repo) {
      try {
        const [runsData, issuesData] = await Promise.all([
          ghFetch("/actions/runs?per_page=5"),
          ghFetch("/issues?state=open&labels=pending-approval"),
        ]);
        activeRuns = (runsData.workflow_runs || []).filter(
          (r) => r.status === "in_progress" || r.status === "queued"
        );
        pendingIssues = (issuesData || []).filter((i) => !i.pull_request);
      } catch {
        // Repo private tanpa token akan masuk ke sini -> tetap tampilkan state lokal
      }
    }
    renderBanner(state, activeRuns);
    renderApprovals(pendingIssues);
  } catch (err) {
    document.getElementById("officeStatusSub").textContent = err.message;
  }
}

function setupNavigation() {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    });
  });
}

function setupActions() {
  const cfg = getConfig();
  document.getElementById("cfgRepo").value = cfg.repo;
  document.getElementById("cfgToken").value = cfg.token;

  document.getElementById("btnSaveSettings").addEventListener("click", () => {
    const repo = document.getElementById("cfgRepo").value.trim();
    const token = document.getElementById("cfgToken").value.trim();
    localStorage.setItem(STORAGE_REPO_KEY, repo);
    localStorage.setItem(STORAGE_TOKEN_KEY, token);
    showToast("💾 Pengaturan tersimpan di HP!");
    refreshAll();
  });

  document.getElementById("btnRefresh").addEventListener("click", () => {
    showToast("🔄 Memperbarui status kantor...");
    refreshAll();
  });

  document.getElementById("btnGenerateScript").addEventListener("click", async () => {
    try {
      const { token } = getConfig();
      if (!token) {
        showToast("Isi GitHub PAT dulu di tab Setting agar bisa trigger dari HP.");
        return;
      }
      const theme = document.getElementById("inputTheme").value;
      const custom_topic = document.getElementById("inputTopic").value.trim();
      const privacy_status = document.getElementById("inputPrivacy").value;

      await ghFetch("/actions/workflows/01-script-agent.yml/dispatches", {
        method: "POST",
        body: JSON.stringify({
          ref: "main",
          inputs: { theme, custom_topic, privacy_status },
        }),
      });
      showToast("🚀 Pena mulai menulis! Tunggu ±30 detik lalu cek tab Approval.");
      document.getElementById("inputTopic").value = "";
      setTimeout(refreshAll, 5000);
    } catch (err) {
      showToast(err.message);
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupActions();
  refreshAll();
  setInterval(refreshAll, 20000);
});
