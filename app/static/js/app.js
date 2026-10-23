/**
 * ABOO PERFUMES — Aboo AI Interactive Sommelier Frontend
 * Powered by Google Gemini & Scento API (130,000+ flacons).
 * 
 * Features:
 * 1. Interactive Chat Assistant «Aboo AI» with natural dialog flow;
 * 2. 3 Mascot Animated States:
 *    - isIdle: gentle breathing + soft glowing star on mask;
 *    - isThinking: intense neon pulsation + status message;
 *    - isAnswering: vocal rhythm pulse + smooth message delivery;
 * 3. Step 0 (Category), Step 1 (DNA Input), Step 2 (Strictly 5 questions),
 *    Step 3 (Chain-of-Thought & Ranked TOP-10 with unique reasons & authentic bottle photos);
 * 4. Dual View: Interactive Chat (Primary) & Classic Stepper (Secondary).
 */

document.addEventListener("DOMContentLoaded", () => {
  // ==========================================
  // Application State
  // ==========================================
  let selectedCategory = "Унисекс";
  let currentSessionId = null;
  let currentPerfume = null;
  let currentQuestions = [];
  let userAnswers = {}; // { question_id: answer_text }
  let currentQuestionIndex = 0; // 0 to 4 (questions 1 to 5)
  let currentRecommendations = [];
  let currentChainOfThought = null;
  let chatStep = "category"; // "category" -> "perfume" -> "interview" -> "results"
  let isAiBusy = false;

  // DOM Elements - Mascot Stage & HUD
  const abooAvatarStage = document.getElementById("aboo-avatar-stage");
  const abooCharacterStage = document.getElementById("aboo-character-stage");
  const characterStatusLabel = document.getElementById("character-status-label");
  const abooStatusText = document.getElementById("aboo-status-text");
  const chatProgressBar = document.getElementById("chat-progress-bar");
  const quizStepBubble = document.getElementById("quiz-step-bubble");

  // DOM Elements - Chat Window
  const chatMessages = document.getElementById("chat-messages");
  const chatInputForm = document.getElementById("chat-input-form");
  const chatUserInput = document.getElementById("chat-user-input");
  const chatCategoryBadge = document.getElementById("chat-category-badge");
  const chatCategoryText = document.getElementById("chat-category-text");
  const btnResetAll = document.getElementById("btn-reset-all");

  // DOM Elements - View Switcher
  const tabChatMode = document.getElementById("tab-chat-mode");
  const tabClassicMode = document.getElementById("tab-classic-mode");
  const chatSection = document.getElementById("chat-section");
  const classicSection = document.getElementById("classic-stepper-section");

  // DOM Elements - Character Modal
  const openCharModalBtn = document.getElementById("open-character-modal-btn");
  const closeCharModalBtn = document.getElementById("close-character-modal-btn");
  const characterModal = document.getElementById("character-modal");

  // DOM Elements - Classic Flow (Secondary View)
  const categoryChips = document.querySelectorAll(".category-chip");
  const searchForm = document.getElementById("perfume-search-form");
  const searchInput = document.getElementById("perfume-search-input");
  const quickPicksContainer = document.getElementById("quick-picks-list");
  const autocompleteDropdown = document.getElementById("autocomplete-dropdown");
  const passportCard = document.getElementById("perfume-passport");
  const step1 = document.getElementById("step-1-container");
  const step2 = document.getElementById("step-2-container");
  const step3 = document.getElementById("step-3-container");
  const stepNav1 = document.getElementById("step-nav-1");
  const stepNav2 = document.getElementById("step-nav-2");
  const stepNav3 = document.getElementById("step-nav-3");
  const questionsList = document.getElementById("questions-list");
  const submitAnswersBtn = document.getElementById("submit-answers-btn");
  const quizProgressBar = document.getElementById("quiz-progress-bar");
  const quizProgressLabel = document.getElementById("quiz-progress-label");
  const quizProgressPercent = document.getElementById("quiz-progress-percent");
  const cotBody = document.getElementById("cot-body");
  const recommendationsGrid = document.getElementById("recommendations-grid");
  const sommelierNoteEl = document.getElementById("sommelier-note-quote");
  const copyBtn = document.getElementById("copy-btn");
  const restartBtn = document.getElementById("restart-btn");
  const filterTabs = document.querySelectorAll(".filter-tab");
  const loadingOverlay = document.getElementById("loading-overlay");
  const loadingSubtext = document.getElementById("loading-subtext");

  // ==========================================
  // Mascot Animation State Machine
  // ==========================================
  /**
   * Sets the mascot animation state across both the HUD avatar and the Character Stage:
   * - "idle": gentle breathing + soft glowing mask star
   * - "thinking": intense white neon pulsation + thinking status
   * - "answering": vocal pulse rhythm + active speaking state
   */
  function setAbooState(state, statusText = null) {
    // 1. Mini Avatar Stage
    if (abooAvatarStage) {
      abooAvatarStage.classList.remove("is-idle", "is-thinking", "is-answering");
      if (state === "thinking") {
        abooAvatarStage.classList.add("is-thinking");
      } else if (state === "answering") {
        abooAvatarStage.classList.add("is-answering");
      } else {
        abooAvatarStage.classList.add("is-idle");
      }
    }

    // 2. Large Character Stage (Left Column)
    if (abooCharacterStage) {
      abooCharacterStage.classList.remove("is-idle", "is-thinking", "is-answering");
      if (state === "thinking") {
        abooCharacterStage.classList.add("is-thinking");
        if (characterStatusLabel) characterStatusLabel.textContent = "АНАЛИЗ ДНК...";
      } else if (state === "answering") {
        abooCharacterStage.classList.add("is-answering");
        if (characterStatusLabel) characterStatusLabel.textContent = "ОТВЕЧАЕТ...";
      } else {
        abooCharacterStage.classList.add("is-idle");
        if (characterStatusLabel) characterStatusLabel.textContent = "ONLINE • ГОТОВ";
      }
    }

    // 3. Status text in HUD
    if (abooStatusText) {
      if (state === "thinking") {
        abooStatusText.textContent = statusText || "Aboo AI анализирует ольфакторный профиль...";
      } else if (state === "answering") {
        abooStatusText.textContent = statusText || "Aboo AI отвечает...";
      } else {
        abooStatusText.textContent = statusText || "Готов к персональной консультации";
      }
    }
  }

  // ==========================================
  // Chat Messaging Utilities
  // ==========================================
  function scrollToBottom() {
    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }

  function addUserMessage(text) {
    const msgDiv = document.createElement("div");
    msgDiv.className = "chat-msg user";
    msgDiv.innerHTML = `
      <div class="chat-user-thumb">✦</div>
      <div class="chat-bubble">${escapeHtml(text)}</div>
    `;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
  }

  function addBotMessage(contentHtml, callback = null, delayMs = 350) {
    setAbooState("answering");

    setTimeout(() => {
      const msgDiv = document.createElement("div");
      msgDiv.className = "chat-msg bot";
      msgDiv.innerHTML = `
        <div class="chat-avatar-thumb"></div>
        <div class="chat-bubble">${contentHtml}</div>
      `;
      chatMessages.appendChild(msgDiv);
      scrollToBottom();

      setTimeout(() => {
        setAbooState("idle");
        if (callback) callback();
      }, 400);
    }, delayMs);
  }

  function updateChatProgress(stepNum, totalSteps = 5) {
    if (!chatProgressBar || !quizStepBubble) return;
    const pct = Math.round((stepNum / totalSteps) * 100);
    chatProgressBar.style.width = `${pct}%`;
    quizStepBubble.textContent = `Интервью ${stepNum} / ${totalSteps}`;
  }

  function updateCategoryDisplay(cat) {
    selectedCategory = cat;
    if (chatCategoryText) chatCategoryText.textContent = cat.toUpperCase();
    categoryChips.forEach(c => {
      const match = (c.getAttribute("data-category") === cat);
      c.classList.toggle("active", match);
      c.setAttribute("aria-checked", match ? "true" : "false");
    });
    updateQuickPicksForCategory(cat);
  }

  // ==========================================
  // Conversational Flow Controller
  // ==========================================
  function bindCategoryChips() {
    if (!chatMessages) return;
    const catBtns = chatMessages.querySelectorAll(".chat-cat-chip");
    catBtns.forEach(btn => {
      btn.onclick = () => {
        const chosenCat = btn.getAttribute("data-cat");
        catBtns.forEach(b => {
          b.classList.remove("active-cat", "selected");
          b.setAttribute("aria-checked", "false");
        });
        btn.classList.add("active-cat", "selected");
        btn.setAttribute("aria-checked", "true");
        handleCategoryChosen(chosenCat);
      };
    });
  }

  function initAbooChat(forceReset = false) {
    if (!chatMessages) return;
    userAnswers = {};
    currentQuestionIndex = 0;
    currentSessionId = null;
    currentPerfume = null;
    currentQuestions = [];
    currentRecommendations = [];
    chatStep = "category";
    isAiBusy = false;
    updateChatProgress(0, 5);
    setAbooState("idle", "Готов к персональной консультации");

    const staticWelcomeTurn = document.getElementById("static-welcome-turn");

    if (!forceReset && staticWelcomeTurn) {
      // Keep static welcome message visible instantly and bind chips
      bindCategoryChips();
      scrollToBottom();
    } else {
      chatMessages.innerHTML = "";
      const welcomeHtml = `
        <div class="welcome-box">
          <div class="welcome-badge">
            <span class="welcome-badge-star">✦</span> ЭКСПЕРТИЗА ABOO PERFUMES
          </div>
          <p class="welcome-title-lead">
            Приветствую. Я — <strong>Aboo AI</strong>, твой персональный парфюмерный сомелье бренда <strong>ABOO PERFUMES</strong>.
          </p>
          <p class="welcome-body-text">
            Я сопоставляю ольфакторную ДНК композиций через <strong>Google Gemini</strong> и базу <strong>Scento API</strong> (более 130 000 флаконов с реальными фото). После короткого экспертного интервью из 5 вопросов я сформирую твой персональный <strong>ТОП-10</strong> с уникальным обоснованием каждого аромата.
          </p>

          <!-- ОПРОС: ШАГ 0 (МУЖСКОЙ / ЖЕНСКИЙ / УНИСЕКС) -->
          <div class="chat-category-poll-wrap" id="chat-category-poll-wrap">
            <div class="poll-prompt-line">
              <span class="poll-star-glow">✦</span>
              <span class="poll-heading-text">ШАГ 0: ВЫБЕРИТЕ КАТЕГОРИЮ ДЛЯ ПОДБОРА</span>
            </div>
            
            <div class="chat-category-chips" id="initial-category-selector" role="radiogroup" aria-label="Опрос: Категория аромата">
              <button type="button" class="chat-cat-chip ${selectedCategory === 'Мужской' ? 'active-cat selected' : ''}" data-cat="Мужской" role="radio" aria-checked="${selectedCategory === 'Мужской'}">
                <span class="cat-symbol">♂</span>
                <span class="cat-title">МУЖСКОЙ</span>
                <span class="cat-sub">Статус, кожа, дерево и фужер</span>
              </button>
              <button type="button" class="chat-cat-chip ${selectedCategory === 'Женский' ? 'active-cat selected' : ''}" data-cat="Женский" role="radio" aria-checked="${selectedCategory === 'Женский'}">
                <span class="cat-symbol">♀</span>
                <span class="cat-title">ЖЕНСКИЙ</span>
                <span class="cat-sub">Чувственные цветы и гурманика</span>
              </button>
              <button type="button" class="chat-cat-chip ${selectedCategory === 'Унисекс' ? 'active-cat selected' : ''}" data-cat="Унисекс" role="radio" aria-checked="${selectedCategory === 'Унисекс'}">
                <span class="cat-symbol">⚥</span>
                <span class="cat-title">УНИСЕКС</span>
                <span class="cat-sub">Ниша, минералы и современный код</span>
              </button>
            </div>
            <div class="poll-action-hint">
              <span>Нажмите на нужную категорию выше, чтобы перейти к вводу любимого парфюма.</span>
            </div>
          </div>
        </div>
      `;

      addBotMessage(welcomeHtml, () => {
        bindCategoryChips();
      }, 100);
    }
  }

  function handleCategoryChosen(cat) {
    if (chatStep !== "category") return;
    updateCategoryDisplay(cat);
    addUserMessage(`Выбрана категория: ${cat}`);
    chatStep = "perfume";

    setAbooState("thinking", "Aboo AI фиксирует категорию...");

    const picks = getQuickPickListForCategory(cat);
    const quickPickTagsHtml = picks.map(p => `
      <button type="button" class="chat-quick-tag" data-perfume="${p.name}">
        ${p.icon} ${p.name}
      </button>
    `).join("");

    const askPerfumeHtml = `
      <div>
        <p style="margin: 0 0 10px 0;">
          Зафиксировал: категория <strong>«${cat}»</strong>.
        </p>
        <p style="margin: 0 0 12px 0;">
          <strong>Шаг 1:</strong> Назови свой прошлый любимый парфюм, который покорил твое сердце больше всего (или выбери один из эталонов ниже):
        </p>
        <div class="chat-quick-picks">
          ${quickPickTagsHtml}
        </div>
      </div>
    `;

    addBotMessage(askPerfumeHtml, () => {
      // Attach click events on quick-pick tags
      const quickTags = chatMessages.querySelectorAll(".chat-quick-tag");
      quickTags.forEach(tag => {
        tag.addEventListener("click", () => {
          const perfumeName = tag.getAttribute("data-perfume");
          handlePerfumeSubmitted(perfumeName);
        });
      });
      if (chatUserInput) chatUserInput.focus();
    }, 450);
  }

  async function handlePerfumeSubmitted(perfumeName) {
    if (!perfumeName || perfumeName.trim().length < 2 || isAiBusy) return;
    isAiBusy = true;
    addUserMessage(perfumeName.trim());

    if (chatUserInput) chatUserInput.value = "";
    setAbooState("thinking", `Aboo AI анализирует ДНК «${perfumeName}» через Gemini & Scento...`);

    try {
      const resp = await fetch("/api/sommelier/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          perfume_name: perfumeName.trim(),
          category: selectedCategory
        })
      });

      if (!resp.ok) {
        throw new Error(`Ошибка сервера: ${resp.status}`);
      }

      const data = await resp.json();
      currentSessionId = data.session_id;
      currentPerfume = data.matched_perfume;
      currentQuestions = data.questions || [];
      currentQuestionIndex = 0;
      userAnswers = {};

      const matchedName = `${currentPerfume.brand} ${currentPerfume.name}`;
      const notesPreview = (currentPerfume.all_notes || currentPerfume.notes || []).slice(0, 4).join(", ");
      const bottleImg = currentPerfume.image_url || `/api/perfumes/${currentPerfume.id}/badge.svg`;

      const matchFeedbackHtml = `
        <div>
          <p style="margin: 0 0 8px 0;">
            Отличный выбор! Я нашел этот аромат в официальной базе:
          </p>
          <div class="chat-passport-card">
            <div class="chat-passport-bottle">
              <img src="${bottleImg}" alt="${matchedName}" onerror="this.src='/static/images/pwa-icon.svg'" />
            </div>
            <div class="chat-passport-details">
              <div class="chat-passport-brand">${currentPerfume.brand}</div>
              <div class="chat-passport-name">${currentPerfume.name}</div>
              <div class="chat-passport-family">${currentPerfume.family}</div>
              <div style="font-size: 11.5px; color: #a8a8a8; line-height: 1.4;">
                ${currentPerfume.character || `Ключевые ноты: ${notesPreview}`}
              </div>
            </div>
          </div>
          <p style="margin: 12px 0 0 0; color: #e0e0e0;">
            Анализ ДНК завершен. Чтобы найти преемника без шаблонных клише, я задам тебе <strong>строго 5 точных вопросов</strong>.
          </p>
        </div>
      `;

      addBotMessage(matchFeedbackHtml, () => {
        chatStep = "interview";
        isAiBusy = false;
        deliverCurrentQuestion();
      }, 500);

    } catch (err) {
      console.error("Error starting sommelier session:", err);
      isAiBusy = false;
      setAbooState("idle");
      addBotMessage(`
        <div>
          <p style="color: #ff8585; margin: 0 0 6px 0;">Не удалось найти данный аромат.</p>
          <p style="margin: 0;">Попробуй указать бренд и название точнее (например, <em>Tom Ford Lost Cherry</em> или <em>Ganymede</em>).</p>
        </div>
      `, null, 200);
    }
  }

  function deliverCurrentQuestion() {
    if (currentQuestionIndex >= currentQuestions.length) {
      finishInterviewAndGenerateRecommendations();
      return;
    }

    const q = currentQuestions[currentQuestionIndex];
    const qNum = currentQuestionIndex + 1;
    updateChatProgress(qNum, 5);

    const aspectLabels = {
      lifestyle: "КОНТЕКСТ И СТИЛЬ ЖИЗНИ",
      sillage: "ШЛЕЙФ И ИНТИМНОСТЬ",
      temperature_notes: "ТЕМПЕРАТУРА И ПЛОТНОСТЬ НОТ",
      antipathies: "ПАРФЮМЕРНЫЕ АНТИПАТИИ (ТАБУ)",
      boldness: "СТЕПЕНЬ СМЕЛОСТИ"
    };

    const aspectName = aspectLabels[q.aspect] || "КАЛИБРОВКА ПРЕДПОЧТЕНИЙ";
    const optionsHtml = (q.options || []).map(opt => `
      <button type="button" class="chat-option-btn" data-qid="${q.id}" data-answer="${escapeHtml(opt)}">
        ${escapeHtml(opt)}
      </button>
    `).join("");

    const questionHtml = `
      <div class="chat-interactive-box">
        <div class="chat-criterion-badge">✦ ВОПРОС ${qNum} ИЗ 5 • ${aspectName}</div>
        <div class="chat-question-text">${q.question}</div>
        <div class="chat-options-grid">
          ${optionsHtml}
        </div>
      </div>
    `;

    addBotMessage(questionHtml, () => {
      const optBtns = chatMessages.querySelectorAll(`.chat-option-btn[data-qid="${q.id}"]`);
      optBtns.forEach(btn => {
        btn.addEventListener("click", () => {
          const ans = btn.getAttribute("data-answer");
          handleAnswerSubmitted(q.id, ans);
        });
      });
      if (chatUserInput) chatUserInput.focus();
    }, 400);
  }

  function handleAnswerSubmitted(questionId, answerText) {
    if (!answerText || isAiBusy) return;
    isAiBusy = true;

    // Highlight chosen button
    const chosenBtn = chatMessages.querySelector(`.chat-option-btn[data-qid="${questionId}"][data-answer="${CSS.escape(answerText)}"]`);
    if (chosenBtn) chosenBtn.classList.add("selected");

    addUserMessage(answerText);
    userAnswers[questionId] = answerText;
    currentQuestionIndex++;

    setAbooState("thinking", `Aboo AI зафиксировал ответ (${currentQuestionIndex}/5)...`);

    setTimeout(() => {
      isAiBusy = false;
      if (currentQuestionIndex < currentQuestions.length) {
        deliverCurrentQuestion();
      } else {
        finishInterviewAndGenerateRecommendations();
      }
    }, 450);
  }

  async function finishInterviewAndGenerateRecommendations() {
    if (isAiBusy) return;
    isAiBusy = true;

    updateChatProgress(5, 5);
    setAbooState("thinking", "Aboo AI активирует режим Chain-of-Thought и опрашивает Scento API...");

    const thinkingMsgHtml = `
      <div>
        <p style="margin: 0 0 6px 0;">Все 5 ответов приняты.</p>
        <p style="margin: 0; color: #a0a0a0;">
          Активирую режим <strong>Chain-of-Thought</strong>: сопоставляю психотип, фильтрую табу-ноты и отбираю ранжированный ТОП-10 из базы Scento...
        </p>
      </div>
    `;
    addBotMessage(thinkingMsgHtml, null, 200);

    // Prepare payload
    const answersPayload = Object.keys(userAnswers).map(qid => ({
      question_id: parseInt(qid, 10),
      answer: userAnswers[qid]
    }));

    try {
      const resp = await fetch("/api/sommelier/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: currentSessionId,
          category: selectedCategory,
          answers: answersPayload
        })
      });

      if (!resp.ok) {
        throw new Error(`Ошибка генерации: ${resp.status}`);
      }

      const recData = await resp.json();
      currentRecommendations = recData.recommendations || [];
      currentChainOfThought = recData.chain_of_thought;

      renderChatFinalRecommendations(recData);
      chatStep = "results";
      isAiBusy = false;
      setAbooState("idle", "Консультация завершена • ТОП-10 сформирован");

      // Also sync with classic view
      syncClassicViewWithResults(recData);

    } catch (err) {
      console.error("Error generating recommendations:", err);
      isAiBusy = false;
      setAbooState("idle");
      addBotMessage(`
        <div style="color: #ff8585;">
          Произошла ошибка при обращении к Gemini или Scento API. Пожалуйста, попробуйте нажать «Сброс» и начать заново.
        </div>
      `, null, 300);
    }
  }

  function renderChatFinalRecommendations(recData) {
    const cotText = recData.chain_of_thought || "Анализ психотипа и ольфакторного профиля успешно завершен.";
    const sommelierNote = recData.sommelier_note || "Опираясь на твой вкус, я составил персональный ТОП-10 реальных ароматов.";

    // Render Chain-of-Thought block
    const cotHtml = `
      <div class="chat-cot-card">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
          <span style="color: #ffffff; filter: drop-shadow(0 0 6px #ffffff);">✦</span>
          <span style="font-family: var(--font-brand); font-size: 10px; font-weight: 700; letter-spacing: 0.18em; color: #ffffff;">
            РАССУЖДЕНИЯ ГЛАВНОГО СОМЕЛЬЕ ABOO AI (CHAIN-OF-THOUGHT)
          </span>
        </div>
        <div style="font-size: 13px; color: #d0d0d0; line-height: 1.6; white-space: pre-line;">
          ${escapeHtml(cotText)}
        </div>
      </div>
    `;

    // Render Cards
    const recs = recData.recommendations || [];
    const cardsHtml = recs.map(item => {
      let badgeClass = "niche";
      let badgeLabel = "СМЕЛАЯ НИША";
      if (item.rank <= 3) {
        badgeClass = "hit";
        badgeLabel = "ТОЧНОЕ ПОПАДАНИЕ";
      } else if (item.rank <= 7) {
        badgeClass = "variation";
        badgeLabel = "ВАРИАЦИЯ";
      }

      const img = item.image_url || `/api/perfumes/${item.id || "flacon"}/badge.svg`;
      const notesStr = Array.isArray(item.notes) ? item.notes.join(", ") : (item.notes || "");

      return `
        <div class="chat-rec-item" data-rank="${item.rank}">
          <div class="chat-rec-bottle">
            <img src="${img}" alt="${item.brand} ${item.name}" onerror="this.src='/static/images/pwa-icon.svg'" />
          </div>
          <div class="chat-rec-body">
            <div class="chat-rec-rank-row">
              <span class="chat-rank-num">#${item.rank}</span>
              <span class="chat-rank-badge ${badgeClass}">${badgeLabel}</span>
            </div>
            <div class="chat-rec-name">${escapeHtml(item.name)}</div>
            <div class="chat-rec-brand">${escapeHtml(item.brand)} • ${escapeHtml(item.family)}</div>
            <div style="font-size: 11.5px; color: #9e9e9e; margin-bottom: 6px;">Ноты: ${escapeHtml(notesStr)}</div>
            <div class="chat-rec-reason">${escapeHtml(item.reason)}</div>
          </div>
        </div>
      `;
    }).join("");

    const finalHtml = `
      <div>
        <p style="font-size: 15px; font-weight: 600; color: #ffffff; margin: 0 0 8px 0;">
          Готово! Твой персональный ТОП-10 реальных ароматов:
        </p>
        <p style="font-style: italic; color: #b8b8b8; margin: 0 0 14px 0; border-left: 2px solid #ffffff; padding-left: 10px;">
          ${escapeHtml(sommelierNote)}
        </p>
        ${cotHtml}
        <div class="chat-recommendations-box">
          ${cardsHtml}
        </div>
        <div style="margin-top: 20px; text-align: center;">
          <button type="button" class="btn-secondary" id="chat-restart-btn" style="padding: 10px 20px;">
            ↻ Провести новую консультацию
          </button>
        </div>
      </div>
    `;

    addBotMessage(finalHtml, () => {
      const rBtn = document.getElementById("chat-restart-btn");
      if (rBtn) {
        rBtn.addEventListener("click", () => {
          initAbooChat();
        });
      }
    }, 600);
  }

  // Handle Input Bar Submission in Chat
  if (chatInputForm) {
    chatInputForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (!chatUserInput) return;
      const text = chatUserInput.value.trim();
      if (!text || isAiBusy) return;

      if (chatStep === "category") {
        // Match category word
        const lower = text.toLowerCase();
        if (lower.includes("муж")) handleCategoryChosen("Мужской");
        else if (lower.includes("жен")) handleCategoryChosen("Женский");
        else handleCategoryChosen("Унисекс");
      } else if (chatStep === "perfume") {
        handlePerfumeSubmitted(text);
      } else if (chatStep === "interview") {
        const q = currentQuestions[currentQuestionIndex];
        if (q) handleAnswerSubmitted(q.id, text);
      } else {
        // General query or restart
        addUserMessage(text);
        addBotMessage("Консультация завершена. Чтобы начать новый подбор, нажми «↻ Новый диалог» вверху.", null, 250);
      }
    });
  }

  // Category Badge Click in Input Dock toggles category
  if (chatCategoryBadge) {
    chatCategoryBadge.addEventListener("click", () => {
      const cats = ["Унисекс", "Мужской", "Женский"];
      const nextIdx = (cats.indexOf(selectedCategory) + 1) % cats.length;
      updateCategoryDisplay(cats[nextIdx]);
    });
  }

  // Reset All Button
  if (btnResetAll) {
    btnResetAll.addEventListener("click", () => {
      initAbooChat(true);
    });
  }

  // ==========================================
  // Dual View Tab Switching
  // ==========================================
  if (tabChatMode && tabClassicMode) {
    tabChatMode.addEventListener("click", () => {
      tabChatMode.classList.add("active");
      tabChatMode.setAttribute("aria-selected", "true");
      tabClassicMode.classList.remove("active");
      tabClassicMode.setAttribute("aria-selected", "false");
      chatSection.style.display = "block";
      classicSection.style.display = "none";
    });

    tabClassicMode.addEventListener("click", () => {
      tabClassicMode.classList.add("active");
      tabClassicMode.setAttribute("aria-selected", "true");
      tabChatMode.classList.remove("active");
      tabChatMode.setAttribute("aria-selected", "false");
      chatSection.style.display = "none";
      classicSection.style.display = "block";
    });
  }

  // ==========================================
  // Character Showcase Modal
  // ==========================================
  if (openCharModalBtn && characterModal) {
    openCharModalBtn.addEventListener("click", () => {
      characterModal.classList.add("active");
      characterModal.setAttribute("aria-hidden", "false");
    });
  }

  if (closeCharModalBtn && characterModal) {
    closeCharModalBtn.addEventListener("click", () => {
      characterModal.classList.remove("active");
      characterModal.setAttribute("aria-hidden", "true");
    });
  }

  if (characterModal) {
    characterModal.addEventListener("click", (e) => {
      if (e.target === characterModal) {
        characterModal.classList.remove("active");
        characterModal.setAttribute("aria-hidden", "true");
      }
    });
  }

  // ==========================================
  // Quick Picks Data & Helpers
  // ==========================================
  function getQuickPickListForCategory(cat) {
    if (cat === "Мужской") {
      return [
        { icon: "👑", name: "Creed Aventus" },
        { icon: "🪐", name: "Marc-Antoine Barrois Ganymede" },
        { icon: "🌲", name: "Essential Parfums Bois Impérial" },
        { icon: "🌊", name: "Chanel Bleu de Chanel" },
        { icon: "🏛️", name: "Hermes Terre d'Hermes" },
        { icon: "🥃", name: "Kilian Angels' Share" }
      ];
    } else if (cat === "Женский") {
      return [
        { icon: "🍒", name: "Tom Ford Lost Cherry" },
        { icon: "🌸", name: "Ex Nihilo Fleur Narcotique" },
        { icon: "💎", name: "Baccarat Rouge 540" },
        { icon: "🌹", name: "Parfums de Marly Delina" },
        { icon: "☀️", name: "Byredo Bal d'Afrique" },
        { icon: "🍑", name: "Tom Ford Bitter Peach" }
      ];
    } else {
      return [
        { icon: "🍒", name: "Tom Ford Lost Cherry" },
        { icon: "💎", name: "Baccarat Rouge 540" },
        { icon: "🪐", name: "Marc-Antoine Barrois Ganymede" },
        { icon: "🥃", name: "Kilian Angels' Share" },
        { icon: "👑", name: "Creed Aventus" },
        { icon: "🌸", name: "Ex Nihilo Fleur Narcotique" }
      ];
    }
  }

  function updateQuickPicksForCategory(cat) {
    if (!quickPicksContainer) return;
    const picks = getQuickPickListForCategory(cat);
    quickPicksContainer.innerHTML = picks.map(p => `
      <button type="button" class="quick-pick-chip" data-perfume="${p.name}">
        ${p.icon} ${p.name}
      </button>
    `).join("");

    quickPicksContainer.querySelectorAll(".quick-pick-chip").forEach(btn => {
      btn.addEventListener("click", () => {
        const pName = btn.getAttribute("data-perfume");
        if (searchInput) searchInput.value = pName;
        selectPerfumeAndStart(pName);
      });
    });
  }

  // ==========================================
  // Classic Stepper Flow Implementation
  // ==========================================
  categoryChips.forEach(chip => {
    chip.addEventListener("click", () => {
      const cat = chip.getAttribute("data-category") || "Унисекс";
      updateCategoryDisplay(cat);
      if (searchInput && searchInput.value.trim().length >= 2) {
        triggerSearch(searchInput.value.trim());
      }
    });
  });

  if (searchForm) {
    searchForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (!searchInput) return;
      const q = searchInput.value.trim();
      if (q) selectPerfumeAndStart(q);
    });
  }

  if (searchInput) {
    let debounceTimer = null;
    searchInput.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      const q = searchInput.value.trim();
      if (q.length < 2) {
        if (autocompleteDropdown) autocompleteDropdown.style.display = "none";
        return;
      }
      debounceTimer = setTimeout(() => triggerSearch(q), 250);
    });
  }

  async function triggerSearch(query) {
    if (!autocompleteDropdown) return;
    try {
      const catParam = encodeURIComponent(selectedCategory);
      const resp = await fetch(`/api/perfumes/search?q=${encodeURIComponent(query)}&limit=6&category=${catParam}`);
      if (!resp.ok) return;
      const data = await resp.json();
      renderAutocomplete(data.results || []);
    } catch (err) {
      console.warn("Search error:", err);
    }
  }

  function renderAutocomplete(results) {
    if (!autocompleteDropdown) return;
    if (results.length === 0) {
      autocompleteDropdown.style.display = "none";
      return;
    }

    autocompleteDropdown.innerHTML = results.map(item => `
      <div class="autocomplete-item" data-perfume="${escapeHtml(item.perfume.brand + ' ' + item.perfume.name)}">
        <span class="item-name">${escapeHtml(item.perfume.brand)} — ${escapeHtml(item.perfume.name)}</span>
        <span class="item-family">${escapeHtml(item.perfume.family)}</span>
      </div>
    `).join("");

    autocompleteDropdown.style.display = "block";

    autocompleteDropdown.querySelectorAll(".autocomplete-item").forEach(el => {
      el.addEventListener("click", () => {
        const pName = el.getAttribute("data-perfume");
        if (searchInput) searchInput.value = pName;
        autocompleteDropdown.style.display = "none";
        selectPerfumeAndStart(pName);
      });
    });
  }

  async function selectPerfumeAndStart(perfumeName) {
    if (!perfumeName) return;
    showLoading("ИИ-Сомелье анализирует формулу аромата...");
    setAbooState("thinking", `Анализ ДНК «${perfumeName}»...`);

    try {
      const resp = await fetch("/api/sommelier/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          perfume_name: perfumeName,
          category: selectedCategory
        })
      });

      if (!resp.ok) throw new Error("Ошибка сервера");
      const data = await resp.json();

      currentSessionId = data.session_id;
      currentPerfume = data.matched_perfume;
      currentQuestions = data.questions || [];

      // Render Classic Step 2
      renderClassicQuestions(currentQuestions);

      if (step1) step1.style.display = "none";
      if (step2) step2.style.display = "block";
      if (stepNav1) stepNav1.classList.remove("active");
      if (stepNav2) stepNav2.classList.add("active");

      hideLoading();
      setAbooState("idle");

    } catch (err) {
      hideLoading();
      setAbooState("idle");
      alert("Не удалось загрузить данные парфюма: " + err.message);
    }
  }

  function renderClassicQuestions(questions) {
    if (!questionsList) return;
    questionsList.innerHTML = questions.map((q, idx) => {
      const optionsHtml = (q.options || []).map(opt => `
        <button type="button" class="option-btn" data-qid="${q.id}" data-opt="${escapeHtml(opt)}">
          ${escapeHtml(opt)}
        </button>
      `).join("");

      return `
        <div class="question-card" data-qid="${q.id}">
          <div class="question-header">
            <span class="question-badge">ВОПРОС ${idx + 1} ИЗ 5</span>
            <span class="question-aspect">${q.aspect}</span>
          </div>
          <h4 class="question-title">${q.question}</h4>
          <div class="options-grid">
            ${optionsHtml}
          </div>
          <input type="text" class="custom-answer-input" placeholder="Или напишите свой ответ..." data-qid="${q.id}" />
        </div>
      `;
    }).join("");

    // Attach click events on classic options
    questionsList.querySelectorAll(".option-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const qid = btn.getAttribute("data-qid");
        const val = btn.getAttribute("data-opt");
        questionsList.querySelectorAll(`.option-btn[data-qid="${qid}"]`).forEach(b => b.classList.remove("selected"));
        btn.classList.add("selected");
        userAnswers[qid] = val;
        updateClassicQuizProgress();
      });
    });

    questionsList.querySelectorAll(".custom-answer-input").forEach(inp => {
      inp.addEventListener("input", () => {
        const qid = inp.getAttribute("data-qid");
        if (inp.value.trim().length > 0) {
          questionsList.querySelectorAll(`.option-btn[data-qid="${qid}"]`).forEach(b => b.classList.remove("selected"));
          userAnswers[qid] = inp.value.trim();
        }
        updateClassicQuizProgress();
      });
    });

    updateClassicQuizProgress();
  }

  function updateClassicQuizProgress() {
    const answeredCount = Object.keys(userAnswers).length;
    const total = 5;
    const pct = Math.round((answeredCount / total) * 100);

    if (quizProgressBar) quizProgressBar.style.width = `${pct}%`;
    if (quizProgressLabel) quizProgressLabel.textContent = `Отвечено ${answeredCount} из ${total}`;
    if (quizProgressPercent) quizProgressPercent.textContent = `${pct}%`;

    if (submitAnswersBtn) {
      submitAnswersBtn.disabled = (answeredCount < total);
    }
  }

  if (submitAnswersBtn) {
    submitAnswersBtn.addEventListener("click", async () => {
      showLoading("Aboo AI формирует персональный ТОП-10 через Chain-of-Thought...");
      setAbooState("thinking", "Анализируем формулы через Gemini и Scento...");

      const answersPayload = Object.keys(userAnswers).map(qid => ({
        question_id: parseInt(qid, 10),
        answer: userAnswers[qid]
      }));

      try {
        const resp = await fetch("/api/sommelier/recommend", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: currentSessionId,
            category: selectedCategory,
            answers: answersPayload
          })
        });

        if (!resp.ok) throw new Error("Ошибка формирования ТОП-10");
        const data = await resp.json();

        syncClassicViewWithResults(data);

        if (step2) step2.style.display = "none";
        if (step3) step3.style.display = "block";
        if (stepNav2) stepNav2.classList.remove("active");
        if (stepNav3) stepNav3.classList.add("active");

        hideLoading();
        setAbooState("idle");

      } catch (err) {
        hideLoading();
        setAbooState("idle");
        alert("Ошибка: " + err.message);
      }
    });
  }

  function syncClassicViewWithResults(data) {
    currentRecommendations = data.recommendations || [];

    // Render Chain of Thought
    if (cotBody && data.chain_of_thought) {
      const steps = data.chain_of_thought.split("✦").filter(s => s.trim().length > 0);
      cotBody.innerHTML = steps.map(s => {
        const parts = s.split(":");
        const tag = parts[0].trim();
        const bodyText = parts.slice(1).join(":").trim();
        return `
          <div class="cot-step-card">
            <div class="cot-step-header">
              <span class="cot-step-tag">✦ ${escapeHtml(tag)}</span>
            </div>
            <div class="cot-step-text">${escapeHtml(bodyText || tag)}</div>
          </div>
        `;
      }).join("");
    }

    if (sommelierNoteEl) {
      sommelierNoteEl.textContent = data.sommelier_note || "";
    }

    renderClassicRecommendationsGrid(currentRecommendations);
  }

  function renderClassicRecommendationsGrid(recs) {
    if (!recommendationsGrid) return;
    recommendationsGrid.innerHTML = recs.map(item => {
      let badgeClass = "niche";
      let badgeLabel = "СМЕЛАЯ НИША (8-10)";
      if (item.rank <= 3) {
        badgeClass = "hit";
        badgeLabel = "ТОЧНОЕ ПОПАДАНИЕ (1-3)";
      } else if (item.rank <= 7) {
        badgeClass = "variation";
        badgeLabel = "ВАРИАЦИЯ (4-7)";
      }

      const img = item.image_url || `/api/perfumes/${item.id || "flacon"}/badge.svg`;
      const notes = Array.isArray(item.notes) ? item.notes.join(", ") : item.notes;

      return `
        <div class="rec-card" data-rank="${item.rank}">
          <div class="rec-card-bottle">
            <img src="${img}" alt="${item.brand} ${item.name}" onerror="this.src='/static/images/pwa-icon.svg'" />
          </div>
          <div class="rec-card-info">
            <div class="rec-rank-row">
              <span class="rec-rank-num">#${item.rank}</span>
              <span class="rec-badge ${badgeClass}">${badgeLabel}</span>
            </div>
            <div class="rec-name">${escapeHtml(item.name)}</div>
            <div class="rec-brand">${escapeHtml(item.brand)} • ${escapeHtml(item.family)}</div>
            <div class="rec-notes">Ноты: ${escapeHtml(notes)}</div>
            <div class="rec-reason">${escapeHtml(item.reason)}</div>
          </div>
        </div>
      `;
    }).join("");
  }

  // Filter Tabs in Classic View
  filterTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      filterTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const f = tab.getAttribute("data-filter");
      filterClassicCards(f);
    });
  });

  function filterClassicCards(filter) {
    const cards = document.querySelectorAll(".rec-card");
    cards.forEach(card => {
      const r = parseInt(card.getAttribute("data-rank"), 10);
      if (filter === "hits") {
        card.style.display = (r <= 3) ? "flex" : "none";
      } else if (filter === "variations") {
        card.style.display = (r >= 4 && r <= 7) ? "flex" : "none";
      } else if (filter === "bold") {
        card.style.display = (r >= 8) ? "flex" : "none";
      } else {
        card.style.display = "flex";
      }
    });
  }

  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      if (currentRecommendations.length === 0) return;
      const text = currentRecommendations.map(r => `#${r.rank} ${r.brand} - ${r.name} (${r.family})\nОбоснование: ${r.reason}\n`).join("\n");
      navigator.clipboard.writeText(text).then(() => {
        copyBtn.textContent = "✓ Скопировано!";
        setTimeout(() => copyBtn.textContent = "📋 Скопировать список", 2000);
      });
    });
  }

  if (restartBtn) {
    restartBtn.addEventListener("click", () => {
      if (step3) step3.style.display = "none";
      if (step2) step2.style.display = "none";
      if (step1) step1.style.display = "block";
      if (stepNav3) stepNav3.classList.remove("active");
      if (stepNav2) stepNav2.classList.remove("active");
      if (stepNav1) stepNav1.classList.add("active");
      if (searchInput) searchInput.value = "";
      initAbooChat(true);
    });
  }

  function showLoading(subtext = null) {
    if (loadingOverlay) {
      if (loadingSubtext && subtext) loadingSubtext.textContent = subtext;
      loadingOverlay.classList.add("active");
    }
  }

  function hideLoading() {
    if (loadingOverlay) loadingOverlay.classList.remove("active");
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // ==========================================
  // Initialization
  // ==========================================
  updateQuickPicksForCategory(selectedCategory);
  initAbooChat();
});
