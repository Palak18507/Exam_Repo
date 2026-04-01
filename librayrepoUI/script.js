/* ============================================================
   IGDTUW Question Papers Archive — script.js
   Connected to FastAPI Docker Backend
   ============================================================ */

const API_BASE = 'http://localhost:8000';

/* ── Real API layer ── */
const API = {
  getStats: () => fetch(`${API_BASE}/stats`).then(r => r.json()),
  
  getFilters: () => fetch(`${API_BASE}/filters`).then(r => r.json()),

  // Traditional Paper Search
  search: (filters) => {
    const params = new URLSearchParams();
    if (filters.branch)        params.set('department', filters.branch);
    if (filters.semester)      params.set('semester', filters.semester);
    if (filters.subject_code)  params.set('subject_name', filters.subject_code); 
    if (filters.examType)      params.set('exam_type', filters.examType);
    if (filters.academic_year) params.set('academic_year', filters.academic_year);
    
    return fetch(`${API_BASE}/search?${params}`).then(r => r.json()).then(d => d.papers || []);
  },

  // Semantic Question Search
  searchQuestions: (filters) => {
    const params = new URLSearchParams();
    if (filters.search)        params.set('query', filters.search);
    if (filters.branch)        params.set('department', filters.branch);
    if (filters.subject_code)  params.set('subject_name', filters.subject_code);
    return fetch(`${API_BASE}/search/questions?${params}`).then(r => r.json());
  },

  semanticSearch: (query, filters = {}) => {
    return API.searchQuestions({search: query, ...filters});
  },

  getDownloadUrl: (paperId) => `${API_BASE}/papers/${paperId}/download`,
  
  // Fallbacks for UI components that don't have perfect backend matches yet
  getSuggestions: async (query) => [],
  getRepeatedQuestions: async () => ({ repeated: [] }),
  getTopicClusters: async () => ({ topics: [] })
};

/* ── Autocomplete for search bars ── */
function initAutocomplete(inputEl, onSelect) {
  if (!inputEl) return;

  // Create dropdown container
  const wrapper = inputEl.parentElement;
  wrapper.style.position = 'relative';

  const dropdown = document.createElement('div');
  dropdown.className = 'autocomplete-dropdown';
  wrapper.appendChild(dropdown);

  let debounceTimer = null;
  let activeIndex = -1;
  let currentItems = [];

  function hide() {
    dropdown.innerHTML = '';
    dropdown.style.display = 'none';
    activeIndex = -1;
    currentItems = [];
  }

  function show(items) {
    if (!items.length) { hide(); return; }
    currentItems = items;
    activeIndex = -1;
    dropdown.innerHTML = items.map((item, i) => {
      // Bold the matching part
      const query = inputEl.value.trim().toLowerCase();
      const idx = item.toLowerCase().indexOf(query);
      let html = item;
      if (idx >= 0) {
        html = item.slice(0, idx) + '<strong>' + item.slice(idx, idx + query.length) + '</strong>' + item.slice(idx + query.length);
      }
      return `<div class="autocomplete-item" data-index="${i}">${html}</div>`;
    }).join('');
    dropdown.style.display = 'block';

    // Click handlers
    dropdown.querySelectorAll('.autocomplete-item').forEach(el => {
      el.addEventListener('mousedown', (e) => {
        e.preventDefault();
        inputEl.value = items[parseInt(el.dataset.index)];
        hide();
        if (onSelect) onSelect();
      });
    });
  }

  function highlight(index) {
    const items = dropdown.querySelectorAll('.autocomplete-item');
    items.forEach(el => el.classList.remove('active'));
    if (index >= 0 && index < items.length) {
      items[index].classList.add('active');
      items[index].scrollIntoView({ block: 'nearest' });
    }
  }

  inputEl.addEventListener('input', () => {
    const q = inputEl.value.trim();
    if (q.length < 1) { hide(); return; }
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      try {
        const suggestions = await API.getSuggestions(q);
        show(suggestions);
      } catch (e) { hide(); }
    }, 150);
  });

  inputEl.addEventListener('keydown', (e) => {
    if (!currentItems.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, currentItems.length - 1);
      highlight(activeIndex);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, 0);
      highlight(activeIndex);
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      inputEl.value = currentItems[activeIndex];
      hide();
      if (onSelect) onSelect();
    } else if (e.key === 'Escape') {
      hide();
    }
  });

  inputEl.addEventListener('blur', () => setTimeout(hide, 200));
}

