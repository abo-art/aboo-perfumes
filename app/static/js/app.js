/**
 * ABOO PERFUMES — Aboo AI Perfume Sommelier Frontend
 * Classic Stepper Flow (Step 1 -> Step 2 -> Step 3)
 * with Interactive Floating Bottom-Left Aboo AI Chat in Step 3.
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
  let currentRecommendations = [];
  let currentChainOfThought = null;
  let isChatOpen = false;
  let chatInitialized = false;
  let isChatAiBusy = false;

  // DOM Elements - Stepper Navigation & Steps
  const stepNav1 = document.getElementById("step-nav-1");
  const stepNav2 = document.getElementById("step-nav-2");
  const stepNav3 = document.getElementById("step-nav-3");
  const step1 = document.getElementById("step-1-container");
  const step2 = document.getElementById("step-2-container");
  const step3 = document.getElementById("step-3-container");

  // DOM Elements - Step 1: Category, Search & Passport
  const categoryChips = document.querySelectorAll("#category-selector-step1 .category-chip");
  const searchInput = document.getElementById("perfume-search-input");
  const startSommelierBtn = document.getElementById("start-sommelier-btn");
  const autocompleteDropdown = document.getElementById("autocomplete-dropdown");
  const quickPicks = document.querySelectorAll("#quick-picks-list .quick-pick-chip");
  const passportCard = document.getElementById("perfume-passport");
  const passportBrand = document.getElementById("passport-brand");
  const passportName = document.getElementById("passport-name");
  const passportFamily = document.getElementById("passport-family");
  const passportCharacter = document.getElementById("passport-character");
  const passportTop = document.getElementById("passport-top");
  const passportHeart = document.getElementById("passport-heart");
  const passportBase = document.getElementById("passport-base");
  const passportBottleImg = document.getElementById("passport-bottle-img");
  const confirmPassportBtn = document.getElementById("confirm-passport-btn");

  // DOM Elements - Step 2: 5 Questions
  const sommelierIntroTitle = document.getElementById("sommelier-intro-title");
  const sommelierIntroText = document.getElementById("sommelier-intro-text");
  const questionsList = document.getElementById("questions-list");
  const quizProgressBar = document.getElementById("quiz-progress-bar");
  const quizProgressLabel = document.getElementById("quiz-progress-label");
  const quizProgressPercent = document.getElementById("quiz-progress-percent");
  const submitAnswersBtn = document.getElementById("submit-answers-btn");

  // DOM Elements - Step 3: Recommendations & Chain-of-Thought
  const cotBody = document.getElementById("cot-body");
  const sommelierNoteEl = document.getElementById("sommelier-note-quote");
  const filterTabs = document.querySelectorAll(".filter-tab");
  const recommendationsGrid = document.getElementById("recommendations-grid");
  const copyBtn = document.getElementById("copy-btn");
  const restartBtn = document.getElementById("restart-btn");

  // DOM Elements - Step 3 Floating Bottom-Left Aboo AI Chat
  const floatingAbooContainer = document.getElementById("floating-aboo-container");
  const floatingAbooTrigger = document.getElementById("floating-aboo-trigger");
  const floatingChatWindow = document.getElementById("floating-chat-window");
  const floatingChatCloseBtn = document.getElementById("floating-chat-close-btn");
  const floatingQuickChips = document.querySelectorAll(".floating-quick-chip");
  const floatingChatMessages = document.getElementById("floating-chat-messages");
  const floatingChatForm = document.getElementById("floating-chat-form");
  const floatingChatInput = document.getElementById("floating-chat-input");

  // DOM Elements - Modals & Overlays
  const openCharModalBtn = document.getElementById("open-character-modal-btn");
  const closeCharModalBtn = document.getElementById("close-character-modal-btn");
  const characterModal = document.getElementById("character-modal");
  const loadingOverlay = document.getElementById("loading-overlay");
  const loadingSubtext = document.getElementById("loading-subtext");

  // Aspect dictionary mapping technical keys to elegant Russian labels
  const aspectTitles = {
    lifestyle: "Контекст и стиль жизни",
    sillage: "Шлейф и интимность",
    temperature_notes: "Температура и плотность",
    antipathies: "Ольфакторные табу",
    boldness: "Ольфакторная смелость"
  };

  // Client-side Note & Accord Translations for Flawless Russian Presentation
  const NOTE_RU_MAP = {
    "cognac": "Коньяк",
    "cinnamon": "Корица",
    "tonka bean": "Бобы тонка",
    "oak": "Дуб",
    "hedione": "Гедион",
    "candied almond": "Засахаренный миндаль",
    "bitter almond": "Горький миндаль",
    "almond": "Миндаль",
    "vanilla": "Ваниль",
    "praline": "Пралине",
    "sandalwood": "Сандал",
    "bergamot": "Бергамот",
    "lemon": "Лимон",
    "orange": "Апельсин",
    "mandarin": "Мандарин",
    "mandarin orange": "Мандарин",
    "grapefruit": "Грейпфрут",
    "lime": "Лайм",
    "orange blossom": "Флердоранж",
    "neroli": "Нероли",
    "jasmine": "Жасмин",
    "jasmine sambac": "Жасмин самбак",
    "rose": "Роза",
    "turkish rose": "Турецкая роза",
    "damask rose": "Дамасская роза",
    "lavender": "Лаванда",
    "cardamom": "Кардамон",
    "pink pepper": "Розовый перец",
    "black pepper": "Черный перец",
    "pepper": "Перец",
    "nutmeg": "Мускатный орех",
    "cloves": "Гвоздика",
    "star anise": "Анис",
    "anise": "Анис",
    "coriander": "Кориандр",
    "ginger": "Имбирь",
    "mint": "Мята",
    "cedar": "Кедр",
    "cedarwood": "Кедр",
    "vetiver": "Ветивер",
    "musk": "Мускус",
    "white musk": "Белый мускус",
    "amber": "Амбра",
    "ambergris": "Серая амбра",
    "ambroxan": "Амброксан",
    "iso e super": "Изо Е Супер",
    "akigalawood": "Акигалавуд",
    "cashmeran": "Кашмеран",
    "patchouli": "Пачули",
    "iris": "Ирис",
    "orris": "Корень ириса",
    "tobacco": "Табак",
    "leather": "Кожа",
    "suede": "Замша",
    "oud": "Уд",
    "agarwood": "Агаровое дерево",
    "saffron": "Шафран",
    "incense": "Ладан",
    "myrrh": "Мирра",
    "labdanum": "Лабданум",
    "benzoin": "Бензоин",
    "olibanum": "Олибанум",
    "elemi": "Элеми",
    "guaiac wood": "Гваяк",
    "coffee": "Кофе",
    "chocolate": "Шоколад",
    "honey": "Мёд",
    "caramel": "Карамель",
    "peach": "Персик",
    "cherry": "Вишня",
    "black cherry": "Черная вишня",
    "plum": "Слива",
    "apple": "Яблоко",
    "pear": "Груша",
    "black currant": "Черная смородина",
    "raspberry": "Малина",
    "blackberry": "Ежевика",
    "fig": "Инжир",
    "coconut": "Кокос",
    "sea salt": "Морская соль",
    "sea notes": "Морские ноты",
    "mineral notes": "Минеральные ноты",
    "rum": "Ром",
    "whiskey": "Виски",
    "liquor": "Ликёр",
    "cacao": "Какао",
    "violet": "Фиалка",
    "tuberose": "Тубероза",
    "ylang-ylang": "Иланг-иланг",
    "cypress": "Кипарис",
    "pine": "Сосна",
    "fir": "Пихта",
    "birch": "Береза",
    "smoke": "Дым",
    "moss": "Мох",
    "oakmoss": "Дубовый мох"
  };

  function translateNote(n) {
    if (!n) return "";
    const key = String(n).trim().toLowerCase();
    return NOTE_RU_MAP[key] || n;
  }

  function formatCharacterRu(text) {
    if (!text) return "";
    let clean = text;
    const replacements = {
      "woody": "древесные",
      "warm-spicy": "теплые пряные",
      "warm spicy": "теплые пряные",
      "sweet": "сладкие",
      "vanilla": "ванильные",
      "amber": "амбровые",
      "fruity": "фруктовые",
      "cinnamon": "коричные",
      "leather": "кожаные",
      "powdery": "пудровые",
      "fresh-spicy": "свежие пряные",
      "aromatic": "ароматические",
      "citrus": "цитрусовые",
      "floral": "цветочные",
      "musky": "мускусные",
      "cognac": "коньяк",
      "tonka bean": "бобы тонка",
      "oak": "дуб",
      "candied almond": "засахаренный миндаль",
      "praline": "пралине",
      "sandalwood": "сандал"
    };
    for (const [k, v] of Object.entries(replacements)) {
      const reg = new RegExp(`\\b${k}\\b`, "gi");
      clean = clean.replace(reg, v);
    }
    return clean;
  }

  // ==========================================
  // Helper Functions
  // ==========================================
  function showLoading(subtext = "Анализируем формулу через Gemini и Scento...") {
    if (loadingSubtext) loadingSubtext.textContent = subtext;
    if (loadingOverlay) loadingOverlay.classList.add("active");
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

  function formatMarkdown(text) {
    if (!text) return "";
    let formatted = escapeHtml(text);
    // Bold
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Newlines
    formatted = formatted.replace(/\n\n/g, "<br><br>").replace(/\n/g, "<br>");
    return formatted;
  }

  // ==========================================
  // Step 1: Category Selection
  // ==========================================
  categoryChips.forEach(chip => {
    chip.addEventListener("click", () => {
      categoryChips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      selectedCategory = chip.getAttribute("data-cat") || "Унисекс";
      
      // If a search input exists with content, refresh suggestions
      if (searchInput && searchInput.value.trim().length >= 2) {
        handleSearchInput(searchInput.value.trim());
      }
    });
  });

  // ==========================================
  // Step 1: Live Autocomplete Search
  // ==========================================
  let searchDebounceTimer = null;

  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      const query = e.target.value.trim();
      clearTimeout(searchDebounceTimer);
      if (query.length < 2) {
        if (autocompleteDropdown) autocompleteDropdown.style.display = "none";
        return;
      }
      searchDebounceTimer = setTimeout(() => {
        handleSearchInput(query);
      }, 250);
    });

    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const query = searchInput.value.trim();
        if (query.length >= 2) {
          if (autocompleteDropdown) autocompleteDropdown.style.display = "none";
          selectPerfumeAndStart(query);
        }
      }
    });
  }

  if (startSommelierBtn) {
    startSommelierBtn.addEventListener("click", () => {
      const query = searchInput ? searchInput.value.trim() : "";
      if (query.length >= 2) {
        if (autocompleteDropdown) autocompleteDropdown.style.display = "none";
        selectPerfumeAndStart(query);
      } else {
        alert("Пожалуйста, введите название или бренд любимого парфюма.");
      }
    });
  }

  // Close dropdown on outside click
  document.addEventListener("click", (e) => {
    if (autocompleteDropdown && !autocompleteDropdown.contains(e.target) && e.target !== searchInput) {
      autocompleteDropdown.style.display = "none";
    }
  });

  async function handleSearchInput(query) {
    try {
      const catParam = encodeURIComponent(selectedCategory);
      const resp = await fetch(`/api/perfumes/search?q=${encodeURIComponent(query)}&limit=6&category=${catParam}`);
      if (!resp.ok) return;
      const data = await resp.json();
      renderAutocomplete(data.results || []);
    } catch (err) {
      console.warn("Search fetch error:", err);
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
        <span class="item-family">${escapeHtml(item.perfume.family || 'Нишевая парфюмерия')}</span>
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

  // Quick picks clicks
  quickPicks.forEach(chip => {
    chip.addEventListener("click", () => {
      const pName = chip.getAttribute("data-perfume");
      if (searchInput) searchInput.value = pName;
      selectPerfumeAndStart(pName);
    });
  });

  // ==========================================
  // Core Sommelier Start: Fetch DNA & Questions
  // ==========================================
  async function selectPerfumeAndStart(perfumeName) {
    if (!perfumeName) return;
    showLoading(`ИИ-Сомелье Aboo AI анализирует ДНК «${perfumeName}»...`);

    try {
      const resp = await fetch("/api/sommelier/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          perfume_name: perfumeName,
          category: selectedCategory
        })
      });

      if (!resp.ok) throw new Error("Не удалось получить ольфакторный паспорт");
      const data = await resp.json();

      currentSessionId = data.session_id;
      currentPerfume = data.matched_perfume;
      currentQuestions = data.questions || [];
      userAnswers = {};

      // Populate Passport Card
      populatePassport(currentPerfume);

      // Render Questions for Step 2
      renderQuestions(currentQuestions, data.analysis);

      hideLoading();

      // Scroll to passport card smoothly
      if (passportCard) {
        passportCard.style.display = "block";
        passportCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }

    } catch (err) {
      hideLoading();
      alert("Ошибка при анализе аромата: " + err.message);
    }
  }

  function populatePassport(perfume) {
    if (!passportCard || !perfume) return;

    if (passportBrand) passportBrand.textContent = perfume.brand || "Эксклюзив";
    if (passportName) passportName.textContent = perfume.name || "Парфюм";
    if (passportFamily) passportFamily.textContent = perfume.family || "Нишевая композиция";
    if (passportCharacter) {
      const charStr = perfume.character || `Оригинальная композиция бренда ${perfume.brand}`;
      passportCharacter.textContent = `«${formatCharacterRu(charStr)}»`;
    }

    function renderNotes(container, notes) {
      if (!container) return;
      if (!notes || notes.length === 0) {
        container.innerHTML = '<span class="note-chip">Базовые ноты</span>';
        return;
      }
      container.innerHTML = notes.map(n => `<span class="note-chip">${escapeHtml(translateNote(n))}</span>`).join("");
    }

    renderNotes(passportTop, perfume.top_notes);
    renderNotes(passportHeart, perfume.heart_notes);
    renderNotes(passportBase, perfume.base_notes);

    if (passportBottleImg) {
      const imgUrl = perfume.image_url || `/api/perfumes/${perfume.id || 'custom'}/badge.svg`;
      passportBottleImg.src = imgUrl;
      passportBottleImg.onerror = () => {
        passportBottleImg.src = "/static/images/pwa-icon.svg";
      };
    }

    passportCard.style.display = "block";
  }

  // Continue to Step 2 Button Click
  if (confirmPassportBtn) {
    confirmPassportBtn.addEventListener("click", () => {
      goToStep2();
    });
  }

  function goToStep2() {
    if (step1) step1.style.display = "none";
    if (step2) {
      step2.style.display = "block";
      step2.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    if (stepNav1) {
      stepNav1.classList.remove("active");
      stepNav1.classList.add("completed");
    }
    if (stepNav2) {
      stepNav2.classList.add("active");
    }
  }

  // ==========================================
  // Step 2: Render 5 Questions & Radio Selection
  // ==========================================
  function renderQuestions(questions, analysis) {
    if (sommelierIntroTitle && currentPerfume) {
      sommelierIntroTitle.textContent = `Ольфакторный вердикт по «${currentPerfume.brand} ${currentPerfume.name}»`;
    }
    if (sommelierIntroText && analysis) {
      sommelierIntroText.textContent = analysis;
    }

    if (!questionsList) return;

    questionsList.innerHTML = questions.map((q, idx) => {
      const aspectLabel = aspectTitles[q.aspect] || q.aspect || "Калибровка вкуса";
      const optionsHtml = (q.options || []).map(opt => `
        <button type="button" class="option-btn" data-qid="${q.id}" data-opt="${escapeHtml(opt)}">
          ${escapeHtml(opt)}
        </button>
      `).join("");

      return `
        <div class="question-card" data-qid="${q.id}">
          <div class="question-header">
            <span class="question-badge">ВОПРОС ${idx + 1} ИЗ 5</span>
            <span class="question-aspect-pill">${escapeHtml(aspectLabel)}</span>
          </div>
          <h4 class="question-title">${escapeHtml(q.question)}</h4>
          <div class="options-grid">
            ${optionsHtml}
          </div>
          <input 
            type="text" 
            class="custom-answer-input" 
            placeholder="Или напишите свой вариант ответа..." 
            data-qid="${q.id}" 
          />
        </div>
      `;
    }).join("");

    // Wire up clicks on option buttons
    questionsList.querySelectorAll(".option-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const qid = btn.getAttribute("data-qid");
        const val = btn.getAttribute("data-opt");
        questionsList.querySelectorAll(`.option-btn[data-qid="${qid}"]`).forEach(b => b.classList.remove("selected"));
        btn.classList.add("selected");
        
        // Clear custom input if option chosen
        const customInput = questionsList.querySelector(`.custom-answer-input[data-qid="${qid}"]`);
        if (customInput) customInput.value = "";

        userAnswers[qid] = val;
        updateQuizProgress();
      });
    });

    // Wire up typing in custom input
    questionsList.querySelectorAll(".custom-answer-input").forEach(inp => {
      inp.addEventListener("input", () => {
        const qid = inp.getAttribute("data-qid");
        const val = inp.value.trim();
        if (val.length > 0) {
          questionsList.querySelectorAll(`.option-btn[data-qid="${qid}"]`).forEach(b => b.classList.remove("selected"));
          userAnswers[qid] = val;
        } else {
          delete userAnswers[qid];
        }
        updateQuizProgress();
      });
    });

    updateQuizProgress();
  }

  function updateQuizProgress() {
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

  // ==========================================
  // Step 2 -> Step 3: Recommend Top-10
  // ==========================================
  if (submitAnswersBtn) {
    submitAnswersBtn.addEventListener("click", async () => {
      showLoading("Aboo AI активирует Chain-of-Thought и формирует персональный ТОП-10...");

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

        if (!resp.ok) throw new Error("Не удалось сформировать ТОП-10");
        const data = await resp.json();

        currentRecommendations = data.recommendations || [];
        currentChainOfThought = data.chain_of_thought || "";

        // Render Step 3
        renderStep3(data);

        // Transition from Step 2 to Step 3
        if (step2) step2.style.display = "none";
        if (step3) {
          step3.style.display = "block";
          step3.scrollIntoView({ behavior: "smooth", block: "start" });
        }
        if (stepNav2) {
          stepNav2.classList.remove("active");
          stepNav2.classList.add("completed");
        }
        if (stepNav3) {
          stepNav3.classList.add("active");
        }

        hideLoading();

        // ACTIVATE STEP 3 FLOATING ABOO AI CHAT IN BOTTOM-LEFT CORNER!
        activateFloatingAbooWidget();

      } catch (err) {
        hideLoading();
        alert("Ошибка при формировании рекомендаций: " + err.message);
      }
    });
  }

  // ==========================================
  // Step 3: Render Top-10 Cards & Chain of Thought
  // ==========================================
  function renderStep3(data) {
    // 1. Render Chain of Thought
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

    // 2. Sommelier Note
    if (sommelierNoteEl) {
      sommelierNoteEl.textContent = data.sommelier_note || "Опираясь на твой вкус, я составил выверенную подборку.";
    }

    // 3. Render 10 Cards Grid
    renderCards(currentRecommendations);
  }

  function renderCards(items) {
    if (!recommendationsGrid) return;

    if (!items || items.length === 0) {
      recommendationsGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-silver);">
          В данной категории ароматы не найдены.
        </div>
      `;
      return;
    }

    recommendationsGrid.innerHTML = items.map(item => {
      let badgeClass = "niche";
      let badgeLabel = "СМЕЛАЯ НИША (8-10)";
      if (item.rank <= 3) {
        badgeClass = "hit";
        badgeLabel = "ТОЧНОЕ ПОПАДАНИЕ (1-3)";
      } else if (item.rank <= 7) {
        badgeClass = "variation";
        badgeLabel = "ВАРИАЦИЯ (4-7)";
      }

      const img = item.image_url || `/api/perfumes/${item.id || 'flacon'}/badge.svg`;
      const rawNotes = Array.isArray(item.notes) ? item.notes : (item.notes ? item.notes.split(",") : ["Нишевые аккорды"]);
      const notes = rawNotes.map(n => translateNote(String(n).trim())).join(", ");

      return `
        <div class="rec-card" data-rank="${item.rank}">
          <div class="rec-card-bottle">
            <img src="${img}" alt="${escapeHtml(item.brand)} ${escapeHtml(item.name)}" onerror="this.src='/static/images/pwa-icon.svg'" />
          </div>
          <div class="rec-card-info">
            <div class="rec-rank-row">
              <span class="rec-rank-num">#${item.rank}</span>
              <span class="rec-badge ${badgeClass}">${badgeLabel}</span>
            </div>
            <div class="rec-name">${escapeHtml(item.name)}</div>
            <div class="rec-brand">${escapeHtml(item.brand)} • ${escapeHtml(item.family || 'Ниша')}</div>
            <div class="rec-notes">Ноты: ${escapeHtml(notes)}</div>
            <div class="rec-reason">«${escapeHtml(item.reason)}»</div>
          </div>
        </div>
      `;
    }).join("");
  }

  // Filter Tabs
  filterTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      filterTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const f = tab.getAttribute("data-filter");

      if (f === "hits") {
        renderCards(currentRecommendations.filter(r => r.rank >= 1 && r.rank <= 3));
      } else if (f === "variations") {
        renderCards(currentRecommendations.filter(r => r.rank >= 4 && r.rank <= 7));
      } else if (f === "bold") {
        renderCards(currentRecommendations.filter(r => r.rank >= 8 && r.rank <= 10));
      } else {
        renderCards(currentRecommendations);
      }
    });
  });

  // Copy List Button
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      if (!currentRecommendations || currentRecommendations.length === 0) return;
      const lines = [
        `✦ ТОП-10 ПАРФЮМОВ ОТ ABOO AI (Фаворит: ${currentPerfume ? currentPerfume.brand + ' ' + currentPerfume.name : 'ABOO Selection'}) ✦\n`
      ];
      currentRecommendations.forEach(r => {
        lines.push(`#${r.rank}. ${r.brand} — ${r.name}`);
        lines.push(`   Семейство: ${r.family}`);
        lines.push(`   Обоснование: ${r.reason}\n`);
      });
      navigator.clipboard.writeText(lines.join("\n")).then(() => {
        copyBtn.textContent = "✓ Скопировано!";
        setTimeout(() => {
          copyBtn.textContent = "📋 Скопировать список";
        }, 2200);
      });
    });
  }

  // Restart Button
  if (restartBtn) {
    restartBtn.addEventListener("click", () => {
      resetToStep1();
    });
  }

  function resetToStep1() {
    currentSessionId = null;
    currentPerfume = null;
    currentQuestions = [];
    userAnswers = {};
    currentRecommendations = [];
    chatInitialized = false;

    // Reset Steps
    if (step3) step3.style.display = "none";
    if (step2) step2.style.display = "none";
    if (step1) step1.style.display = "block";

    // Reset Stepper Nav
    if (stepNav1) {
      stepNav1.className = "step-item active";
    }
    if (stepNav2) {
      stepNav2.className = "step-item";
    }
    if (stepNav3) {
      stepNav3.className = "step-item";
    }

    // Hide Floating Aboo Widget
    if (floatingAbooContainer) {
      floatingAbooContainer.style.display = "none";
    }
    if (floatingChatWindow) {
      floatingChatWindow.style.display = "none";
    }
    isChatOpen = false;

    // Scroll to top
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // =========================================================================
  // STEP 3 FLOATING ABOO AI WIDGET & CHAT DRAWER (BOTTOM-LEFT CORNER)
  // =========================================================================
  function activateFloatingAbooWidget() {
    if (!floatingAbooContainer) return;
    floatingAbooContainer.style.display = "flex";

    // Auto-initialize chat welcome if not done yet
    if (!chatInitialized) {
      initFloatingChatGreeting();
      chatInitialized = true;
    }
  }

  if (floatingAbooTrigger) {
    floatingAbooTrigger.addEventListener("click", () => {
      toggleFloatingChat();
    });
  }

  if (floatingChatCloseBtn) {
    floatingChatCloseBtn.addEventListener("click", () => {
      toggleFloatingChat(false);
    });
  }

  function toggleFloatingChat(forceState = null) {
    if (!floatingChatWindow) return;
    if (forceState !== null) {
      isChatOpen = forceState;
    } else {
      isChatOpen = !isChatOpen;
    }

    if (isChatOpen) {
      floatingChatWindow.style.display = "flex";
      if (floatingChatInput) floatingChatInput.focus();
      scrollChatToBottom();
    } else {
      floatingChatWindow.style.display = "none";
    }
  }

  function initFloatingChatGreeting() {
    if (!floatingChatMessages) return;

    const pName = currentPerfume ? `${currentPerfume.brand} ${currentPerfume.name}` : "твоего выбора";
    const topPick = currentRecommendations[0] ? `${currentRecommendations[0].brand} ${currentRecommendations[0].name}` : "номер 1";

    floatingChatMessages.innerHTML = `
      <div class="floating-msg bot">
        <div class="floating-msg-avatar">
          <img src="/static/images/aboo-avatar.png" alt="Aboo AI" />
        </div>
        <div class="floating-msg-bubble">
          <strong>Приветствую! Я — Aboo AI</strong>, главный парфюмерный сомелье бренда ABOO PERFUMES.<br><br>
          Я сопоставил ДНК твоего любимого парфюма <em>${escapeHtml(pName)}</em> с твоими 5 ответами и сформировал этот эксклюзивный ТОП-10 (на вершине — <strong>${escapeHtml(topPick)}</strong>).<br><br>
          Нажми на быструю подсказку ниже или задай любой вопрос: стойкость, шлейф, вечерний повод или сравнение любых двух флаконов! ✦
        </div>
      </div>
    `;
  }

  function appendChatMessage(role, htmlContent) {
    if (!floatingChatMessages) return;

    const msgEl = document.createElement("div");
    msgEl.className = `floating-msg ${role}`;

    if (role === "bot") {
      msgEl.innerHTML = `
        <div class="floating-msg-avatar">
          <img src="/static/images/aboo-avatar.png" alt="Aboo AI" />
        </div>
        <div class="floating-msg-bubble">${htmlContent}</div>
      `;
    } else {
      msgEl.innerHTML = `
        <div class="floating-msg-bubble">${htmlContent}</div>
      `;
    }

    floatingChatMessages.appendChild(msgEl);
    scrollChatToBottom();
    return msgEl;
  }

  function scrollChatToBottom() {
    if (floatingChatMessages) {
      floatingChatMessages.scrollTop = floatingChatMessages.scrollHeight;
    }
  }

  // Quick Chips in Floating Chat
  floatingQuickChips.forEach(chip => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      if (prompt) {
        handleUserChatMessage(prompt);
      }
    });
  });

  // Chat Form Submission
  if (floatingChatForm && floatingChatInput) {
    floatingChatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = floatingChatInput.value.trim();
      if (text.length > 0) {
        floatingChatInput.value = "";
        handleUserChatMessage(text);
      }
    });
  }

  async function handleUserChatMessage(userText) {
    if (isChatAiBusy) return;
    isChatAiBusy = true;

    // Append user message
    appendChatMessage("user", escapeHtml(userText));

    // Append thinking placeholder
    const thinkingEl = appendChatMessage("bot", `
      <span style="opacity: 0.8; font-style: italic;">
        ✦ Aboo AI анализирует формулы рекомендаций...
      </span>
    `);

    try {
      const resp = await fetch("/api/sommelier/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userText,
          session_id: currentSessionId,
          perfume_name: currentPerfume ? `${currentPerfume.brand} ${currentPerfume.name}` : null,
          recommendations: currentRecommendations,
          category: selectedCategory
        })
      });

      if (!resp.ok) throw new Error("Ошибка связи с сомелье");
      const data = await resp.json();

      const replyHtml = formatMarkdown(data.reply);
      if (thinkingEl) {
        const bubble = thinkingEl.querySelector(".floating-msg-bubble");
        if (bubble) bubble.innerHTML = replyHtml;
      }
      scrollChatToBottom();

    } catch (err) {
      if (thinkingEl) {
        const bubble = thinkingEl.querySelector(".floating-msg-bubble");
        if (bubble) bubble.innerHTML = "Извините, произошла небольшая заминка при связи с базой. Попробуйте еще раз.";
      }
    } finally {
      isChatAiBusy = false;
    }
  }

  // ==========================================
  // Character Showcase Modal
  // ==========================================
  if (openCharModalBtn && characterModal) {
    openCharModalBtn.addEventListener("click", () => {
      characterModal.classList.add("active");
    });
  }

  if (closeCharModalBtn && characterModal) {
    closeCharModalBtn.addEventListener("click", () => {
      characterModal.classList.remove("active");
    });
  }

  if (characterModal) {
    characterModal.addEventListener("click", (e) => {
      if (e.target === characterModal) {
        characterModal.classList.remove("active");
      }
    });
  }
});
