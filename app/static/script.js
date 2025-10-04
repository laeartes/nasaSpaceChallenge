function runSearch() {
    const term = document.getElementById('searchInput').value.trim();
    const exactOnly = !!document.getElementById('exactOnly') && document.getElementById('exactOnly').checked;
    // minRefs removed; search focuses on matches only
    if (!term) {
        document.getElementById('results').innerText = "Please enter a search term.";
        return;
    }
    document.getElementById('results').innerText = "Searching...";
    document.getElementById('detailPanel').innerHTML = "";
    const exactParam = exactOnly ? "&exact=1" : "";
    fetch('/search?query=' + encodeURIComponent(term) + exactParam)
        .then(response => {
            if (!response.ok) {
                return response.json().then(errBody => {
                    const message = (errBody && (errBody.detail || errBody.error)) ? (errBody.detail || errBody.error) : `HTTP ${response.status}`;
                    throw new Error(message);
                }).catch(() => {
                    throw new Error(`HTTP ${response.status}`);
                });
            }
            return response.json();
        })
        .then(items => {
            const resultsEl = document.getElementById('results');
            resultsEl.innerHTML = "";
            if (!Array.isArray(items) || items.length === 0) {
                resultsEl.innerText = "No results.";
                const summaryEl = document.getElementById('resultsSummary');
                if (summaryEl) summaryEl.innerText = "Found 0 articles.";
                return;
            }
            // summary: total articles and total matched sections
            const totalArticles = items.length;
            const totalMatchedSections = items.reduce((acc, it) => acc + (it.match_count || 0), 0);
            const summaryEl = document.getElementById('resultsSummary');
            if (summaryEl) summaryEl.innerText = `Found ${totalArticles} articles — ${totalMatchedSections} matched sections (shown per item)`;
            const list = document.createElement('ul');
            items.forEach(article => {
                const li = document.createElement('li');
                const header = document.createElement('div');
                const a = document.createElement('a');
                a.href = article.link || "#";
                a.innerText = article.name || (article.link || "Untitled");
                a.target = "_blank";
                a.style.fontWeight = "600";
                header.appendChild(a);
                // small meta: matches and counts
                const meta = document.createElement('span');
                meta.style.marginLeft = "8px";
                meta.style.fontSize = "0.95rem";
                meta.style.color = "var(--muted)";
                const mcount = article.match_count || 0;
                const occ = article.occurrence_count || 0;
                const wcount = article.word_match_count || 0;
                let parts = [`${mcount} matches`];
                if (occ > 0) parts.push(`${occ} occurrences`);
                else if (wcount > 0) parts.push(`${wcount} words`);
                meta.innerText = ` ${parts.join(' • ')}`;
                header.appendChild(meta);
                const openBtn = document.createElement('button');
                openBtn.innerText = "Open article";
                openBtn.style.marginLeft = "8px";
                openBtn.onclick = () => window.open(article.link || "#", "_blank");
                header.appendChild(openBtn);
                li.appendChild(header);
                if (Array.isArray(article.sections) && article.sections.length > 0) {
                    const sub = document.createElement('ul');
                    article.sections.forEach((sectionObj, idx) => {
                        const subLi = document.createElement('li');
                        const sectionBtn = document.createElement('button');
                        sectionBtn.innerText = sectionObj.title || ("section " + (idx + 1));
                        sectionBtn.style.marginRight = "8px";
                        if (sectionObj.matched) {
                            sectionBtn.style.backgroundColor = "#2a2";
                            sectionBtn.style.color = "#000";
                        }
                        sectionBtn.onclick = () => showSection(article, sectionObj);
                        subLi.appendChild(sectionBtn);
                        sub.appendChild(subLi);
                    });
                    li.appendChild(sub);
                } else if (Array.isArray(article.matches) && article.matches.length > 0) {
                    const sub = document.createElement('ul');
                    article.matches.forEach((m, idx) => {
                        const subLi = document.createElement('li');
                        const btn = document.createElement('button');
                        btn.innerText = (m.title || ("section " + (idx+1)));
                        btn.style.marginRight = "8px";
                        btn.onclick = () => showSection(article, m);
                        subLi.appendChild(btn);
                        sub.appendChild(subLi);
                    });
                    li.appendChild(sub);
                }
                list.appendChild(li);
            });
            resultsEl.appendChild(list);
        })
        .catch(err => {
            const out = "Error during search: " + err.message;
            document.getElementById('results').innerText = out;
            const summaryEl = document.getElementById('resultsSummary');
            if (summaryEl) summaryEl.innerText = out;
        });
}

