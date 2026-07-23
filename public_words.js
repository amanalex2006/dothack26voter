// Public Wordlist (2048 BIP-39 standard English words)
let PUBLIC_WORDS = [];

// Load from local words.json or fallback array if needed
async function initPublicWordlist() {
    try {
        const res = await fetch('/words.json');
        if (res.ok) {
            PUBLIC_WORDS = await res.json();
        }
    } catch (e) {
        console.warn('Wordlist fetch fallback used', e);
    }
}

// Generate a 2-word password with hyphen separator
function generatePublicPassword() {
    if (!PUBLIC_WORDS || PUBLIC_WORDS.length === 0) {
        // High quality local fallback list if fetch fails
        const fallbackAdj = ["swift","bright","dark","hollow","amber","crisp","silver","bold","quiet","solar","lunar","iron","copper","wild","frozen","velvet","glassy","rusted","bitter","jade","neon","ashen","mossy","dusty","stark","pale","vivid","sharp","delta","cobalt"];
        const fallbackNoun = ["ridge","vault","storm","forge","cliff","ember","grove","prism","flare","drift","haven","thorn","crater","spire","basin","nexus","glyph","orbit","marsh","titan","comet","raven","shroud","flint","abyss","bloom","quartz","zenith","shard","void"];
        const a = fallbackAdj[Math.floor(Math.random() * fallbackAdj.length)];
        const n = fallbackNoun[Math.floor(Math.random() * fallbackNoun.length)];
        return `${a}-${n}`;
    }
    const w1 = PUBLIC_WORDS[Math.floor(Math.random() * PUBLIC_WORDS.length)];
    let w2 = PUBLIC_WORDS[Math.floor(Math.random() * PUBLIC_WORDS.length)];
    while (w2 === w1) {
        w2 = PUBLIC_WORDS[Math.floor(Math.random() * PUBLIC_WORDS.length)];
    }
    return `${w1}-${w2}`;
}

// Decaying Password Input Handler
// Shows typed character briefly before decaying to '•'
function setupDecayingPasswordInput(inputEl, delay = 700) {
    if (!inputEl) return null;

    let realValue = "";
    let maskTimer = null;

    inputEl.type = "text";
    inputEl.autocomplete = "off";
    inputEl.spellcheck = false;

    function updateMask(showLast = true) {
        clearTimeout(maskTimer);
        if (!realValue) {
            inputEl.value = "";
            return;
        }
        if (showLast && realValue.length > 0) {
            const masked = "•".repeat(realValue.length - 1) + realValue.slice(-1);
            inputEl.value = masked;
            maskTimer = setTimeout(() => {
                inputEl.value = "•".repeat(realValue.length);
            }, delay);
        } else {
            inputEl.value = "•".repeat(realValue.length);
        }
    }

    inputEl.addEventListener("input", (e) => {
        const currentText = inputEl.value;
        if (e.inputType === "deleteContentBackward" || e.inputType === "deleteContentForward") {
            realValue = realValue.slice(0, currentText.length);
            updateMask(false);
        } else {
            if (currentText.length > realValue.length) {
                const diff = currentText.length - realValue.length;
                const newlyTyped = currentText.slice(-diff);
                realValue += newlyTyped;
                updateMask(true);
            } else if (currentText.length < realValue.length) {
                realValue = realValue.slice(0, currentText.length);
                updateMask(false);
            }
        }
    });

    return {
        get value() { return realValue; },
        set value(val) {
            realValue = val || "";
            updateMask(false);
        },
        clear() {
            realValue = "";
            inputEl.value = "";
            clearTimeout(maskTimer);
        }
    };
}

// Automatically initialize wordlist on load
initPublicWordlist();