/* ── Toast helper ── */
function showToast(message) {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3000);
}

/* ── Build paper card HTML ── */
function buildPaperCard(paper) {
  const tagClass = paper.exam_type === 'MidSem' ? 'mid' : (paper.exam_type === 'EndSem' ? 'end' : 'supplementary');
  const tagLabel = paper.exam_type === 'MidSem' ? 'Mid Semester'
    : paper.exam_type === 'EndSem' ? 'End Semester'
    : (paper.exam_type || 'Unknown');

  const downloadUrl = API.getDownloadUrl(paper.paper_id);

  return `
    <div class="paper-card">
      <div class="paper-card-top">
        <span class="paper-tag ${tagClass}">${tagLabel}</span>
        <span class="paper-year">${paper.academic_year || ''}</span>
      </div>
      <div class="paper-title">${paper.subject_name || paper.subject_code}</div>
      <div>
        <div class="paper-subject">${paper.subject_name || ''}</div>
        <div class="paper-code">${paper.subject_code || ''}</div>
      </div>
      <div class="paper-meta">
        ${paper.department ? `<span class="meta-chip">${paper.department}</span>` : ''}
        ${paper.semester ? `<span class="meta-chip">Sem ${paper.semester}</span>` : ''}
        ${paper.max_marks ? `<span class="meta-chip">${paper.max_marks} marks</span>` : ''}
      </div>
      <button class="btn-view-pdf" onclick="window.open('${downloadUrl}', '_blank')">
        <svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
        View PDF
      </button>
    </div>`;
}

/* ============================================================
   NAV TAB SWITCHING
   ============================================================ */
function initNavTabs() {
  const tabs = document.querySelectorAll('.nav-tab');
  if (!tabs.length) return;

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const panel = document.getElementById('tab-' + tab.dataset.tab);
      if (panel) panel.classList.add('active');
    });
  });
}

/* ============================================================
   POPULATE FILTER DROPDOWNS (shared across tabs)
   ============================================================ */
let cachedFilters = null;

async function loadFilters() {
  if (cachedFilters) return cachedFilters;
  try {
    cachedFilters = await API.getFilters();
  } catch (e) {
    console.error('Failed to load filters:', e);
    cachedFilters = { branches: [], semesters: [], academic_years: [], exam_types: [], subjects: [] };
  }
  return cachedFilters;
}

function populateSelect(selectEl, options, labelFn) {
  if (!selectEl) return;
  // Keep the first "All..." option, clear the rest
  const firstOpt = selectEl.options[0];
  selectEl.innerHTML = '';
  selectEl.appendChild(firstOpt);
  options.forEach(opt => {
    const el = document.createElement('option');
    if (typeof opt === 'object') {
      el.value = opt.value;
      el.textContent = opt.label;
    } else {
      el.value = opt;
      el.textContent = labelFn ? labelFn(opt) : opt;
    }
    selectEl.appendChild(el);
  });
}

/* ============================================================
   QUESTION BANK (student.html — tab 2)
   ============================================================ */
