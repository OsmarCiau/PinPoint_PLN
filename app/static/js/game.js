const i18n = {
    spa: {
        inputPlaceholder: "> ESCRIBE TU RESPUESTA_",
        clueLocked: "[PISTA BLOQUEADA]",
        emptyInputWarning: "[!] ESCRIBE UNA PALABRA_",
        networkError: "[!] ERROR DE CONEXIÓN CON EL SERVIDOR",
        stageClear: "> STAGE CLEAR! <",
        gameOver: "> GAME OVER <",
        acceptedLabel: "ACEPTADAS:",
        solutionLabel: "SOLUCIÓN:",
        synonymsLabel: "SINÓNIMOS:",
        restartBtn: "[ INSERT COIN / REINTENTAR ]",
        levelLabel: "NIVEL DE PISTAS:",
        processing: "[ PROCESANDO RESPUESTA... ]",
        revealing: "[ REVELANDO PISTA... ]",
        starting: "[ INICIANDO PARTIDA... ]",
    },
    eng: {
        inputPlaceholder: "> ENTER YOUR GUESS_",
        clueLocked: "[LOCKED CLUE]",
        emptyInputWarning: "[!] ENTER A WORD FIRST_",
        networkError: "[!] SERVER CONNECTION ERROR",
        stageClear: "> STAGE CLEAR! <",
        gameOver: "> GAME OVER <",
        acceptedLabel: "ACCEPTED:",
        solutionLabel: "SOLUTION:",
        synonymsLabel: "SYNONYMS:",
        restartBtn: "[ INSERT COIN / RETRY ]",
        levelLabel: "CLUE LEVEL:",
        processing: "[ PROCESSING GUESS... ]",
        revealing: "[ REVEALING CLUE... ]",
        starting: "[ STARTING MATCH... ]",
    }
};

let currentLanguage = "spa";
let currentSession = null;
let catalog = [];

const clueContainer = document.getElementById("clues-container");
const guessInput = document.getElementById("guess-input");
const submitBtn = document.getElementById("submit-guess-btn");
const revealBtn = document.getElementById("reveal-clue-btn");
const restartBtn = document.getElementById("restart-btn");
const btnLangEs = document.getElementById("btn-lang-es");
const btnLangEn = document.getElementById("btn-lang-en");
const demoCategorySelect = document.getElementById("demo-category-select");
const demoLoadBtn = document.getElementById("demo-load-btn");
const clueCounter = document.getElementById("clue-counter");
const feedbackBanner = document.getElementById("feedback-banner");
const feedbackMessage = document.getElementById("feedback-message");
const progressIndicators = document.getElementById("progress-indicators");
const resultScreen = document.getElementById("result-screen");
const resultTitle = document.getElementById("result-title");
const resultScore = document.getElementById("result-score");
const resultDetails = document.getElementById("result-details");
const inputContainer = document.getElementById("input-container");

async function fetchCatalog() {
    try {
        const response = await fetch("/api/game/catalog");
        if (response.ok) {
            catalog = await response.json();
            populateDemoCategorySelect();
        }
    } catch (error) {
        showFeedback(i18n[currentLanguage].networkError, "error");
    }
}

function populateDemoCategorySelect() {
    demoCategorySelect.innerHTML = "";
    catalog.forEach(item => {
        const option = document.createElement("option");
        option.value = item.synset_id;
        const categoryLabel = currentLanguage === "spa" ? item.category_es : item.category_en;
        const lemmaName = item.synset_id.split('.')[0].replace('_', ' ');
        option.textContent = `${categoryLabel} - ${lemmaName}`;
        demoCategorySelect.appendChild(option);
    });
}

function setLanguage(lang) {
    currentLanguage = lang;
    if (lang === "spa") {
        btnLangEs.className = "px-2.5 py-1 text-[10px] font-bold border-2 border-[#45A29E] bg-[#66FCF1] text-[#000000] retro-btn";
        btnLangEn.className = "px-2.5 py-1 text-[10px] font-bold border-2 border-[#45A29E] bg-[#0B0C10] text-[#C5C6C7] retro-btn";
    } else {
        btnLangEn.className = "px-2.5 py-1 text-[10px] font-bold border-2 border-[#45A29E] bg-[#66FCF1] text-[#000000] retro-btn";
        btnLangEs.className = "px-2.5 py-1 text-[10px] font-bold border-2 border-[#45A29E] bg-[#0B0C10] text-[#C5C6C7] retro-btn";
    }

    guessInput.placeholder = i18n[currentLanguage].inputPlaceholder;
    restartBtn.textContent = i18n[currentLanguage].restartBtn;
    populateDemoCategorySelect();
    startNewGame(null);
}

