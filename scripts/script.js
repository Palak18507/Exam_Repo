/*********************************
 * MOCK DATABASE (temporary)
 * Later this will come from backend APIs
 *********************************/

const mockDatabase = {
  subjects: [
    { id: 1, name: "Data Structures", code: "CS201", branch: "CSE", year: 2, semester: 3 },
    { id: 2, name: "Operating Systems", code: "CS302", branch: "CSE", year: 3, semester: 5 },
    { id: 3, name: "Database Management Systems", code: "CS202", branch: "CSE", year: 2, semester: 4 },
    { id: 4, name: "Computer Networks", code: "CS301", branch: "CSE", year: 2, semester: 4 }
  ],

  papers: [
    {
      id: 1,
      subjectId: 1,
      title: "Mid Semester Exam 2023",
      examType: "MID",
      year: 2023,
      pdfUrl: "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
      questions: [
        { id: "Q1", text: "Explain linked lists", concept: "Linked Lists", page: 1 }
      ]
    },
    {
      id: 2,
      subjectId: 1,
      title: "End Semester Exam 2023",
      examType: "END",
      year: 2023,
      pdfUrl: "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
      questions: [
        { id: "Q1", text: "Explain trees", concept: "Trees", page: 2 }
      ]
    },
    {
      id: 3,
      subjectId: 2,
      title: "End Semester Exam 2024",
      examType: "END",
      year: 2024,
      pdfUrl: "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
      questions: [
        { id: "Q1", text: "What is deadlock?", concept: "Deadlock", page: 1 }
      ]
    }
  ]
};


/*********************************
 * STATE
 *********************************/

let state = {
  branch: "",
  year: "",
  semester: "",
  subject: "",
  examType: "",
  searchQuery: ""
};


/*********************************
 * DOM ELEMENTS
 *********************************/

const branchFilter = document.getElementById("branchFilter");
const yearFilter = document.getElementById("yearFilter");
const semesterFilter = document.getElementById("semesterFilter");
const subjectFilter = document.getElementById("subjectFilter");
const examTypeFilter = document.getElementById("examTypeFilter");
const searchInput = document.getElementById("mainSearch");

const resultsSection = document.getElementById("resultsSection");
const papersGrid = document.getElementById("papersGrid");
const resultsCount = document.getElementById("resultsCount");
const welcomeState = document.getElementById("welcomeState");
const resetBtn = document.getElementById("resetFilters");


/*********************************
 * INITIALIZE
 *********************************/

document.addEventListener("DOMContentLoaded", () => {
  populateSubjects();
  attachEventListeners();
});


/*********************************
 * EVENT LISTENERS
 *********************************/

function attachEventListeners() {
  branchFilter.addEventListener("change", applyFilters);
  yearFilter.addEventListener("change", applyFilters);
  semesterFilter.addEventListener("change", applyFilters);
  subjectFilter.addEventListener("change", applyFilters);
  examTypeFilter.addEventListener("change", applyFilters);

  searchInput.addEventListener("input", () => {
    state.searchQuery = searchInput.value.trim();
    applyFilters();
  });

  resetBtn.addEventListener("click", resetFilters);
}


/*********************************
 * POPULATE SUBJECT DROPDOWN
 *********************************/

function populateSubjects() {
  subjectFilter.innerHTML = `<option value="">All Subjects</option>`;

  mockDatabase.subjects.forEach(subject => {
    const option = document.createElement("option");
    option.value = subject.id;
    option.textContent = `${subject.name} (${subject.code})`;
    subjectFilter.appendChild(option);
  });
}


/*********************************
 * CORE FILTER LOGIC
 *********************************/

function applyFilters() {
  state.branch = branchFilter.value;
  state.year = yearFilter.value;
  state.semester = semesterFilter.value;
  state.subject = subjectFilter.value;
  state.examType = examTypeFilter.value;

  let filtered = mockDatabase.papers.filter(paper => {
    const subject = mockDatabase.subjects.find(s => s.id === paper.subjectId);

    if (state.branch && subject.branch !== state.branch) return false;
    if (state.year && subject.year != state.year) return false;
    if (state.semester && subject.semester != state.semester) return false;
    if (state.subject && subject.id != state.subject) return false;
    if (state.examType && paper.examType !== state.examType) return false;

    if (state.searchQuery) {
      const q = state.searchQuery.toLowerCase();
      return (
        subject.name.toLowerCase().includes(q) ||
        subject.code.toLowerCase().includes(q) ||
        paper.title.toLowerCase().includes(q) ||
        paper.questions.some(ques =>
          ques.text.toLowerCase().includes(q) ||
          ques.concept.toLowerCase().includes(q)
        )
      );
    }

    return true;
  });

  if (filtered.length > 0) {
    renderResults(filtered);
  } else {
    showNoResults();
  }
}


/*********************************
 * RENDER RESULTS
 *********************************/

function renderResults(papers) {
  welcomeState.style.display = "none";
  resultsSection.style.display = "block";
  resultsCount.textContent = `${papers.length} paper(s) found`;

  papersGrid.innerHTML = papers.map(paper => {
    const subject = mockDatabase.subjects.find(s => s.id === paper.subjectId);

    return `
      <div class="paper-card">
        <h3>${paper.title}</h3>
        <p>${subject.name} (${subject.code})</p>
        <p>Year: ${paper.year} • ${paper.examType}</p>
        <button onclick="openPDF('${paper.pdfUrl}')">View PDF</button>
      </div>
    `;
  }).join("");
}


/*********************************
 * EMPTY STATE
 *********************************/

function showNoResults() {
  resultsSection.style.display = "block";
  welcomeState.style.display = "none";
  papersGrid.innerHTML = `<p style="text-align:center;">No papers found.</p>`;
  resultsCount.textContent = "";
}


/*********************************
 * RESET
 *********************************/

function resetFilters() {
  branchFilter.value = "";
  yearFilter.value = "";
  semesterFilter.value = "";
  subjectFilter.value = "";
  examTypeFilter.value = "";
  searchInput.value = "";

  state = {
    branch: "",
    year: "",
    semester: "",
    subject: "",
    examType: "",
    searchQuery: ""
  };

  resultsSection.style.display = "none";
  welcomeState.style.display = "block";
}


/*********************************
 * PDF VIEW
 *********************************/

function openPDF(url) {
  window.open(url, "_blank");
}