function initQuestionBank() {
  const searchInput   = document.getElementById('qb-search-input');
  const filterBranch  = document.getElementById('qb-filter-branch');
  const filterSubject = document.getElementById('qb-filter-subject');
  const btnReset      = document.getElementById('qb-btn-reset');
  const resultsDiv    = document.getElementById('qb-results');
  const resultsHeader = document.getElementById('qb-results-header');
  const resultsCount  = document.getElementById('qb-results-count');
  const welcomeState  = document.getElementById('qb-welcome');
  const noResults     = document.getElementById('qb-no-results');

  if (!searchInput) return;

  loadFilters().then(f => {
    populateSelect(filterBranch, f.branches);
    populateSelect(filterSubject, f.subjects.map(s => ({
      value: s.code, label: `${s.name} (${s.code})`
    })));
  });

  let timeout = null;
  function trigger() { clearTimeout(timeout); timeout = setTimeout(runSearch, 300); }

  searchInput.addEventListener('input', trigger);
  filterBranch.addEventListener('change', trigger);
  filterSubject.addEventListener('change', trigger);

  btnReset.addEventListener('click', () => {
    searchInput.value = '';
    filterBranch.value = '';
    filterSubject.value = '';
    resultsDiv.innerHTML = '';
    resultsHeader.classList.add('hidden');
    noResults.classList.remove('visible');
    welcomeState.classList.add('visible');
  });

  async function runSearch() {
    const query = searchInput.value.toLowerCase().trim();
    const branch = filterBranch.value;
    const subjectCode = filterSubject.value;

    if (!query && !branch && !subjectCode) {
      resultsDiv.innerHTML = '';
      resultsHeader.classList.add('hidden');
      noResults.classList.remove('visible');
      welcomeState.classList.add('visible');
      return;
    }

    welcomeState.classList.remove('visible');

    let allQuestions = [];

    // Try semantic search first if there's a text query
    if (query) {
      const semanticData = await API.semanticSearch(query, {
        department: branch,
        subject_name: subjectCode ? undefined : undefined,
        top_k: 30
      });

      if (semanticData && semanticData.results && semanticData.results.length > 0) {
        allQuestions = semanticData.results.map(r => {
          // Extract question text from embedding document
          let text = r.text;
          const qMatch = text.match(/Question:\s*(.+?)\.\s*Concepts:/);
          if (qMatch) text = qMatch[1];
          return {
            question_text: text,
            similarity: r.similarity,
            marks: null,
            unit: r.unit,
            department: r.department,
            academic_year: r.academic_year,
            subject_name: r.subject_name,
            subject_code: '',
            exam_type: r.exam_type,
          };
        });
      }
    }

    // Fallback to keyword search if semantic returned nothing or no query
    if (allQuestions.length === 0) {
      const data = await API.searchQuestions({
        search: query, branch, subject_code: subjectCode, limit: 50
      });
      allQuestions = (data.questions || []).map(q => ({
        ...q,
        question_text: q.question_text?.value || q.question_text || '',
      }));
    }

    if (allQuestions.length === 0) {
      resultsDiv.innerHTML = '';
      resultsHeader.classList.add('hidden');
      noResults.classList.add('visible');
      return;
    }

    noResults.classList.remove('visible');
    resultsHeader.classList.remove('hidden');
    resultsCount.textContent = `${allQuestions.length} question${allQuestions.length !== 1 ? 's' : ''} found`;

    resultsDiv.innerHTML = allQuestions.map(q => {
      const text = typeof q.question_text === 'string' ? q.question_text : (q.question_text?.value || '');
      const pct = q.similarity ? Math.round(q.similarity * 100) : null;
      return `
      <div class="question-card">
        <div class="q-text">${text}</div>
        <div class="q-meta">
          ${pct ? `<span class="similarity-badge">${pct}% match</span>` : ''}
          ${q.marks ? `<span class="q-concept">${q.marks} marks</span>` : ''}
          ${q.unit ? `<span class="meta-chip">${q.unit}</span>` : ''}
          ${q.department ? `<span class="meta-chip">${q.department}</span>` : ''}
          ${q.academic_year ? `<span class="meta-chip">${q.academic_year}</span>` : ''}
          <span class="q-source">From: <strong>${q.subject_name}</strong> (${q.subject_code}) — ${q.exam_type}</span>
        </div>
      </div>`;
    }).join('');
  }
}

/* ============================================================
   FREQUENTLY ASKED (student.html — tab 3)
   ============================================================ */
