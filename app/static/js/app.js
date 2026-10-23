/**
 * Aboo Perfumes — Sommelier AI Frontend Application Logic
 */

document.addEventListener("DOMContentLoaded", () => {
  // State
  let currentSessionId = null;
  let currentPerfume = null;
  let currentQuestions = [];
  let userAnswers = {};
  let currentRecommendations = [];
  let debounceTimer = null;

  // DOM Elements
  const searchInput = document.getElementById("perfume-search-input");
  const startBtn = document.getElementById("start-sommelier-btn");
  const autocompleteDropdown = document.getElementById("autocomplete-dropdown");
  const quickPicks = document.querySelectorAll(".quick-pick-chip");
  const passportCard = document.getElementById("perfume-passport");

  const step1 = document.getElementById("step-1-container");
  const step2 = document.getElementById("step-2-container");
  const step3 = document.getElementById("step-3-container");

  const stepNav1 = document.getElementById("step-nav-1");
  const stepNav2 = document.getElementById("step-nav-2");
  const stepNav3 = document.getElementById("step-nav-3");

  const sommelierIntroText = document.getElementById("sommelier-intro-text");
  const questionsList = document.getElementById("questions-list");
  const submitAnswersBtn = document.getElementById("submit-answers-btn");

  const resultsGrid = document.getElementById("recommendations-grid");
  const sommelierNoteEl = document.getElementById("sommelier-note-quote");
  const restartBtn = document.getElementById("restart-btn");
  const copyBtn = document.getElementById("copy-btn");
  const filterTabs = document.querySelectorAll(".filter-tab");
  const loadingOverlay = document.getElementById("loading-overlay");
  const loadingSubtext = document.getElementById("loading-subtext");

  // Show/Hide Loading Overlay
  function showLoading(text, subtext = "") {
    const textEl = document.querySelector(".loading-text");
    if (textEl) textEl.textContent = text;
    if (loadingSubtext) loadingSubtext.textContent = subtext;
    if (loadingOverlay) loadingOverlay.style.display = "flex";
  }

  function hideLoading() {
    if (loadingOverlay) loadingOverlay.style.display = "none";
  }

  // Update Stepper Navigation
  function setStep(stepNum) {
    [stepNav1, stepNav2, stepNav3].forEach((el, idx) => {
      el.classList.remove("active", "completed");
      if (idx + 1 < stepNum) el.classList.add("completed");
      if (idx + 1 === stepNum) el.classList.add("active");
    });

    step1.style.display = stepNum === 1 ? "block" : "none";
    step2.style.display = stepNum === 2 ? "block" : "none";
    step3.style.display = stepNum === 3 ? "block" : "none";

    window.scrollTo({ top: 120, behavior: "smooth" });
  }

  // Live Autocomplete
  searchInput.addEventListener("input", (e) => {
    const val = e.target.value.trim();
    clearTimeout(debounceTimer);

    if (val.length < 2) {
      autocompleteDropdown.style.display = "none";
      return;
    }

    debounceTimer = setTimeout(async () => {
      try {
        const resp = await fetch(`/api/perfumes/search?q=${encodeURIComponent(val)}&limit=6`);
        if (!resp.ok) return;
        const data = await resp.json();

        if (data.results && data.results.length > 0) {
          renderAutocomplete(data.results);
        } else {
          autocompleteDropdown.style.display = "none";
        }
      } catch (err) {
        console.error("Autocomplete error:", err);
      }
    }, 200);
  });

  function renderAutocomplete(results) {
    autocompleteDropdown.innerHTML = "";
    results.forEach((item) => {
      const p = item.perfume;
      const row = document.createElement("div");
      row.className = "autocomplete-item";
      row.innerHTML = `
        <div>
          <span class="auto-brand">${p.brand}</span>
          <span class="auto-name">${p.name}</span>
        </div>
        <span class="auto-family">${p.family}</span>
      `;
      row.addEventListener("click", () => {
        searchInput.value = `${p.brand} ${p.name}`;
        autocompleteDropdown.style.display = "none";
        renderPassport(p);
      });
      autocompleteDropdown.appendChild(row);
    });
    autocompleteDropdown.style.display = "block";
  }

  // Hide autocomplete on click outside
  document.addEventListener("click", (e) => {
    if (!searchInput.contains(e.target) && !autocompleteDropdown.contains(e.target)) {
      autocompleteDropdown.style.display = "none";
    }
  });

  // Quick Pick Chips
  quickPicks.forEach((chip) => {
    chip.addEventListener("click", () => {
      const name = chip.getAttribute("data-perfume");
      searchInput.value = name;
      startInterview(name);
    });
  });

  // Start Sommelier Process on button click or Enter key
  startBtn.addEventListener("click", () => {
    const query = searchInput.value.trim();
    if (query) startInterview(query);
  });

  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      autocompleteDropdown.style.display = "none";
      const query = searchInput.value.trim();
      if (query) startInterview(query);
    }
  });

  // Step 1 -> Step 2: Start Interview
  async function startInterview(perfumeName) {
    showLoading("Анализ ольфакторного профиля...", `Изучаем ноты и ДНК аромата «${perfumeName}»`);
    try {
      const resp = await fetch("/api/sommelier/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ perfume_name: perfumeName })
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Не удалось инициализировать сомелье");
      }

      const data = await resp.json();
      currentSessionId = data.session_id;
      currentPerfume = data.matched_perfume;
      currentQuestions = data.questions;
      userAnswers = {};

      renderPassport(currentPerfume);
      renderQuestions(data.analysis, currentQuestions);
      setStep(2);
    } catch (err) {
      alert("Ошибка: " + err.message);
    } finally {
      hideLoading();
    }
  }

  // Render Perfume Passport Card
  function renderPassport(p) {
    if (!p) return;

    const brandEl = document.getElementById("passport-brand");
    if (brandEl) brandEl.textContent = p.brand || "";

    const nameEl = document.getElementById("passport-name") || document.getElementById("passport-title");
    if (nameEl) nameEl.textContent = p.name || "";

    const familyEl = document.getElementById("passport-family");
    if (familyEl) familyEl.textContent = (p.family || "") + (p.subfamily ? ` • ${p.subfamily}` : "");

    const charEl = document.getElementById("passport-character");
    if (charEl) charEl.textContent = p.character ? `«${p.character}»` : "";

    const topEl = document.getElementById("passport-top");
    const heartEl = document.getElementById("passport-heart");
    const baseEl = document.getElementById("passport-base");

    if (topEl && p.top_notes) {
      topEl.innerHTML = p.top_notes.map(n => `<span class="note-chip">${n}</span>`).join("");
    }
    if (heartEl && p.heart_notes) {
      heartEl.innerHTML = p.heart_notes.map(n => `<span class="note-chip">${n}</span>`).join("");
    }
    if (baseEl && p.base_notes) {
      baseEl.innerHTML = p.base_notes.map(n => `<span class="note-chip">${n}</span>`).join("");
    }

    if (passportCard) {
      passportCard.style.display = "block";
    }
  }

  // Render 3 Interview Questions
  function renderQuestions(analysis, questions) {
    sommelierIntroText.textContent = analysis;
    questionsList.innerHTML = "";

    questions.forEach((q) => {
      const qBlock = document.createElement("div");
      qBlock.className = "question-block";
      qBlock.id = `question-block-${q.id}`;

      let optionsHtml = "";
      if (q.options && q.options.length > 0) {
        optionsHtml = q.options.map((opt) => `
          <button type="button" class="option-btn" data-qid="${q.id}" data-val="${opt}">
            <span>•</span> ${opt}
          </button>
        `).join("");
      }

      qBlock.innerHTML = `
        <div class="question-header">
          <div class="question-badge">${q.id}</div>
          <div class="question-title">${q.question}</div>
        </div>
        <div class="options-grid" id="options-grid-${q.id}">
          ${optionsHtml}
        </div>
        <input 
          type="text" 
          class="custom-answer-input" 
          id="custom-input-${q.id}" 
          placeholder="Или напиши свой ответ своими словами..."
        />
      `;

      questionsList.appendChild(qBlock);

      // Attach option listeners
      const optBtns = qBlock.querySelectorAll(".option-btn");
      const customInput = qBlock.querySelector(".custom-answer-input");

      optBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
          optBtns.forEach(b => b.classList.remove("selected"));
          btn.classList.add("selected");
          userAnswers[q.id] = btn.getAttribute("data-val");
          customInput.value = "";
          qBlock.classList.add("answered");
          checkReadyToSubmit();
        });
      });

      customInput.addEventListener("input", (e) => {
        const val = e.target.value.trim();
        if (val) {
          optBtns.forEach(b => b.classList.remove("selected"));
          userAnswers[q.id] = val;
          qBlock.classList.add("answered");
        } else {
          delete userAnswers[q.id];
          qBlock.classList.remove("answered");
        }
        checkReadyToSubmit();
      });
    });

    submitAnswersBtn.disabled = true;
  }

  function checkReadyToSubmit() {
    const answeredCount = Object.keys(userAnswers).length;
    submitAnswersBtn.disabled = answeredCount < currentQuestions.length;
  }

  // Step 2 -> Step 3: Submit Answers & Fetch Recommendations
  submitAnswersBtn.addEventListener("click", async () => {
    const answersPayload = Object.entries(userAnswers).map(([qid, ans]) => ({
      question_id: parseInt(qid),
      answer: ans
    }));

    showLoading("Формирование ТОП-10...", "ИИ подбирает формулы и валидирует реальность каждого аромата по каталогу");

    try {
      const resp = await fetch("/api/sommelier/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: currentSessionId,
          answers: answersPayload
        })
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Ошибка при генерации рекомендаций");
      }

      const data = await resp.json();
      currentRecommendations = data.recommendations;
      if (sommelierNoteEl) {
        sommelierNoteEl.textContent = data.sommelier_note || "Вот твой персональный ТОП-10:";
      }

      renderRecommendations(currentRecommendations);
      setStep(3);
    } catch (err) {
      alert("Ошибка: " + err.message);
    } finally {
      hideLoading();
    }
  });

  // Render Top 10 Recommendations
  function renderRecommendations(items, filter = "all") {
    resultsGrid.innerHTML = "";

    const filtered = items.filter((item) => {
      if (filter === "hits") return item.rank <= 3;
      if (filter === "variations") return item.rank >= 4 && item.rank <= 7;
      if (filter === "bold") return item.rank >= 8;
      return true;
    });

    filtered.forEach((item) => {
      const card = document.createElement("div");
      card.className = `perfume-card ${item.rank <= 3 ? "top-3" : ""}`;

      let rankClass = `rank-${item.rank}`;
      if (item.rank > 3) rankClass = "rank-other";

      const notesHtml = (item.notes || []).map(n => `<span class="card-note-badge">${n}</span>`).join("");

      card.innerHTML = `
        <div class="card-rank ${rankClass}">#${item.rank}</div>
        <div class="card-body">
          <div class="card-top-row">
            <div>
              <div class="card-brand">${item.brand}</div>
              <div class="card-title">${item.name}</div>
            </div>
            <div class="card-family-pill">${item.family}</div>
          </div>
          <div class="card-reason">
            <strong>Почему тебе зайдет:</strong> ${item.reason}
          </div>
          <div class="card-notes-row">
            <span class="card-notes-label">Ноты:</span>
            ${notesHtml}
            <div class="verified-stamp">
              <span>✓</span> Подтвержден в каталоге
            </div>
          </div>
        </div>
      `;

      resultsGrid.appendChild(card);
    });
  }

  // Filter Tabs
  filterTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      filterTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      renderRecommendations(currentRecommendations, tab.getAttribute("data-filter"));
    });
  });

  // Restart Flow
  restartBtn.addEventListener("click", () => {
    currentSessionId = null;
    currentPerfume = null;
    currentQuestions = [];
    userAnswers = {};
    currentRecommendations = [];
    searchInput.value = "";
    passportCard.style.display = "none";
    setStep(1);
  });

  // Copy Top 10 to Clipboard
  copyBtn.addEventListener("click", () => {
    if (!currentRecommendations || currentRecommendations.length === 0) return;

    let text = `👑 ТОП-10 АРОМАТОВ ОТ ПАРФЮМЕРНОГО СОМЕЛЬЕ (на замену ${currentPerfume ? currentPerfume.brand + ' ' + currentPerfume.name : ''}):\n\n`;
    currentRecommendations.forEach((item) => {
      text += `#${item.rank} ${item.brand} — ${item.name} (${item.family})\n`;
      text += `Ноты: ${(item.notes || []).join(", ")}\n`;
      text += `Почему подойдет: ${item.reason}\n\n`;
    });

    navigator.clipboard.writeText(text).then(() => {
      const orig = copyBtn.innerHTML;
      copyBtn.innerHTML = `<span>✓</span> Скопировано!`;
      setTimeout(() => copyBtn.innerHTML = orig, 2500);
    });
  });
});