// helper: make a safe id from strings
function slugify(input) {
    if (!input) return "section";
    return input.toString()
        .toLowerCase()
        .trim()
        .replace(/\s+/g, "-")         // spaces -> dashes
        .replace(/[^a-z0-9\-_]/g, "") // remove unsafe chars
        .replace(/-+/g, "-");         // collapse dashes
}

function showSection(article, sec) {
    const panel = document.getElementById('detailPanel');
    panel.innerHTML = "";

    // create a stable id for this article+section so we can use #anchor-style navigation
    const base = (article && article.name) ? article.name : (article && article.link) ? article.link : "article";
    const titleText = sec && (sec.title || sec.type) ? (sec.title || sec.type) : "section";
    const id = "detail-" + slugify(base + "-" + titleText);

    // wrapper with id so location.hash will jump to it
    const wrapper = document.createElement('div');
    wrapper.id = id;
    wrapper.setAttribute('data-article', base);
    wrapper.setAttribute('data-section', titleText);

    const title = document.createElement('h3');
    title.innerText = article.name || "Article";
    wrapper.appendChild(title);

    const sectionTitle = document.createElement('h4');
    sectionTitle.innerText = (sec.title ? sec.title : (sec.type || "section"));
    wrapper.appendChild(sectionTitle);

    const content = document.createElement('p');
    content.innerText = (sec.content !== undefined && sec.content !== null && sec.content !== "") ? sec.content : (sec.excerpt || "");
    wrapper.appendChild(content);

    const openBtn = document.createElement('button');
    openBtn.innerText = "Open full article";
    openBtn.onclick = () => window.open(article.link || "#", "_blank");
    wrapper.appendChild(openBtn);

    // replace "Select this section" with a "Scroll to top" button
    const upBtn = document.createElement('button');
    upBtn.innerText = "Scroll to top";
    upBtn.style.marginLeft = "8px";
    upBtn.onclick = () => {
        try {
            // instant jump to top
            window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
            // set focus back to the detail panel for accessibility
            try {
                panel.setAttribute('tabindex', '-1');
                panel.focus({ preventScroll: true });
            } catch (e) {}
        } catch (e) {
            // fail silently
            console.warn("Scroll to top failed", e);
        }
    };
    wrapper.appendChild(upBtn);

    panel.appendChild(wrapper);

    // emulate anchor behavior: set hash after element is in DOM so browser jumps to it
    try {
        const hash = "#" + id;
        setTimeout(() => {
            window.location.hash = hash;
            try {
                panel.setAttribute('tabindex', '-1');
                panel.focus({ preventScroll: true });
            } catch (e) {}
        }, 0);
    } catch (e) {
        console.warn("Anchor navigation failed:", e);
    }
}

// theme initialization and toggle
function setTheme(name) {
    document.body.classList.remove('dark-mode', 'light-mode');
    document.body.classList.add(name + '-mode');
    try { localStorage.setItem('theme', name); } catch (e) {}
    const btn = document.getElementById('themeToggle');
    if (btn) btn.innerText = name === 'dark' ? 'Switch to light' : 'Switch to dark';
}

function toggleTheme() {
    const current = document.body.classList.contains('dark-mode') ? 'dark' : 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    setTheme(next);
}

(function initTheme() {
    try {
        const saved = localStorage.getItem('theme');
        if (saved === 'light' || saved === 'dark') {
            setTheme(saved);
            return;
        }
    } catch (e) {}
    setTheme('dark');
})();

// font size helpers and preferences
function applyFontSize(name) {
    const map = { small: '14px', medium: '16px', large: '18px', xlarge: '20px' };
    const size = map[name] || map['medium'];
    try { document.documentElement.style.fontSize = size; } catch (e) {}
    try { localStorage.setItem('fontSize', name); } catch (e) {}
}

function increaseText() {
    const sizes = ['small','medium','large','xlarge'];
    const currentName = localStorage.getItem('fontSize') || 'medium';
    const idx = Math.max(0, sizes.indexOf(currentName));
    const next = sizes[Math.min(sizes.length-1, idx + 1)];
    applyFontSize(next);
}

function decreaseText() {
    const sizes = ['small','medium','large','xlarge'];
    const currentName = localStorage.getItem('fontSize') || 'medium';
    const idx = Math.max(0, sizes.indexOf(currentName));
    const next = sizes[Math.max(0, idx - 1)];
    applyFontSize(next);
}

function resetText() {
    applyFontSize('medium');
}

(function initPreferences() {
    try {
        const savedFont = localStorage.getItem('fontSize');
        if (savedFont) applyFontSize(savedFont);
    } catch (e) {}
})();

document.addEventListener('keydown', function(e) {
    const el = document.activeElement;
    if (e.key === 'Enter' && (el && el.id === 'searchInput')) {
        e.preventDefault();
        runSearch();
    }
});