function initFrequentlyAsked() {
  const searchInput   = document.getElementById('fa-search-input');
  const filterBranch  = document.getElementById('fa-filter-branch');
  const filterSubject = document.getElementById('fa-filter-subject');
  const btnReset      = document.getElementById('fa-btn-reset');
  const resultsDiv    = document.getElementById('fa-results');
  const resultsHeader = document.getElementById('fa-results-header');
  const resultsCount  = document.getElementById('fa-results-count');
  const emptyState    = document.getElementById('fa-empty');

  if (!searchInput) return;

  loadFilters().then(f => {
    populateSelect(filterBranch, f.branches);
    populateSelect(filterSubject, f.subjects.map(s => ({
      value: s.code, label: `${s.name} (${s.code})`
    })));
  });

  let timeout = null;
  function trigger() { clearTimeout(timeout); timeout = setTimeout(loadFrequent, 300); }

  searchInput.addEventListener('input', trigger);
  filterBranch.addEventListener('change', trigger);
  filterSubject.addEventListener('change', trigger);

  btnReset.addEventListener('click', () => {
    searchInput.value = '';
    filterBranch.value = '';
    filterSubject.value = '';
    loadFrequent();
  });

  async function loadFrequent() {
    const query = searchInput.value.toLowerCase().trim();
    const branch = filterBranch.value;
    const subjectCode = filterSubject.value;

    let subjectName = '';
    if (subjectCode) {
      const opt = filterSubject.querySelector(`option[value="${subjectCode}"]`);
      if (opt) {
        const m = opt.textContent.match(/^(.+?)\s*\(/);
        if (m) subjectName = m[1].trim();
      }
    }

    const topicData = await API.getTopicClusters({
      subject_name: subjectName,
      department: !subjectName ? branch : '',
    });

    let topics = topicData?.topics || [];

    if (query && topics.length > 0) {
      topics = topics.filter(t =>
        t.topic_label.toLowerCase().includes(query) ||
        t.questions.some(q => q.text.toLowerCase().includes(query))
      );
    }

    if (topics.length === 0) {
      const data = await API.getRepeatedQuestions({
        branch, subject_code: subjectCode, search: query
      });
      const repeated = data.repeated || [];

      if (repeated.length === 0) {
        resultsDiv.innerHTML = '';
        resultsHeader.classList.add('hidden');
        emptyState.classList.add('visible');
        emptyState.querySelector('h3').textContent = 'No Frequently Asked Questions Found';
        emptyState.querySelector('p').textContent = 'Try adjusting your filters or search terms.';
        return;
      }

      emptyState.classList.remove('visible');
      resultsHeader.classList.remove('hidden');
      const totalQ = repeated.reduce((sum, g) => sum + g.instances.length, 0);
      resultsCount.textContent = `${repeated.length} recurring topic${repeated.length !== 1 ? 's' : ''} · ${totalQ} appearances`;

      resultsDiv.innerHTML = repeated.map(group => {
        const text = group.question_text?.value || group.question_text || '';
        return `
        <div class="question-card">
          <div class="q-meta" style="margin-bottom:12px;">
            <span class="freq-badge">
              <svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
              Appears in ${group.paper_count} papers
            </span>
          </div>
          <div class="q-text" style="margin-bottom:12px;font-weight:500;">${text}</div>
          ${group.instances.map(inst => `
            <div style="padding:8px 0;border-top:1px solid var(--gray-100);">
              <span class="q-source">
                ${inst.department ? `<span class="meta-chip">${inst.department}</span>` : ''}
                ${inst.academic_year ? `<span class="meta-chip">${inst.academic_year}</span>` : ''}
                <strong>${inst.subject_name}</strong> (${inst.subject_code}) — ${inst.exam_type}
              </span>
            </div>`).join('')}
        </div>`;
      }).join('');
      return;
    }

    emptyState.classList.remove('visible');
    resultsHeader.classList.remove('hidden');
    resultsCount.textContent = `${topics.length} recurring topic${topics.length !== 1 ? 's' : ''} · ${topicData.total_appearances} appearances`;

    resultsDiv.innerHTML = topics.map(topic => `
      <div class="question-card">
        <div class="q-meta" style="margin-bottom:12px;">
          <span class="freq-badge">
            <svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            ${topic.count} similar questions across papers
          </span>
        </div>
        <div class="q-text" style="margin-bottom:12px;font-weight:500;">${topic.topic_label}</div>
        ${topic.questions.map(q => `
          <div style="padding:8px 0;border-top:1px solid var(--gray-100);">
            <div style="color:var(--gray-600);font-size:0.9rem;margin-bottom:4px;">${q.text}</div>
            <span class="q-source">
              ${q.department ? `<span class="meta-chip">${q.department}</span>` : ''}
              ${q.academic_year ? `<span class="meta-chip">${q.academic_year}</span>` : ''}
              <strong>${q.subject_name}</strong> — ${q.exam_type}
            </span>
          </div>`).join('')}
      </div>`).join('');
  }

  loadFrequent();
}

/* ============================================================
   RELATED QUESTIONS (student.html — tab 4)
   ============================================================ */
function initRelatedQuestions() {
  const searchInput   = document.getElementById('rq-search-input');
  const filterBranch  = document.getElementById('rq-filter-branch');
  const btnReset      = document.getElementById('rq-btn-reset');
  const resultsDiv    = document.getElementById('rq-results');
  const resultsHeader = document.getElementById('rq-results-header');
  const resultsCount  = document.getElementById('rq-results-count');
  const welcomeState  = document.getElementById('rq-welcome');
  const noResults     = document.getElementById('rq-no-results');

  if (!searchInput) return;

  loadFilters().then(f => {
    populateSelect(filterBranch, f.branches);
  });

  let timeout = null;
  function trigger() { clearTimeout(timeout); timeout = setTimeout(runSearch, 300); }

  searchInput.addEventListener('input', trigger);
  filterBranch.addEventListener('change', trigger);

  btnReset.addEventListener('click', () => {
    searchInput.value = '';
    filterBranch.value = '';
    resultsDiv.innerHTML = '';
    resultsHeader.classList.add('hidden');
    noResults.classList.remove('visible');
    welcomeState.classList.add('visible');
  });

  function getWords(text) {
    return text.toLowerCase().replace(/[^a-z0-9\s]/g, '').split(/\s+/).filter(w => w.length > 2);
  }

  function similarity(wordsA, wordsB) {
    const setB = new Set(wordsB);
    const matches = wordsA.filter(w => setB.has(w)).length;
    if (wordsA.length === 0 || wordsB.length === 0) return 0;
    return matches / Math.max(wordsA.length, wordsB.length);
  }

  async function runSearch() {
    const query = searchInput.value.trim();
    const branch = filterBranch.value;

    if (!query) {
      resultsDiv.innerHTML = '';
      resultsHeader.classList.add('hidden');
      noResults.classList.remove('visible');
      welcomeState.classList.add('visible');
      return;
    }

    welcomeState.classList.remove('visible');

    const semanticData = await API.semanticSearch(query, {
      department: branch, top_k: 20
    });

    let scored = [];

    if (semanticData && semanticData.results && semanticData.results.length > 0) {
      scored = semanticData.results.map(r => ({
        text: r.text,
        score: r.similarity,
        department: r.department,
        academic_year: r.academic_year,
        subject_name: r.subject_name,
        exam_type: r.exam_type,
        paper_id: r.paper_id,
      }));
    } else {
      const queryWords = getWords(query);
      const data = await API.searchQuestions({ search: query, branch, limit: 100 });
      const allQ = data.questions || [];

      allQ.forEach(q => {
        const text = q.question_text?.value || q.question_text || '';
        const qWords = getWords(text);
        const score = similarity(queryWords, qWords);
        if (score > 0.1) {
          scored.push({
            text,
            score,
            department: q.department,
            academic_year: q.academic_year,
            subject_name: q.subject_name,
            subject_code: q.subject_code,
            exam_type: q.exam_type,
          });
        }
      });

      scored.sort((a, b) => b.score - a.score);
    }

    if (scored.length === 0) {
      resultsDiv.innerHTML = '';
      resultsHeader.classList.add('hidden');
      noResults.classList.add('visible');
      return;
    }

    noResults.classList.remove('visible');
    resultsHeader.classList.remove('hidden');
    resultsCount.textContent = `${scored.length} related question${scored.length !== 1 ? 's' : ''} found`;

    resultsDiv.innerHTML = scored.map(q => {
      const pct = Math.round(q.score * 100);
      let displayText = q.text;
      const qMatch = displayText.match(/Question:\s*(.+?)\.\s*Concepts:/);
      if (qMatch) displayText = qMatch[1];

      return `
        <div class="question-card">
          <div class="q-text">${displayText}</div>
          <div class="q-meta">
            <span class="similarity-badge">${pct}% match</span>
            ${q.department ? `<span class="meta-chip">${q.department}</span>` : ''}
            ${q.academic_year ? `<span class="meta-chip">${q.academic_year}</span>` : ''}
            <span class="q-source">From: <strong>${q.subject_name || ''}</strong> — ${q.exam_type || ''}</span>
          </div>
        </div>`;
    }).join('');
  }
}

/* ============================================================
   STUDENT DASHBOARD (student.html — tab 1)
   ============================================================ */
function initStudentDashboard() {
  if (!document.getElementById('papers-grid')) return;

  const searchInput   = document.getElementById('search-input');
  const filterBranch  = document.getElementById('filter-branch');
  const filterYear    = document.getElementById('filter-year');
  const filterSem     = document.getElementById('filter-semester');
  const filterSubject = document.getElementById('filter-subject');
  const filterExam    = document.getElementById('filter-exam');
  const btnReset      = document.getElementById('btn-reset');
  const papersGrid    = document.getElementById('papers-grid');
  const resultsHeader = document.getElementById('results-header');
  const resultsCount  = document.getElementById('results-count');
  const welcomeState  = document.getElementById('welcome-state');
  const noResults     = document.getElementById('no-results');

  let searchTimeout = null;

  /* Load stats */
  API.getStats().then(stats => {
    document.getElementById('stat-total-papers').textContent  = stats.totalPapers;
    document.getElementById('stat-subjects').textContent       = stats.subjectsCovered;
    document.getElementById('stat-trending').textContent       = stats.trendingTopic;
    document.getElementById('stat-this-year').textContent      = stats.addedThisYear;
  }).catch(() => {});

  /* Populate filter dropdowns dynamically from DB */
  loadFilters().then(f => {
    populateSelect(filterBranch, f.branches);
    populateSelect(filterYear, f.academic_years);
    populateSelect(filterSem, f.semesters, s => `Semester ${s}`);
    populateSelect(filterSubject, f.subjects.map(s => ({
      value: s.code, label: `${s.name} (${s.code})`
    })));
    populateSelect(filterExam, f.exam_types);
  });

  /* Trigger search on any change */
  function triggerSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(runSearch, 300);
  }

  initAutocomplete(searchInput, triggerSearch);
  searchInput.addEventListener('input', triggerSearch);
  filterBranch.addEventListener('change', triggerSearch);
  filterYear.addEventListener('change', triggerSearch);
  filterSem.addEventListener('change', triggerSearch);
  filterSubject.addEventListener('change', triggerSearch);
  filterExam.addEventListener('change', triggerSearch);

  btnReset.addEventListener('click', () => {
    searchInput.value = '';
    filterBranch.value  = '';
    filterYear.value    = '';
    filterSem.value     = '';
    filterSubject.value = '';
    filterExam.value    = '';
    showWelcome();
  });

  function showWelcome() {
    papersGrid.innerHTML    = '';
    resultsHeader.classList.add('hidden');
    noResults.classList.remove('visible');
    welcomeState.classList.add('visible');
  }

  async function runSearch() {
    const hasFilter = searchInput.value.trim() ||
      filterBranch.value || filterYear.value || filterSem.value ||
      filterSubject.value || filterExam.value;

    if (!hasFilter) { showWelcome(); return; }

    const papers = await API.search({
      q:              searchInput.value,
      branch:         filterBranch.value,
      academic_year:  filterYear.value,
      semester:       filterSem.value,
      subject_code:   filterSubject.value,
      examType:       filterExam.value,
    });

    welcomeState.classList.remove('visible');

    if (papers.length === 0) {
      papersGrid.innerHTML = '';
      resultsHeader.classList.add('hidden');
      noResults.classList.add('visible');
      return;
    }

    noResults.classList.remove('visible');
    resultsHeader.classList.remove('hidden');
    resultsCount.textContent = `${papers.length} paper${papers.length !== 1 ? 's' : ''} found`;
    papersGrid.innerHTML = papers.map(buildPaperCard).join('');
  }

  showWelcome();
}

