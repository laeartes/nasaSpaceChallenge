function runSearch() {
    const term = document.getElementById('searchInput').value.trim();
    if (!term) {
        document.getElementById('results').innerText = "Please enter a search term.";
        return;
    }
    document.getElementById('results').innerText = "Searching...";
    document.getElementById('detailPanel').innerHTML = "";
    fetch('/search?query=' + encodeURIComponent(term))
        .then(response => {
            if (!response.ok) throw new Error("Network response was not ok");
            return response.json();
        })
        .then(items => {
            const resultsEl = document.getElementById('results');
            resultsEl.innerHTML = "";
            if (!Array.isArray(items) || items.length === 0) {
                resultsEl.innerText = "No results.";
                return;
            }
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
            document.getElementById('results').innerText = "Error during search: " + err.message;
        });
}

function showSection(article, sec) {
    const panel = document.getElementById('detailPanel');
    panel.innerHTML = "";
    const title = document.createElement('h3');
    title.innerText = article.name || "Article";
    panel.appendChild(title);
    const sectionTitle = document.createElement('h4');
    sectionTitle.innerText = (sec.title ? sec.title : (sec.type || "section"));
    panel.appendChild(sectionTitle);
    const content = document.createElement('p');
    content.innerText = (sec.content !== undefined && sec.content !== null && sec.content !== "") ? sec.content : (sec.excerpt || "");
    panel.appendChild(content);
    const openBtn = document.createElement('button');
    openBtn.innerText = "Open full article";
    openBtn.onclick = () => window.open(article.link || "#", "_blank");
    panel.appendChild(openBtn);
    const selectBtn = document.createElement('button');
    selectBtn.innerText = "Select this section";
    selectBtn.style.marginLeft = "8px";
    selectBtn.onclick = () => { alert("Selected section: " + (sec.title || "section")); };
    panel.appendChild(selectBtn);
}

document.addEventListener('keydown', function(e) {
    const el = document.activeElement;
    if (e.key === 'Enter' && (el && el.id === 'searchInput')) {
        e.preventDefault();
        runSearch();
    }
});