async function startNewGame(forcedSynset = null) {
    hideFeedback();
    resultScreen.classList.add("hidden");
    inputContainer.classList.remove("hidden");
    guessInput.value = "";
    guessInput.disabled = true;
    submitBtn.disabled = true;
    revealBtn.disabled = true;
    showFeedback(i18n[currentLanguage].starting, "info");

    try {
        const response = await fetch("/api/game/new", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                language: currentLanguage,
                synset_id: forcedSynset
            })
        });

        if (!response.ok) {
            throw new Error();
        }

        currentSession = await response.json();
        hideFeedback();
        renderClues();
        renderProgress();
    } catch (error) {
        showFeedback(i18n[currentLanguage].networkError, "error");
    } finally {
        guessInput.disabled = false;
        submitBtn.disabled = false;
        revealBtn.disabled = false;
        guessInput.focus();
    }
}

async function handleGuess() {
    const guessText = guessInput.value.trim();
    if (!guessText) {
        showFeedback(i18n[currentLanguage].emptyInputWarning, "warning");
        return;
    }

    if (!currentSession || currentSession.is_game_over) {
        return;
    }

    submitBtn.disabled = true;
    revealBtn.disabled = true;
    guessInput.disabled = true;
    guessInput.classList.add("arcade-blink");
    showFeedback(i18n[currentLanguage].processing, "info");

    try {
        const response = await fetch("/api/game/guess", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: currentSession.session_id,
                guess: guessText
            })
        });

        if (!response.ok) {
            throw new Error();
        }

        const result = await response.json();
        hideFeedback();
        updateGameWithResult(result);
        guessInput.value = "";
    } catch (error) {
        showFeedback(i18n[currentLanguage].networkError, "error");
    } finally {
        guessInput.classList.remove("arcade-blink");
        guessInput.disabled = false;
        if (!currentSession.is_game_over) {
            submitBtn.disabled = false;
            revealBtn.disabled = false;
            guessInput.focus();
        }
    }
}

async function handleReveal() {
    if (!currentSession || currentSession.is_game_over) {
        return;
    }

    submitBtn.disabled = true;
    revealBtn.disabled = true;
    guessInput.disabled = true;
    showFeedback(i18n[currentLanguage].revealing, "info");

    try {
        const response = await fetch("/api/game/reveal", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: currentSession.session_id
            })
        });

        if (!response.ok) {
            throw new Error();
        }

        const result = await response.json();
        hideFeedback();
        updateGameWithResult(result);
    } catch (error) {
        showFeedback(i18n[currentLanguage].networkError, "error");
    } finally {
        guessInput.disabled = false;
        if (!currentSession.is_game_over) {
            submitBtn.disabled = false;
            revealBtn.disabled = false;
            guessInput.focus();
        }
    }
}

function updateGameWithResult(result) {
    currentSession.attempts_used = result.attempts_used;
    currentSession.revealed_clues = result.revealed_clues;
    currentSession.is_game_over = result.is_game_over;
    currentSession.is_solved = result.is_solved;
    currentSession.score = result.score;

    renderClues();
    renderProgress();

    if (result.is_correct) {
        finishGame(true, result);
    } else if (result.is_game_over) {
        finishGame(false, result);
    } else {
        const failureText = currentLanguage === "spa" ? "[!] INTENTO FALLIDO" : "[!] GUESS FAILED";
        showFeedback(failureText, "error");
        guessInput.classList.add("arcade-shake");
        setTimeout(() => guessInput.classList.remove("arcade-shake"), 400);
    }
}

function finishGame(isWinner, result) {
    inputContainer.classList.add("hidden");
    hideFeedback();

    const texts = i18n[currentLanguage];
    resultScreen.classList.remove("hidden");

    if (isWinner) {
        resultScreen.className = "p-4 bg-[#0B0C10] border-4 border-[#22C55E] shadow-[6px_6px_0px_#000000] mb-4 text-center";
        resultTitle.className = "text-sm sm:text-base font-bold mb-3 tracking-wider text-[#22C55E]";
        resultTitle.textContent = texts.stageClear;
        resultScore.textContent = `SCORE: ${result.score * 1000} PTS`;
        const acceptedWords = result.alternative_lemmas.map(l => l.toUpperCase()).join(", ");
        resultDetails.textContent = `${texts.acceptedLabel} ${acceptedWords}`;
    } else {
        resultScreen.className = "p-4 bg-[#0B0C10] border-4 border-[#EF4444] shadow-[6px_6px_0px_#000000] mb-4 text-center";
        resultTitle.className = "text-sm sm:text-base font-bold mb-3 tracking-wider text-[#EF4444]";
        resultTitle.textContent = texts.gameOver;
        resultScore.textContent = "SCORE: 0 PTS";
        const targetWord = (result.target_lemma || "").toUpperCase();
        const altWords = result.alternative_lemmas.filter(l => l.toLowerCase() !== (result.target_lemma || "").toLowerCase()).map(l => l.toUpperCase()).join(", ");
        resultDetails.innerHTML = `${texts.solutionLabel} ${targetWord}<br><br>${texts.synonymsLabel} ${altWords || targetWord}`;
    }
}