/* ============================================================
   LIBRARIAN DASHBOARD (librarian.html)
   ============================================================ */
function initLibrarianDashboard() {
  if (!document.getElementById('manage-table-body')) return;

  function refreshStats() {
    API.getStats().then(stats => {
      const el = (id) => document.getElementById(id);
      if (el('admin-total-papers'))  el('admin-total-papers').textContent  = stats.totalPapers;
      if (el('admin-total-users'))   el('admin-total-users').textContent   = '—';
      if (el('admin-users-online'))  el('admin-users-online').textContent  = '—';
      if (el('admin-pending'))       el('admin-pending').textContent       = '0';
      if (el('admin-ai-processed'))  el('admin-ai-processed').textContent  = stats.totalPapers;
    }).catch(() => {});
  }
  refreshStats();

  loadFilters().then(f => {
    const sel = document.getElementById('upload-subject');
    if (!sel) return;
    f.subjects.forEach(sub => {
      const opt = document.createElement('option');
      opt.value = sub.code;
      opt.textContent = `${sub.name} (${sub.code})`;
      sel.appendChild(opt);
    });
  });

  // Load all papers into manage table
  function loadManageTable() {
    fetch(`${API_BASE}/librarian/papers?limit=100`).then(r => r.json()).then(data => {
      const tbody = document.getElementById('manage-table-body');
      if (!tbody) return;
      tbody.innerHTML = (data.papers || []).map(paper => {
        let uploadDate = '';
        if (paper.created_at) {
          const d = new Date(paper.created_at);
          uploadDate = d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
            + ' ' + d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
        }
        return `
        <tr id="row-${paper.paper_id}">
          <td><code style="font-size:0.78rem;color:var(--text-muted)">${paper.paper_id}</code></td>
          <td>
            <div style="font-weight:600;font-size:0.88rem">${paper.subject_name || ''}</div>
            <div style="font-size:0.74rem;color:var(--text-muted)">${paper.subject_code || ''}</div>
          </td>
          <td>${paper.academic_year || ''}</td>
          <td>${paper.exam_type || ''}</td>
          <td style="font-size:0.78rem;color:var(--text-muted);white-space:nowrap;">${uploadDate}</td>
          <td><span class="status-badge approved">Processed</span></td>
          <td>
            <div class="action-btns">
              <button class="btn-action delete" onclick="deletePaper('${paper.paper_id}')">Delete</button>
            </div>
          </td>
        </tr>`;
      }).join('');

      // Update analytics cards
      const totalEl = document.getElementById('stat-total-papers');
      if (totalEl) totalEl.textContent = data.total || 0;
    }).catch(() => {});
  }
  loadManageTable();

  const uploadForm = document.getElementById('upload-form');
  if (uploadForm) {
    uploadForm.addEventListener('submit', async e => {
      e.preventDefault();

      const fileInput = document.getElementById('pdf-file-input');
      if (!fileInput || !fileInput.files.length) {
        showToast('Please select a file first.');
        return;
      }

      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append('file', file);

      // Disable submit button while uploading
      const submitBtn = uploadForm.querySelector('button[type="submit"]');
      const originalText = submitBtn.textContent;
      submitBtn.disabled = true;
      submitBtn.textContent = 'Uploading...';

      try {
        const resp = await fetch(`${API_BASE}/upload`, {
          method: 'POST',
          body: formData,
        });

        if (!resp.ok) {
          const err = await resp.json();
          showToast(`Upload failed: ${err.detail || 'Unknown error'}`);
          return;
        }

        const result = await resp.json();
        if (result.status === 'reupload') {
          const when = result.previously_uploaded_at
            ? new Date(result.previously_uploaded_at).toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' })
            : 'earlier';
          showToast(`"${result.paper_id}" was already uploaded on ${when}. Re-processing with updated file.`);
        } else {
          showToast(`Uploading "${file.name}"...`);
        }
        uploadForm.reset();

        // Reset file drop area text
        const fileArea = document.getElementById('file-drop-area');
        if (fileArea) {
          const p = fileArea.querySelector('p');
          if (p) p.innerHTML = '<strong>Click to upload</strong> or drag and drop &nbsp;·&nbsp; <span>PDF / DOCX · Max 20 MB</span>';
        }

        // Poll job progress
        const jobId = result.job_id;
        if (jobId) {
          submitBtn.textContent = 'Processing... 0%';
          submitBtn.disabled = true;

          const pollJob = setInterval(async () => {
            try {
              // FIXED: Corrected the endpoint from /job to /jobs
              const jobResp = await fetch(`${API_BASE}/jobs/${jobId}`);
              if (!jobResp.ok) { clearInterval(pollJob); return; }
              const responseData = await jobResp.json();
              const job = responseData.data; // Added .data because of the way routes/jobs.py sends it back

              submitBtn.textContent = `${job.message} ${job.progress}%`;

              if (job.status === 'completed') {
                clearInterval(pollJob);
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
                showToast(`Paper processed successfully!`);
                loadManageTable();
                refreshStats();
              } else if (job.status === 'failed') {
                clearInterval(pollJob);
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
                showToast(`Processing failed: ${job.message}`);
              }
            } catch {
              // Network error, keep polling
            }
          }, 1500);

          // Safety: stop polling after 2 minutes
          setTimeout(() => {
            clearInterval(pollJob);
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
            loadManageTable();
            refreshStats();
          }, 120000);
        }
      } catch (err) {
        showToast('Upload failed: Network error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
      }
    });
  }

  const fileArea = document.getElementById('file-drop-area');
  const fileInput = document.getElementById('pdf-file-input');
  if (fileArea && fileInput) {
    fileArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) {
        fileArea.querySelector('p').textContent = fileInput.files[0].name;
        showToast('PDF selected: ' + fileInput.files[0].name);
      }
    });
  }
}

