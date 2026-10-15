// Sonar LSE Studio - Plataforma de Acessibilidade Audiovisual, Versionamento & Metragem
document.addEventListener("DOMContentLoaded", () => {
  // Estado da Aplicação
  let activeTab = "files"; // 'files' ou 'url'
  let selectedFiles = [];
  let currentJobs = [];
  let activeJobId = null;
  let activeJob = null;
  let activeEntries = [];
  let activeHistory = [];
  let currentHistoryIndex = -1; // para Undo/Redo local
  let timecodeMode = "srt"; // 'srt' ou 'smpte'
  let activeFps = 24.0;
  let pollInterval = null;

  // Elementos do DOM - Cabeçalho e Configuração
  const apiStatusDot = document.getElementById("apiStatusDot");
  const apiStatusText = document.getElementById("apiStatusText");
  const btnOpenConfig = document.getElementById("btnOpenConfig");
  const btnCloseConfig = document.getElementById("btnCloseConfig");
  const modalConfig = document.getElementById("modalConfig");
  const inputApiKey = document.getElementById("inputApiKey");
  const selectModel = document.getElementById("selectModel");
  const btnTestApi = document.getElementById("btnTestApi");
  const btnSaveConfig = document.getElementById("btnSaveConfig");
  const testFeedback = document.getElementById("testFeedback");

  const modalHelp = document.getElementById("modalHelp");
  const btnOpenHelp = document.getElementById("btnOpenHelp");
  const btnCloseHelp = document.getElementById("btnCloseHelp");
  const btnHelpCloseOk = document.getElementById("btnHelpCloseOk");

  // Elementos do DOM - Importação (Tabs, Arquivos e URL)
  const tabFiles = document.getElementById("tabFiles");
  const tabUrl = document.getElementById("tabUrl");
  const panelTabFiles = document.getElementById("panelTabFiles");
  const panelTabUrl = document.getElementById("panelTabUrl");
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const selectedFilesSummary = document.getElementById("selectedFilesSummary");
  const inputStreamingUrl = document.getElementById("inputStreamingUrl");
  const selectMode = document.getElementById("selectMode");
  const selectDetail = document.getElementById("selectDetail");
  const selectLang = document.getElementById("selectLang");
  const btnStartProcess = document.getElementById("btnStartProcess");

  // Elementos do DOM - Fila de Produção
  const queueList = document.getElementById("queueList");
  const btnDownloadAllZip = document.getElementById("btnDownloadAllZip");

  // Elementos do DOM - Estúdio Ativo
  const studioEmptyState = document.getElementById("studioEmptyState");
  const studioActiveContent = document.getElementById("studioActiveContent");
  const activeMovieTitle = document.getElementById("activeMovieTitle");
  const activeMovieMeta = document.getElementById("activeMovieMeta");
  const activeMovieStatusText = document.getElementById("activeMovieStatusText");
  const selectFps = document.getElementById("selectFps");
  const playerTypeLabel = document.getElementById("playerTypeLabel");

  const videoContainer = document.getElementById("videoContainer");
  const videoPlayer = document.getElementById("videoPlayer");
  const audioContainer = document.getElementById("audioContainer");
  const audioPlayer = document.getElementById("audioPlayer");

  const subCount = document.getElementById("subCount");
  const entriesModeBadge = document.getElementById("entriesModeBadge");
  const btnToggleTimecodeMode = document.getElementById("btnToggleTimecodeMode");
  const lblTimecodeMode = document.getElementById("lblTimecodeMode");
  const btnAddSubtitle = document.getElementById("btnAddSubtitle");
  const subtitlesTableBody = document.getElementById("subtitlesTableBody");

  // Ações de Versionamento e Exportação
  const btnUndo = document.getElementById("btnUndo");
  const btnRedo = document.getElementById("btnRedo");
  const btnHistory = document.getElementById("btnHistory");
  const revBadge = document.getElementById("revBadge");
  const btnSaveEdits = document.getElementById("btnSaveEdits");
  const btnDownloadSrt = document.getElementById("btnDownloadSrt");
  const btnDownloadVtt = document.getElementById("btnDownloadVtt");
  const btnDownloadScript = document.getElementById("btnDownloadScript");

  // Modal de Histórico de Versões
  const modalHistory = document.getElementById("modalHistory");
  const btnCloseHistory = document.getElementById("btnCloseHistory");
  const btnCloseHistoryFooter = document.getElementById("btnCloseHistoryFooter");
  const historyListContainer = document.getElementById("historyListContainer");

  // Player Ativo Dinâmico (Vídeo ou Áudio)
  function getActivePlayer() {
    if (activeJob && activeJob.is_video) {
      return videoPlayer;
    }
    return audioPlayer;
  }

  // 1. Inicialização e Verificação da API
  async function checkApiConfig() {
    try {
      const res = await fetch("/api/config");
      const data = await res.json();
      if (data.gemini_configured) {
        apiStatusDot.className = "status-dot connected";
        apiStatusText.innerText = `API Conectada (${data.gemini_model})`;
        if (data.gemini_model) selectModel.value = data.gemini_model;
      } else {
        apiStatusDot.className = "status-dot disconnected";
        apiStatusText.innerText = "API Não Configurada";
      }
    } catch (e) {
      apiStatusText.innerText = "Erro no Servidor";
    }
  }
  checkApiConfig();

  // 2. Gestão de Abas de Importação
  tabFiles.addEventListener("click", () => {
    activeTab = "files";
    tabFiles.classList.add("active");
    tabUrl.classList.remove("active");
    panelTabFiles.style.display = "block";
    panelTabUrl.style.display = "none";
  });

  tabUrl.addEventListener("click", () => {
    activeTab = "url";
    tabUrl.classList.add("active");
    tabFiles.classList.remove("active");
    panelTabFiles.style.display = "none";
    panelTabUrl.style.display = "block";
  });

  // Drag and drop de arquivos
  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
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
      selectedFilesSummary.innerText = `✓ 1 arquivo selecionado: ${files[0].name}`;
    } else {
      selectedFilesSummary.innerText = `✓ ${files.length} arquivos selecionados para lote do Animage.`;
    }
    selectedFilesSummary.style.display = "block";
  }

  // 3. Iniciar Processamento (Upload ou URL Streaming)
  btnStartProcess.addEventListener("click", async () => {
    const mode = selectMode.value;
    const detail = selectDetail.value;
    const lang = selectLang.value;

    if (activeTab === "url") {
      const url = inputStreamingUrl.value.trim();
      if (!url) {
        alert("Por favor cole a URL do vídeo/streaming (YouTube, Vimeo ou link direto).");
        return;
      }

      btnStartProcess.disabled = true;
      btnStartProcess.innerText = "Conectando ao Stream...";

      try {
        const res = await fetch("/api/ingest-url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: url,
            mode: mode,
            detail_level: detail,
            language: lang,
          }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Erro ao processar streaming");

        inputStreamingUrl.value = "";
        startPolling();
        if (data.job_id) selectJob(data.job_id);
      } catch (err) {
        alert("Aviso: " + err.message);
        if (err.message.includes("Chave de API")) modalConfig.classList.add("open");
      } finally {
        btnStartProcess.disabled = false;
        btnStartProcess.innerText = "⚡ Iniciar Processamento Inteligente";
      }
    } else {
      // Importação por Arquivo Local
      if (selectedFiles.length === 0) {
        alert("Por favor selecione ou arraste pelo menos um arquivo de vídeo ou áudio.");
        return;
      }

      const formData = new FormData();
      selectedFiles.forEach((file) => formData.append("files", file));
      formData.append("mode", mode);
      formData.append("detail_level", detail);
      formData.append("language", lang);

      btnStartProcess.disabled = true;
      btnStartProcess.innerText = "Enviando para a Sonar...";

      try {
        const res = await fetch("/api/upload", {
          method: "POST",
          body: formData,
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Erro no envio");

        selectedFiles = [];
        selectedFilesSummary.style.display = "none";
        fileInput.value = "";

        startPolling();
        if (data.job_ids && data.job_ids.length > 0) {
          selectJob(data.job_ids[0]);
        }
      } catch (err) {
        alert("Aviso: " + err.message);
        if (err.message.includes("Chave de API")) modalConfig.classList.add("open");
      } finally {
        btnStartProcess.disabled = false;
        btnStartProcess.innerText = "⚡ Iniciar Processamento Inteligente";
      }
    }
  });

  // 4. Polling e Sincronização da Fila
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

      if (activeJobId) {
        const currentActive = currentJobs.find((j) => j.id === activeJobId);
        if (currentActive && (currentActive.status !== "analyzing_ai" && currentActive.status !== "extracting_audio" && currentActive.status !== "downloading_url")) {
          loadJobDetail(activeJobId, false);
        } else if (currentActive) {
          activeMovieStatusText.innerText = currentActive.status_message;
        }
      } else if (currentJobs.length > 0 && !activeJobId) {
        selectJob(currentJobs[0].id);
      }
    } catch (e) {
      console.error("Erro na sincronização:", e);
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
      else badgeColor = "var(--sonar-amber)";

      const modeBadge = job.mode === "audiodescricao" ? "👁️ AD" : "🔊 Foley";

      item.innerHTML = `
        <div class="queue-item-header">
          <div class="queue-item-title" title="${job.filename}">${job.filename}</div>
          <span style="font-size: 0.72rem; color: ${badgeColor}; font-weight: 700;">${statusLabel}</span>
        </div>
        <div class="queue-item-meta">
          <span style="color: var(--sonar-cyan); font-weight: 600;">${modeBadge}</span>
          ${job.duration ? `<span>${Math.round(job.duration)}s</span>` : ""}
          ${job.entries ? `<span>${job.entries.length} blocos</span>` : ""}
          ${job.is_video ? `<span>🎥 Vídeo</span>` : `<span>🎵 Áudio</span>`}
        </div>
        <div class="progress-bar-container">
          <div class="progress-bar-fill" style="width: ${job.progress || 0}%;"></div>
        </div>
      `;
      queueList.appendChild(item);
    });
  }

  // 5. Seleção e Exibição de Trabalho no Estúdio
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
      activeJob = job;

      studioEmptyState.style.display = "none";
      studioActiveContent.style.display = "flex";

      activeMovieTitle.innerText = job.filename;
      const modeLabel = job.mode === "audiodescricao" ? "Audiodescrição Roteirizada (AD)" : "Sonoplastia e Foley (LSE)";
      activeMovieMeta.innerText = `Duração: ${Math.round(job.duration || 0)}s | Modo: ${modeLabel} | Idioma: ${job.language.toUpperCase()}`;
      activeMovieStatusText.innerText = job.status_message;

      // Badges
      entriesModeBadge.innerText = job.mode === "audiodescricao" ? "Audiodescrição (AD)" : "LSE Foley";
      if (job.mode === "audiodescricao") {
        entriesModeBadge.style.background = "rgba(245, 158, 11, 0.15)";
        entriesModeBadge.style.color = "var(--sonar-amber)";
      } else {
        entriesModeBadge.style.background = "rgba(6, 182, 212, 0.15)";
        entriesModeBadge.style.color = "var(--sonar-cyan)";
      }

      // Habilitar / Desabilitar botões
      const isCompleted = job.status === "completed";
      btnSaveEdits.disabled = !isCompleted;
      btnDownloadSrt.disabled = !isCompleted;
      btnDownloadVtt.disabled = !isCompleted;
      btnDownloadScript.disabled = !isCompleted;
      btnHistory.disabled = !isCompleted;

      // Versionamento
      activeHistory = job.history || [];
      revBadge.innerText = job.current_revision_id || (activeHistory.length > 0 ? activeHistory[activeHistory.length - 1].revision_id : "v1");
      updateUndoRedoButtons();

      // Configuração de Player Híbrido (Vídeo vs Áudio)
      if (reloadMedia) {
        const mediaUrl = `/api/media/${jobId}`;
        if (job.is_video) {
          videoContainer.style.display = "flex";
          audioContainer.style.display = "none";
          playerTypeLabel.innerText = "Monitor Audiovisual da Sonar (Vídeo Sincronizado)";
          videoPlayer.src = mediaUrl;
          videoPlayer.load();
        } else {
          videoContainer.style.display = "none";
          audioContainer.style.display = "block";
          playerTypeLabel.innerText = "Monitor Acústico da Sonar (Áudio Sincronizado)";
          audioPlayer.src = mediaUrl;
          audioPlayer.load();
        }
      }

      activeEntries = job.entries || [];
      renderSubtitlesTable(activeEntries);
      subCount.innerText = activeEntries.length;
    } catch (e) {
      console.error("Erro ao carregar detalhes:", e);
    }
  }

  // 6. Conversão de Metragem e SMPTE Timecode
  function secondsToSmpte(sec, fps) {
    if (sec < 0) sec = 0;
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    const remainder = sec - Math.floor(sec);
    const frame = Math.round(remainder * fps);
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}:${String(frame).padStart(2, "0")}`;
  }

  function secondsToSrt(sec) {
    if (sec < 0) sec = 0;
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.round((sec - Math.floor(sec)) * 1000);
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")},${String(ms).padStart(3, "0")}`;
  }

  function parseTimeToSeconds(timeStr, fps) {
    const clean = timeStr.trim();
    if (clean.includes(":")) {
      const parts = clean.split(":");
      if (parts.length === 4) {
        // SMPTE HH:MM:SS:FF
        return parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseInt(parts[2]) + parseInt(parts[3]) / fps;
      } else if (parts.length === 3) {
        // SRT HH:MM:SS,mmm
        const subParts = parts[2].replace(".", ",").split(",");
        const s = parseInt(subParts[0]) || 0;
        const ms = parseInt(subParts[1]) || 0;
        return parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + s + ms / 1000;
      }
    }
    return parseFloat(clean) || 0.0;
  }

  // Alternância do Modo de Timecode (SRT ms vs SMPTE Frames)
  btnToggleTimecodeMode.addEventListener("click", () => {
    if (timecodeMode === "srt") {
      timecodeMode = "smpte";
      lblTimecodeMode.innerText = `SMPTE (${activeFps}fps)`;
      lblTimecodeMode.style.color = "var(--sonar-cyan)";
    } else {
      timecodeMode = "srt";
      lblTimecodeMode.innerText = "SRT (ms)";
      lblTimecodeMode.style.color = "var(--sonar-amber)";
    }
    renderSubtitlesTable(activeEntries);
  });

  selectFps.addEventListener("change", (e) => {
    activeFps = parseFloat(e.target.value) || 24.0;
    if (timecodeMode === "smpte") {
      lblTimecodeMode.innerText = `SMPTE (${activeFps}fps)`;
    }
    renderSubtitlesTable(activeEntries);
  });

  // 7. Renderização da Tabela de Entradas
  function renderSubtitlesTable(entries) {
    subtitlesTableBody.innerHTML = "";
    if (entries.length === 0) {
      subtitlesTableBody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: var(--text-dim); padding: 2rem;">
            Aguardando análise da metragem acústica ou nenhum evento sonoro/AD gerado ainda.
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

      const startTimeFormatted = timecodeMode === "smpte" ? secondsToSmpte(entry.start_seconds, activeFps) : entry.start;
      const endTimeFormatted = timecodeMode === "smpte" ? secondsToSmpte(entry.end_seconds, activeFps) : entry.end;

      tr.innerHTML = `
        <td style="color: var(--text-dim); font-size: 0.8rem; font-family: var(--font-mono);">${entry.id || index + 1}</td>
        <td>
          <input type="text" class="time-input" value="${startTimeFormatted}" data-field="start" data-index="${index}">
        </td>
        <td>
          <input type="text" class="time-input" value="${endTimeFormatted}" data-field="end" data-index="${index}">
        </td>
        <td>
          <input type="text" class="text-input" value="${entry.text}" data-field="text" data-index="${index}">
        </td>
        <td style="text-align: center;">
          <button class="btn btn-secondary btn-sm btn-play-cue" style="padding: 2px 6px; font-size: 0.75rem;" title="Ouvir/assistir este trecho" data-start="${entry.start_seconds}">
            ▶ Ir
          </button>
          <button class="btn btn-secondary btn-sm btn-del-cue" style="padding: 2px 6px; font-size: 0.75rem; color: var(--sonar-red);" title="Excluir bloco" data-index="${index}">
            ✕
          </button>
        </td>
      `;
      subtitlesTableBody.appendChild(tr);
    });

    // Edição Inline com cálculo automático de segundos
    subtitlesTableBody.querySelectorAll("input").forEach((inp) => {
      inp.addEventListener("change", (e) => {
        const idx = parseInt(e.target.dataset.index);
        const field = e.target.dataset.field;
        if (activeEntries[idx]) {
          const val = e.target.value.trim();
          if (field === "start") {
            const sec = parseTimeToSeconds(val, activeFps);
            activeEntries[idx].start_seconds = sec;
            activeEntries[idx].start = secondsToSrt(sec);
            activeEntries[idx].smpte_start = secondsToSmpte(sec, activeFps);
          } else if (field === "end") {
            const sec = parseTimeToSeconds(val, activeFps);
            activeEntries[idx].end_seconds = sec;
            activeEntries[idx].end = secondsToSrt(sec);
            activeEntries[idx].smpte_end = secondsToSmpte(sec, activeFps);
          } else {
            activeEntries[idx].text = val;
          }
          btnSaveEdits.classList.add("btn-cyan");
        }
      });
    });

    // Botão Ir para o trecho
    subtitlesTableBody.querySelectorAll(".btn-play-cue").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const startSec = parseFloat(e.currentTarget.dataset.start);
        if (!isNaN(startSec)) {
          const player = getActivePlayer();
          player.currentTime = startSec;
          player.play();
        }
      });
    });

    // Excluir bloco
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

  // 8. Sincronização da Timeline no Player Ativo
  function syncTimelineHighlight() {
    const player = getActivePlayer();
    const curTime = player.currentTime;
    const rows = subtitlesTableBody.querySelectorAll(".sub-row");

    rows.forEach((row) => {
      const start = parseFloat(row.dataset.startSec);
      const end = parseFloat(row.dataset.endSec);
      if (curTime >= start && curTime <= end) {
        row.classList.add("active-time");
      } else {
        row.classList.remove("active-time");
      }
    });
  }

  videoPlayer.addEventListener("timeupdate", syncTimelineHighlight);
  audioPlayer.addEventListener("timeupdate", syncTimelineHighlight);

  // 9. Atalhos de Teclado Globais (Play/Pause, Seek, Undo, Redo)
  window.addEventListener("keydown", (e) => {
    // Se o usuário estiver digitando em um input de texto, permite Ctrl+Z nativo se quiser,
    // ou se pressionar Ctrl+Z fora, desfaz o snapshot
    if (e.ctrlKey && (e.key === "z" || e.key === "Z")) {
      if (e.target.tagName !== "INPUT") {
        e.preventDefault();
        performUndo();
        return;
      }
    }
    if (e.ctrlKey && (e.key === "y" || e.key === "Y")) {
      if (e.target.tagName !== "INPUT") {
        e.preventDefault();
        performRedo();
        return;
      }
    }

    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) return;

    const player = getActivePlayer();
    if (e.code === "Space") {
      e.preventDefault();
      if (player.paused) player.play();
      else player.pause();
    } else if (e.key === "j" || e.key === "J") {
      player.currentTime = Math.max(0, player.currentTime - 2);
    } else if (e.key === "l" || e.key === "L") {
      player.currentTime = player.currentTime + 2;
    }
  });

  // 10. Adicionar Novo Bloco de Legenda / Audiodescrição
  btnAddSubtitle.addEventListener("click", () => {
    const player = getActivePlayer();
    const curTime = player.currentTime || 0;
    const endSec = curTime + 2.5;

    const isAD = activeJob && activeJob.mode === "audiodescricao";
    const defaultText = isAD ? "[AD] " : "[Som / Foley]";

    activeEntries.push({
      id: activeEntries.length + 1,
      start: secondsToSrt(curTime),
      end: secondsToSrt(endSec),
      start_seconds: round(curTime, 3),
      end_seconds: round(endSec, 3),
      smpte_start: secondsToSmpte(curTime, activeFps),
      smpte_end: secondsToSmpte(endSec, activeFps),
      duration: 2.5,
      text: defaultText,
    });

    activeEntries.sort((a, b) => a.start_seconds - b.start_seconds);
    renderSubtitlesTable(activeEntries);
    subCount.innerText = activeEntries.length;
    btnSaveEdits.classList.add("btn-cyan");
  });

  function round(num, dec) {
    return Math.round(num * Math.pow(10, dec)) / Math.pow(10, dec);
  }

  // 11. Salvar Versão / Snapshot no Backend
  btnSaveEdits.addEventListener("click", async () => {
    if (!activeJobId) return;

    btnSaveEdits.innerText = "Salvando...";
    try {
      const res = await fetch(`/api/jobs/${activeJobId}/entries`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entries: activeEntries,
          description: `Edição em ${new Date().toLocaleTimeString("pt-BR")}`,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        btnSaveEdits.innerText = "✓ Versão Salva!";
        btnSaveEdits.classList.remove("btn-cyan");
        // Recarrega detalhes para atualizar histórico
        loadJobDetail(activeJobId, false);
        setTimeout(() => (btnSaveEdits.innerText = "💾 Salvar Versão"), 2000);
      } else {
        alert("Erro ao salvar: " + data.detail);
      }
    } catch (e) {
      alert("Erro na conexão: " + e.message);
    }
  });

  // 12. Versionamento e Histórico de Snapshots (Undo / Redo / Rollback)
  function updateUndoRedoButtons() {
    if (!activeHistory || activeHistory.length <= 1) {
      btnUndo.disabled = true;
      btnRedo.disabled = true;
    } else {
      btnUndo.disabled = false;
      btnRedo.disabled = false;
    }
  }

  async function performUndo() {
    if (!activeJobId || !activeHistory || activeHistory.length <= 1) return;
    // O último item é o atual, restauramos o penúltimo
    const currentRev = activeJob.current_revision_id;
    let targetIndex = -1;
    for (let i = 0; i < activeHistory.length; i++) {
      if (activeHistory[i].revision_id === currentRev) {
        targetIndex = i;
        break;
      }
    }

    if (targetIndex > 0) {
      const targetRev = activeHistory[targetIndex - 1].revision_id;
      await rollbackToRevision(targetRev);
    }
  }

  async function performRedo() {
    if (!activeJobId || !activeHistory) return;
    const currentRev = activeJob.current_revision_id;
    let targetIndex = -1;
    for (let i = 0; i < activeHistory.length; i++) {
      if (activeHistory[i].revision_id === currentRev) {
        targetIndex = i;
        break;
      }
    }

    if (targetIndex >= 0 && targetIndex < activeHistory.length - 1) {
      const targetRev = activeHistory[targetIndex + 1].revision_id;
      await rollbackToRevision(targetRev);
    }
  }

  btnUndo.addEventListener("click", performUndo);
  btnRedo.addEventListener("click", performRedo);

  async function rollbackToRevision(revisionId) {
    if (!activeJobId) return;
    try {
      const res = await fetch(`/api/jobs/${activeJobId}/rollback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ revision_id: revisionId }),
      });
      const data = await res.json();
      if (res.ok) {
        modalHistory.classList.remove("open");
        loadJobDetail(activeJobId, false);
      } else {
        alert("Erro no rollback: " + data.detail);
      }
    } catch (e) {
      alert("Erro ao restaurar versão: " + e.message);
    }
  }

  btnHistory.addEventListener("click", async () => {
    if (!activeJobId) return;
    modalHistory.classList.add("open");
    historyListContainer.innerHTML = "<div style='color: var(--text-dim); padding: 1rem;'>Carregando histórico...</div>";

    try {
      const res = await fetch(`/api/jobs/${activeJobId}/history`);
      const data = await res.json();
      const list = data.history || [];

      if (list.length === 0) {
        historyListContainer.innerHTML = "<div style='color: var(--text-dim); padding: 1rem;'>Nenhuma revisão gravada ainda.</div>";
        return;
      }

      historyListContainer.innerHTML = "";
      list.forEach((item) => {
        const div = document.createElement("div");
        div.className = `history-item ${item.revision_id === activeJob.current_revision_id ? "active-rev" : ""}`;

        const dateStr = new Date(item.timestamp * 1000).toLocaleTimeString("pt-BR", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });

        div.innerHTML = `
          <div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span class="rev-tag">${item.revision_id}</span>
              <strong style="font-size: 0.88rem; color: var(--text-main);">${item.description}</strong>
            </div>
            <div style="font-size: 0.76rem; color: var(--text-dim); margin-top: 2px;">
              Horário: ${dateStr} | Quantidade: ${item.entry_count} blocos
            </div>
          </div>
          <div>
            <button class="btn btn-secondary btn-sm btn-restore-rev" data-revid="${item.revision_id}" ${item.revision_id === activeJob.current_revision_id ? "disabled" : ""}>
              ${item.revision_id === activeJob.current_revision_id ? "Ativa" : "Restaurar"}
            </button>
          </div>
        `;
        historyListContainer.appendChild(div);
      });

      historyListContainer.querySelectorAll(".btn-restore-rev").forEach((b) => {
        b.addEventListener("click", (e) => {
          const revId = e.currentTarget.dataset.revid;
          rollbackToRevision(revId);
        });
      });
    } catch (e) {
      historyListContainer.innerHTML = "<div style='color: var(--sonar-red); padding: 1rem;'>Erro ao carregar histórico.</div>";
    }
  });

  btnCloseHistory.addEventListener("click", () => modalHistory.classList.remove("open"));
  btnCloseHistoryFooter.addEventListener("click", () => modalHistory.classList.remove("open"));

  // 13. Downloads Individuais e em Lote
  btnDownloadSrt.addEventListener("click", () => {
    if (!activeJobId) return;
    window.location.href = `/api/jobs/${activeJobId}/download-srt`;
  });

  btnDownloadVtt.addEventListener("click", () => {
    if (!activeJobId) return;
    window.location.href = `/api/jobs/${activeJobId}/download-vtt`;
  });

  btnDownloadScript.addEventListener("click", () => {
    if (!activeJobId) return;
    window.location.href = `/api/jobs/${activeJobId}/download-script?fps=${activeFps}`;
  });

  btnDownloadAllZip.addEventListener("click", () => {
    window.location.href = "/api/download-all-zip";
  });

  // 14. Modais de Configuração e Ajuda
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

  btnOpenHelp.addEventListener("click", () => modalHelp.classList.add("open"));
  btnCloseHelp.addEventListener("click", () => modalHelp.classList.remove("open"));
  btnHelpCloseOk.addEventListener("click", () => modalHelp.classList.remove("open"));

  // Inicia checagem inicial
  fetchJobs();
});