function renderClues() {
    clueContainer.innerHTML = "";
    const totalClues = 5;
    const revealedCount = currentSession ? currentSession.revealed_clues.length : 1;

    for (let index = 1; index <= totalClues; index++) {
        const isRevealed = currentSession && index <= revealedCount;
        const clueData = isRevealed ? currentSession.revealed_clues[index - 1] : null;

        const card = document.createElement("div");

        if (isRevealed && clueData) {
            card.className = "flex items-center justify-between p-2.5 sm:p-3 bg-[#0B0C10] border-2 border-[#45A29E] shadow-[3px_3px_0px_#000000]";
            card.innerHTML = `
                <div class="flex items-center space-x-2 sm:space-x-3 overflow-hidden">
                    <span class="text-[#66FCF1] text-xs font-bold font-mono shrink-0">#${index}</span>
                    <span class="text-[#FFFFFF] text-xs font-bold tracking-wider uppercase truncate">${clueData.text}</span>
                </div>
                <span class="text-[8px] tracking-wider text-[#66FCF1] border border-[#45A29E] bg-[#1F2833] px-1.5 sm:px-2 py-0.5 uppercase shrink-0">
                    [${clueData.relation_display.toUpperCase()}]
                </span>
            `;
        } else {
            card.className = "flex items-center justify-between p-2.5 sm:p-3 bg-[#0B0C10] border-2 border-dashed border-[#1F2833] text-[#45A29E]";
            card.innerHTML = `
                <span class="text-xs font-bold text-[#45A29E]">#${index} ???</span>
                <span class="text-[8px] uppercase tracking-wider text-[#45A29E]">${i18n[currentLanguage].clueLocked}</span>
            `;
        }
        clueContainer.appendChild(card);
    }
}

function renderProgress() {
    progressIndicators.innerHTML = "";
    const totalClues = 5;
    const revealedCount = currentSession ? currentSession.revealed_clues.length : 1;

    clueCounter.textContent = `${revealedCount} / ${totalClues}`;

    for (let i = 1; i <= totalClues; i++) {
        const cell = document.createElement("div");
        if (i <= revealedCount) {
            cell.className = "bg-[#66FCF1] border-2 border-[#0B0C10]";
        } else {
            cell.className = "bg-[#0B0C10] border-2 border-[#45A29E]";
        }
        progressIndicators.appendChild(cell);
    }
}

function showFeedback(message, type) {
    feedbackMessage.textContent = message;
    if (type === "error") {
        feedbackBanner.className = "p-3 bg-[#0B0C10] border-2 border-[#EF4444] text-[#EF4444] mb-4 text-[10px] leading-relaxed";
    } else if (type === "warning") {
        feedbackBanner.className = "p-3 bg-[#0B0C10] border-2 border-[#F59E0B] text-[#F59E0B] mb-4 text-[10px] leading-relaxed";
    } else if (type === "info") {
        feedbackBanner.className = "p-3 bg-[#0B0C10] border-2 border-[#66FCF1] text-[#66FCF1] mb-4 text-[10px] leading-relaxed arcade-blink";
    } else {
        feedbackBanner.className = "p-3 bg-[#0B0C10] border-2 border-[#45A29E] text-[#66FCF1] mb-4 text-[10px] leading-relaxed";
    }
    feedbackBanner.classList.remove("hidden");
}

function hideFeedback() {
    feedbackBanner.classList.add("hidden");
}

btnLangEs.addEventListener("click", () => setLanguage("spa"));
btnLangEn.addEventListener("click", () => setLanguage("eng"));

submitBtn.addEventListener("click", handleGuess);
revealBtn.addEventListener("click", handleReveal);
restartBtn.addEventListener("click", () => startNewGame(null));

demoLoadBtn.addEventListener("click", () => {
    const selected = demoCategorySelect.value;
    if (selected) {
        startNewGame(selected);
    }
});

guessInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        event.preventDefault();
        handleGuess();
    }
});

window.addEventListener("DOMContentLoaded", async () => {
    await fetchCatalog();
    setLanguage("spa");
});