/* Table action handlers (librarian) */
function editPaper(id) {
  showToast(`Edit functionality — Paper ${id} (connect to backend).`);
}

function deletePaper(id) {
  if (!confirm(`Delete paper ${id}? This removes all questions and metadata.`)) return;
  const row = document.getElementById(`row-${id}`);
  if (row) row.style.opacity = '0.4';

  fetch(`${API_BASE}/paper/${id}`, { method: 'DELETE' })
    .then(r => {
      if (!r.ok) throw new Error('Delete failed');
      return r.json();
    })
    .then(() => {
      if (row) row.remove();
      showToast(`Paper ${id} deleted.`);
    })
    .catch(() => {
      if (row) row.style.opacity = '1';
      showToast(`Failed to delete ${id}.`);
    });
}

/* ============================================================
   LOGIN PAGE (login.html)
   ============================================================ */
function initLoginPage() {
  const loginForm = document.getElementById('login-form');
  if (!loginForm) return;

  const roleTabs = document.querySelectorAll('.role-tab');
  let selectedRole = 'student';

  roleTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      roleTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      selectedRole = tab.dataset.role;
    });
  });

  loginForm.addEventListener('submit', e => {
    e.preventDefault();
    const email    = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value.trim();

    if (!email || !password) {
      showToast('Please enter your email and password.');
      return;
    }

    if (selectedRole === 'student') {
      window.location.href = 'student.html';
    } else {
      window.location.href = 'librarian.html';
    }
  });
}

/* ── Utility ── */
function capitalise(str) { return str.charAt(0).toUpperCase() + str.slice(1); }

function logout() {
  window.location.href = 'login.html';
}

/* ── Init on load ── */
document.addEventListener('DOMContentLoaded', () => {
  initLoginPage();
  initNavTabs();
  initStudentDashboard();
  initQuestionBank();
  initFrequentlyAsked();
  initRelatedQuestions();
  initLibrarianDashboard();
});