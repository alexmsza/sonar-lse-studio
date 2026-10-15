// Sonar LSE Studio - Lógica da Aplicação Web
document.addEventListener("DOMContentLoaded", () => {
  // Estado da aplicação
  let selectedFiles = [];
  let currentJobs = [];
  let activeJobId = null;
  let activeEntries = [];
  let pollInterval = null;

  // Elementos do DOM
  const apiStatusBadge = document.getElementById("apiStatusBadge");
  const apiStatusDot = document.getElementById("apiStatusDot");
  const apiStatusText = document.getElementById("apiStatusText");

  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const selectedFilesSummary = document.getElementById("selectedFilesSummary");
  const btnStartProcess = document.getElementById("btnStartProcess");
  const selectMode = document.getElementById("selectMode");
  const selectDetail = document.getElementById("selectDetail");
  const selectLang = document.getElementById("selectLang");

  const queueList = document.getElementById("queueList");
  const btnDownloadAllZip = document.getElementById("btnDownloadAllZip");

  const studioEmptyState = document.getElementById("studioEmptyState");
  const studioActiveContent = document.getElementById("studioActiveContent");
  const activeMovieTitle = document.getElementById("activeMovieTitle");
  const activeMovieMeta = document.getElementById("activeMovieMeta");
  const activeMovieStatusBadge = document.getElementById("activeMovieStatusBadge");
  const activeMovieStatusText = document.getElementById("activeMovieStatusText");
  const audioPlayer = document.getElementById("audioPlayer");
  const subtitlesTableBody = document.getElementById("subtitlesTableBody");
  const subCount = document.getElementById("subCount");

  const btnAddSubtitle = document.getElementById("btnAddSubtitle");
  const btnSaveEdits = document.getElementById("btnSaveEdits");
  const btnDownloadSrt = document.getElementById("btnDownloadSrt");
  const btnDownloadVtt = document.getElementById("btnDownloadVtt");

  // Modais
  const modalConfig = document.getElementById("modalConfig");
  const btnOpenConfig = document.getElementById("btnOpenConfig");
  const btnCloseConfig = document.getElementById("btnCloseConfig");
  const inputApiKey = document.getElementById("inputApiKey");
  const selectModel = document.getElementById("selectModel");
  const btnTestApi = document.getElementById("btnTestApi");
  const btnSaveConfig = document.getElementById("btnSaveConfig");
  const testFeedback = document.getElementById("testFeedback");

  const modalHelp = document.getElementById("modalHelp");
  const btnOpenHelp = document.getElementById("btnOpenHelp");
  const btnCloseHelp = document.getElementById("btnCloseHelp");
  const btnHelpCloseOk = document.getElementById("btnHelpCloseOk");

  // 1. Inicialização: Verifica Configuração da API
  async function checkApiConfig() {
    try {
      const res = await fetch("/api/config");
      const data = await res.json();
      if (data.gemini_configured) {
        apiStatusDot.className = "status-dot connected";
        apiStatusText.innerText = `API Conectada (${data.gemini_model})`;
        if (data.gemini_model) {
          selectModel.value = data.gemini_model;
        }
      } else {
        apiStatusDot.className = "status-dot disconnected";
        apiStatusText.innerText = "API Não Configurada";
      }
    } catch (e) {
      console.error("Erro ao verificar configuração:", e);
      apiStatusText.innerText = "Erro no Servidor";
    }
  }

  checkApiConfig();

  // 2. Manipulação de Drag & Drop de Arquivos
  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesSelected(Array.from(e.dataTransfer.files));
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFilesSelected(Array.from(e.target.files));
    }
  });

  function handleFilesSelected(files) {
    selectedFiles = files;
    if (files.length === 1) {
      selectedFilesSummary.innerText = `✓ 1 arquivo pronto para envio: ${files[0].name}`;
    } else {
      selectedFilesSummary.innerText = `✓ ${files.length} arquivos selecionados para lote do Animage.`;
    }
    selectedFilesSummary.style.display = "block";
  }

  // 3. Envio e Início do Processamento
  btnStartProcess.addEventListener("click", async () => {
    if (selectedFiles.length === 0) {
      alert("Por favor selecione ou arraste pelo menos um arquivo de filme ou áudio.");
      return;
    }

    const formData = new FormData();
    selectedFiles.forEach((file) => formData.append("files", file));
    formData.append("mode", selectMode.value);
    formData.append("detail_level", selectDetail.value);
    formData.append("language", selectLang.value);

    btnStartProcess.disabled = true;
    btnStartProcess.innerText = "Enviando para a Sonar...";

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Erro ao iniciar processamento");
      }

      // Limpa seleção após upload
      selectedFiles = [];
      selectedFilesSummary.style.display = "none";
      fileInput.value = "";

      // Inicia polling de status
      startPolling();
    } catch (err) {
      alert("Aviso: " + err.message);
      if (err.message.includes("Chave de API")) {
        modalConfig.classList.add("open");
      }
    } finally {
      btnStartProcess.disabled = false;
      btnStartProcess.innerText = "⚡ Iniciar Processamento Inteligente";
    }
  });

  // 4. Polling e Renderização da Fila
  function startPolling() {
    fetchJobs();
    if (!pollInterval) {
      pollInterval = setInterval(fetchJobs, 2500);
    }
  }

  async function fetchJobs() {
    try {
      const res = await fetch("/api/jobs");
      const data = await res.json();
      currentJobs = data.jobs || [];
      renderQueue(currentJobs);

      // Se temos um job ativo, atualiza o detalhe dele
      if (activeJobId) {
        const currentActive = currentJobs.find((j) => j.id === activeJobId);
        if (currentActive && currentActive.status !== "analyzing_ai") {
          loadJobDetail(activeJobId, false);
        }
      } else if (currentJobs.length > 0 && !activeJobId) {
        // Seleciona automaticamente o primeiro job
        selectJob(currentJobs[0].id);
      }
    } catch (e) {
      console.error("Erro ao sincronizar fila:", e);
    }
  }

  function renderQueue(jobs) {
    if (jobs.length === 0) {
      queueList.innerHTML = `
        <div class="empty-state" style="padding: 2rem 1rem;">
          <div style="font-size: 1.8rem; margin-bottom: 0.5rem; opacity: 0.4;">⏳</div>
          <p style="font-size: 0.85rem;">Nenhum arquivo na fila.<br>Importe seus filmes acima para começar.</p>
        </div>
      `;
      return;
    }

    queueList.innerHTML = "";
    jobs.forEach((job) => {
      const item = document.createElement("div");
      item.className = `queue-item ${job.id === activeJobId ? "active" : ""}`;
      item.onclick = () => selectJob(job.id);

      let badgeColor = "var(--text-dim)";
      let statusLabel = job.status_message || job.status;
      if (job.status === "completed") badgeColor = "var(--sonar-emerald)";
      else if (job.status === "error") badgeColor = "var(--sonar-red)";
      else if (job.status === "analyzing_ai" || job.status === "extracting_audio")
        badgeColor = "var(--sonar-amber)";

      item.innerHTML = `
        <div class="queue-item-header">
          <div class="queue-item-title" title="${job.filename}">${job.filename}</div>
          <span style="font-size: 0.72rem; color: ${badgeColor}; font-weight: 700;">${statusLabel}</span>
        </div>
        <div class="queue-item-meta">
          <span>Modo: ${job.mode}</span>
          ${job.duration ? `<span>${Math.round(job.duration)}s</span>` : ""}
          ${job.entries ? `<span>${job.entries.length} sons</span>` : ""}
        </div>
        <div class="progress-bar-container">
          <div class="progress-bar-fill" style="width: ${job.progress || 0}%;"></div>
        </div>
      `;
      queueList.appendChild(item);
    });
  }

  // 5. Seleção e Exibição do Trabalho no Estúdio
  async function selectJob(jobId) {
    activeJobId = jobId;
    renderQueue(currentJobs);
    loadJobDetail(jobId, true);
  }

  async function loadJobDetail(jobId, reloadMedia = false) {
    try {
      const res = await fetch(`/api/jobs/${jobId}`);
      if (!res.ok) return;
      const job = await res.json();

      studioEmptyState.style.display = "none";
      studioActiveContent.style.display = "flex";

      activeMovieTitle.innerText = job.filename;
      activeMovieMeta.innerText = `Duração: ${Math.round(job.duration || 0)}s | Modo: ${job.mode} | Idioma: ${job.language.toUpperCase()}`;
      activeMovieStatusText.innerText = job.status_message;

      // Habilita / Desabilita botões
      const isCompleted = job.status === "completed";
      btnSaveEdits.disabled = !isCompleted;
      btnDownloadSrt.disabled = !isCompleted;
      btnDownloadVtt.disabled = !isCompleted;

      // Carrega áudio no player se for novo
      if (reloadMedia) {
        audioPlayer.src = `/api/media/${jobId}`;
      }

      activeEntries = job.entries || [];
      renderSubtitlesTable(activeEntries);
      subCount.innerText = activeEntries.length;
    } catch (e) {
      console.error("Erro ao carregar detalhes do trabalho:", e);
    }
  }

  function renderSubtitlesTable(entries) {
    subtitlesTableBody.innerHTML = "";
    if (entries.length === 0) {
      subtitlesTableBody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: var(--text-dim); padding: 2rem;">
            Aguardando conclusão da análise acústica ou nenhum som detectado ainda.
          </td>
        </tr>
      `;
      return;
    }

    entries.forEach((entry, index) => {
      const tr = document.createElement("tr");
      tr.className = "sub-row";
      tr.dataset.index = index;
      tr.dataset.startSec = entry.start_seconds;
      tr.dataset.endSec = entry.end_seconds;

      tr.innerHTML = `
        <td style="color: var(--text-dim); font-size: 0.8rem; font-family: var(--font-mono);">${entry.id || index + 1}</td>
        <td>
          <input type="text" class="time-input" value="${entry.start}" data-field="start" data-index="${index}">
        </td>
        <td>
          <input type="text" class="time-input" value="${entry.end}" data-field="end" data-index="${index}">
        </td>
        <td>
          <input type="text" class="text-input" value="${entry.text}" data-field="text" data-index="${index}">
        </td>
        <td style="text-align: center;">
          <button class="btn btn-secondary btn-sm btn-play-cue" style="padding: 2px 6px; font-size: 0.75rem;" title="Ouvir este trecho" data-start="${entry.start_seconds}">
            ▶ Ouvir
          </button>
          <button class="btn btn-secondary btn-sm btn-del-cue" style="padding: 2px 6px; font-size: 0.75rem; color: var(--sonar-red);" title="Excluir bloco" data-index="${index}">
            ✕
          </button>
        </td>
      `;
      subtitlesTableBody.appendChild(tr);
    });

    // Event listeners para edição inline
    subtitlesTableBody.querySelectorAll("input").forEach((inp) => {
      inp.addEventListener("change", (e) => {
        const idx = parseInt(e.target.dataset.index);
        const field = e.target.dataset.field;
        if (activeEntries[idx]) {
          activeEntries[idx][field] = e.target.value;
          btnSaveEdits.classList.add("btn-cyan");
        }
      });
    });

    // Event listener para botão ouvir trecho
    subtitlesTableBody.querySelectorAll(".btn-play-cue").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const startSec = parseFloat(e.currentTarget.dataset.start);
        if (!isNaN(startSec)) {
          audioPlayer.currentTime = startSec;
          audioPlayer.play();
        }
      });
    });

    // Event listener para exclusão de bloco
    subtitlesTableBody.querySelectorAll(".btn-del-cue").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const idx = parseInt(e.currentTarget.dataset.index);
        activeEntries.splice(idx, 1);
        renderSubtitlesTable(activeEntries);
        subCount.innerText = activeEntries.length;
        btnSaveEdits.classList.add("btn-cyan");
      });
    });
  }

  // 6. Sincronização do Player com a Tabela de Legendas (Timeline Sync)
  audioPlayer.addEventListener("timeupdate", () => {
    const currentTime = audioPlayer.currentTime;
    const rows = subtitlesTableBody.querySelectorAll(".sub-row");

    rows.forEach((row) => {
      const start = parseFloat(row.dataset.startSec);
      const end = parseFloat(row.dataset.endSec);
      if (currentTime >= start && currentTime <= end) {
        row.classList.add("active-time");
      } else {
        row.classList.remove("active-time");
      }
    });
  });

  // Atalhos de Teclado no Monitor de Áudio
  window.addEventListener("keydown", (e) => {
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) return;

    if (e.code === "Space") {
      e.preventDefault();
      if (audioPlayer.paused) audioPlayer.play();
      else audioPlayer.pause();
    } else if (e.key === "j" || e.key === "J") {
      audioPlayer.currentTime = Math.max(0, audioPlayer.currentTime - 2);
    } else if (e.key === "l" || e.key === "L") {
      audioPlayer.currentTime = audioPlayer.currentTime + 2;
    }
  });

  // Adicionar Novo Bloco de Legenda
  btnAddSubtitle.addEventListener("click", () => {
    const curTime = audioPlayer.currentTime || 0;
    const hrs = String(Math.floor(curTime / 3600)).padStart(2, "0");
    const mins = String(Math.floor((curTime % 3600) / 60)).padStart(2, "0");
    const secs = String(Math.floor(curTime % 60)).padStart(2, "0");
    const startTimeStr = `${hrs}:${mins}:${secs},000`;

    const endSec = curTime + 2.5;
    const eHrs = String(Math.floor(endSec / 3600)).padStart(2, "0");
    const eMins = String(Math.floor((endSec % 3600) / 60)).padStart(2, "0");
    const eSecs = String(Math.floor(endSec % 60)).padStart(2, "0");
    const endTimeStr = `${eHrs}:${eMins}:${eSecs},000`;

    activeEntries.push({
      id: activeEntries.length + 1,
      start: startTimeStr,
      end: endTimeStr,
      start_seconds: curTime,
      end_seconds: endSec,
      text: "[Novo som / foley]",
    });

    // Reordena por tempo
    activeEntries.sort((a, b) => a.start_seconds - b.start_seconds);
    renderSubtitlesTable(activeEntries);
    subCount.innerText = activeEntries.length;
    btnSaveEdits.classList.add("btn-cyan");
  });

  // Salvar Edições no Backend
  btnSaveEdits.addEventListener("click", async () => {
    if (!activeJobId) return;

    btnSaveEdits.innerText = "Salvando...";
    try {
      const res = await fetch(`/api/jobs/${activeJobId}/entries`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entries: activeEntries }),
      });
      const data = await res.json();
      if (res.ok) {
        btnSaveEdits.innerText = "✓ Salvo!";
        btnSaveEdits.classList.remove("btn-cyan");
        setTimeout(() => (btnSaveEdits.innerText = "💾 Salvar Edição"), 2000);
      } else {
        alert("Erro ao salvar: " + data.detail);
      }
    } catch (e) {
      alert("Erro na conexão: " + e.message);
    }
  });

  // Downloads Individuais
  btnDownloadSrt.addEventListener("click", () => {
    if (!activeJobId) return;
    window.location.href = `/api/jobs/${activeJobId}/download-srt`;
  });

  btnDownloadVtt.addEventListener("click", () => {
    if (!activeJobId) return;
    window.location.href = `/api/jobs/${activeJobId}/download-vtt`;
  });

  // Download do Lote em ZIP
  btnDownloadAllZip.addEventListener("click", () => {
    window.location.href = "/api/download-all-zip";
  });

  // 7. Modal de Configuração de API
  btnOpenConfig.addEventListener("click", () => {
    modalConfig.classList.add("open");
    testFeedback.style.display = "none";
  });

  btnCloseConfig.addEventListener("click", () => modalConfig.classList.remove("open"));

  btnTestApi.addEventListener("click", async () => {
    const key = inputApiKey.value.trim();
    const model = selectModel.value;

    testFeedback.style.display = "block";
    testFeedback.style.background = "rgba(245, 158, 11, 0.1)";
    testFeedback.style.color = "var(--sonar-amber)";
    testFeedback.innerText = "Testando conexão com a Google Gemini API...";

    try {
      const res = await fetch("/api/config/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gemini_api_key: key, gemini_model: model }),
      });
      const data = await res.json();

      if (data.success) {
        testFeedback.style.background = "rgba(16, 185, 129, 0.15)";
        testFeedback.style.color = "var(--sonar-emerald)";
        testFeedback.innerText = "✓ " + data.message;
      } else {
        testFeedback.style.background = "rgba(239, 68, 68, 0.15)";
        testFeedback.style.color = "var(--sonar-red)";
        testFeedback.innerText = "✕ " + data.message;
      }
    } catch (e) {
      testFeedback.style.background = "rgba(239, 68, 68, 0.15)";
      testFeedback.style.color = "var(--sonar-red)";
      testFeedback.innerText = "Erro na requisição: " + e.message;
    }
  });

  btnSaveConfig.addEventListener("click", async () => {
    const key = inputApiKey.value.trim();
    const model = selectModel.value;

    if (!key) {
      alert("Por favor informe a chave da API antes de salvar.");
      return;
    }

    try {
      const res = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gemini_api_key: key, gemini_model: model }),
      });
      if (res.ok) {
        modalConfig.classList.remove("open");
        checkApiConfig();
        alert("Configurações salvas com sucesso no arquivo .env da Sonar!");
      }
    } catch (e) {
      alert("Erro ao salvar: " + e.message);
    }
  });

  // Modal de Ajuda
  btnOpenHelp.addEventListener("click", () => modalHelp.classList.add("open"));
  btnCloseHelp.addEventListener("click", () => modalHelp.classList.remove("open"));
  btnHelpCloseOk.addEventListener("click", () => modalHelp.classList.remove("open"));

  // Inicia checagem inicial da fila
  fetchJobs();
});
