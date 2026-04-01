# Firebase Authentication & Role-Based Access Control — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real Firebase authentication (signup + login) with email domain restriction (`@igdtuw.ac.in`) and role-based access control (student vs librarian), replacing the current mock login system.

**Architecture:** Firebase Auth handles signup/login. Firestore stores an `admins` collection listing librarian emails. On login, the app checks Firestore to determine the user's role. Student role can access `student.html` only. Librarian role can access both `student.html` and `librarian.html`. Route protection runs on every protected page load, redirecting unauthorized users to `login.html`.

**Tech Stack:** Firebase Auth (Email/Password), Cloud Firestore, Firebase JS SDK (v9+ modular), vanilla HTML/CSS/JS (existing stack)

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `firebase-config.js` | **Create** | Firebase SDK initialization, auth & Firestore exports |
| `auth.js` | **Create** | Signup, login, logout, email domain validation, role checking |
| `route-guard.js` | **Create** | Page-level access control — checks auth state + role on load, redirects if unauthorized |
| `login.html` | **Modify** | Add signup form/toggle, wire to Firebase auth, remove demo note, remove role tabs |
| `student.html` | **Modify** | Add Firebase SDK scripts, add route-guard, add "Switch to Librarian" button for admins |
| `librarian.html` | **Modify** | Add Firebase SDK scripts, add route-guard (librarian-only) |
| `index.html` | **Modify** | Add Firebase SDK scripts, show/hide Sign In vs dashboard link based on auth state |
| `script.js` | **Modify** | Update `logout()` to use Firebase signOut, update `initLoginPage()` removal |
| `styles.css` | **Modify** | Add styles for signup form toggle and auth error messages |

---

## Task 1: Firebase Project Setup (Manual — User Action)

This task is done in the Firebase Console, not in code.

- [ ] **Step 1: Create Firebase project**

Go to [Firebase Console](https://console.firebase.google.com/) → "Add project" → Name it `igdtuw-qp-archive` → Disable Google Analytics (not needed) → Create.

- [ ] **Step 2: Enable Email/Password authentication**

In Firebase Console → Build → Authentication → Sign-in method → Enable "Email/Password" → Save.

- [ ] **Step 3: Create Firestore database**

In Firebase Console → Build → Firestore Database → "Create database" → Start in **test mode** (we'll add rules later) → Select region `asia-south1` (Mumbai) → Create.

- [ ] **Step 4: Add the `admins` collection with your email**

In Firestore → "Start collection" → Collection ID: `admins` → Add first document:
- Document ID: (auto-generate)
- Field: `email` (string) → Value: `your-email@igdtuw.ac.in`

This makes your account a librarian. Add more librarian emails here later.

- [ ] **Step 5: Get Firebase config**

In Firebase Console → Project Settings (gear icon) → General → "Your apps" → Click web icon (`</>`) → Register app name `qp-archive-web` → Copy the `firebaseConfig` object. You'll paste it in the next task.

- [ ] **Step 6: Set Firestore security rules**

In Firebase Console → Firestore → Rules → Replace with:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Anyone authenticated can read admins list (needed for role check)
    match /admins/{doc} {
      allow read: if request.auth != null;
      allow write: if false; // Only editable via Firebase Console
    }
  }
}
```

Publish the rules.

---

## Task 2: Create `firebase-config.js`

**Files:**
- Create: `firebase-config.js`

- [ ] **Step 1: Create the Firebase config file**

```js
/* firebase-config.js
   Firebase SDK initialization — Auth + Firestore exports
   ──────────────────────────────────────────────────────── */

import { initializeApp } from 'https://www.gstatic.com/firebasejs/11.4.0/firebase-app.js';
import { getAuth }       from 'https://www.gstatic.com/firebasejs/11.4.0/firebase-auth.js';
import { getFirestore }  from 'https://www.gstatic.com/firebasejs/11.4.0/firebase-firestore.js';

const firebaseConfig = {
  apiKey:            "PASTE_YOUR_API_KEY",
  authDomain:        "PASTE_YOUR_AUTH_DOMAIN",
  projectId:         "PASTE_YOUR_PROJECT_ID",
  storageBucket:     "PASTE_YOUR_STORAGE_BUCKET",
  messagingSenderId: "PASTE_YOUR_SENDER_ID",
  appId:             "PASTE_YOUR_APP_ID"
};

const app  = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db   = getFirestore(app);

export { auth, db };
```

> **User action:** Replace the placeholder values with the config copied from Firebase Console in Task 1 Step 5.

- [ ] **Step 2: Verify file created at `d:\librayrepoUI\firebase-config.js`**

---

## Task 3: Create `auth.js`

**Files:**
- Create: `auth.js`

- [ ] **Step 1: Create the auth module**

```js
/* auth.js
   Signup, login, logout, email validation, role checking
   ─────────────────────────────────────────────────────── */

import { auth, db } from './firebase-config.js';
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  sendPasswordResetEmail
} from 'https://www.gstatic.com/firebasejs/11.4.0/firebase-auth.js';
import {
  collection, query, where, getDocs
} from 'https://www.gstatic.com/firebasejs/11.4.0/firebase-firestore.js';

/* ── Allowed email domain ── */
const ALLOWED_DOMAIN = 'igdtuw.ac.in';

function isAllowedEmail(email) {
  if (!email) return false;
  const domain = email.split('@')[1];
  return domain && domain.toLowerCase() === ALLOWED_DOMAIN;
}

/* ── Check if user is a librarian (admin) ── */
async function checkIsLibrarian(email) {
  const adminsRef = collection(db, 'admins');
  const q = query(adminsRef, where('email', '==', email.toLowerCase()));
  const snapshot = await getDocs(q);
  return !snapshot.empty;
}

/* ── Sign Up ── */
async function signup(email, password) {
  email = email.trim().toLowerCase();

  if (!isAllowedEmail(email)) {
    throw new Error(`Only @${ALLOWED_DOMAIN} email addresses are allowed to sign up.`);
  }
  if (password.length < 6) {
    throw new Error('Password must be at least 6 characters.');
  }

  const userCredential = await createUserWithEmailAndPassword(auth, email, password);
  return userCredential.user;
}

/* ── Login ── */
async function login(email, password) {
  email = email.trim().toLowerCase();

  if (!email || !password) {
    throw new Error('Please enter your email and password.');
  }

  const userCredential = await signInWithEmailAndPassword(auth, email, password);
  const user = userCredential.user;

  /* Determine role and redirect */
  const isLibrarian = await checkIsLibrarian(user.email);
  const role = isLibrarian ? 'librarian' : 'student';

  sessionStorage.setItem('userRole', role);
  sessionStorage.setItem('userEmail', user.email);

  return { user, role };
}

/* ── Logout ── */
async function logoutUser() {
  await signOut(auth);
  sessionStorage.removeItem('userRole');
  sessionStorage.removeItem('userEmail');
  window.location.href = 'login.html';
}

/* ── Password Reset ── */
async function resetPassword(email) {
  email = email.trim().toLowerCase();
  if (!email) {
    throw new Error('Please enter your email address.');
  }
  await sendPasswordResetEmail(auth, email);
}

/* ── Auth State Observer ── */
function onAuthChange(callback) {
  return onAuthStateChanged(auth, callback);
}

export { signup, login, logoutUser, resetPassword, onAuthChange, checkIsLibrarian, isAllowedEmail };
```

- [ ] **Step 2: Verify file created at `d:\librayrepoUI\auth.js`**

---

## Task 4: Create `route-guard.js`

**Files:**
- Create: `route-guard.js`

- [ ] **Step 1: Create the route guard module**

```js
/* route-guard.js
   Page-level access control — runs on protected page load
   ──────────────────────────────────────────────────────── */

import { auth } from './firebase-config.js';
import { onAuthStateChanged } from 'https://www.gstatic.com/firebasejs/11.4.0/firebase-auth.js';
import { checkIsLibrarian } from './auth.js';

/**
 * Guard a page. Call at the top of any protected page.
 * @param {'student'|'librarian'} requiredRole — minimum role needed
 */
function guardPage(requiredRole) {
  onAuthStateChanged(auth, async (user) => {
    if (!user) {
      /* Not logged in → redirect to login */
      window.location.href = 'login.html';
      return;
    }

    const isLibrarian = await checkIsLibrarian(user.email);
    const userRole = isLibrarian ? 'librarian' : 'student';

    /* Update session storage (keeps it fresh) */
    sessionStorage.setItem('userRole', userRole);
    sessionStorage.setItem('userEmail', user.email);

    if (requiredRole === 'librarian' && !isLibrarian) {
      /* Student trying to access librarian page → redirect to student */
      window.location.href = 'student.html';
      return;
    }

    /* Access granted — show the page (it starts hidden) */
    document.body.classList.add('auth-ready');

    /* If user is librarian on student page, show the "Switch to Librarian Dashboard" button */
    if (isLibrarian && requiredRole === 'student') {
      const switchBtn = document.getElementById('btn-switch-to-librarian');
      if (switchBtn) switchBtn.classList.remove('hidden');
    }
  });
}

export { guardPage };
```

- [ ] **Step 2: Verify file created at `d:\librayrepoUI\route-guard.js`**

---

## Task 5: Modify `script.js` — Remove Old Login & Logout Logic

> **IMPORTANT:** This task MUST be done before modifying `student.html` or `librarian.html` (Tasks 7 & 8), because those pages still load `script.js` and the old global `logout()` function would conflict with the Firebase-based logout.

**Files:**
- Modify: `script.js`

- [ ] **Step 1: Remove `initLoginPage()` function**

Delete the entire `initLoginPage()` function (the block starting with `function initLoginPage()` and ending with its closing `}`). This logic is now handled by the module in `login.html`.

- [ ] **Step 2: Remove `initLoginPage()` call from DOMContentLoaded**

In the `DOMContentLoaded` listener, remove the `initLoginPage();` line.

- [ ] **Step 3: Remove the old `logout()` function**

Delete the `function logout()` block (the one that does `window.location.href = 'login.html'`). Logout is now handled by `auth.js` and imported as a module on each page.

---

## Task 6: Modify `login.html` — Real Auth Forms

**Files:**
- Modify: `login.html`

- [ ] **Step 1: Replace the role tabs with a Login/Signup toggle**

Replace the `<div class="role-tabs">` block (containing the Student/Librarian role buttons) with:

```html
<!-- Auth mode toggle -->
<div class="role-tabs">
  <button class="role-tab active" id="tab-login" onclick="showLoginMode()">Sign In</button>
  <button class="role-tab" id="tab-signup" onclick="showSignupMode()">Sign Up</button>
</div>
```

- [ ] **Step 2: Replace the login form with dual-mode form**

Replace the entire `<form id="login-form">` block (including the Remember me / Forgot password row) with:

```html
<!-- Auth error message -->
<div id="auth-error" class="auth-error hidden"></div>

<!-- Login form -->
<form id="login-form" novalidate>
  <div class="form-group">
    <label for="email">Institutional Email</label>
    <input
      type="email"
      id="email"
      class="form-control"
      placeholder="your.name@igdtuw.ac.in"
      autocomplete="email"
      required
    />
  </div>

  <div class="form-group">
    <label for="password">Password</label>
    <input
      type="password"
      id="password"
      class="form-control"
      placeholder="Enter your password"
      autocomplete="current-password"
      required
    />
  </div>

  <!-- Confirm password (signup only) -->
  <div class="form-group hidden" id="confirm-password-group">
    <label for="confirm-password">Confirm Password</label>
    <input
      type="password"
      id="confirm-password"
      class="form-control"
      placeholder="Re-enter your password"
      autocomplete="new-password"
    />
  </div>

  <div id="login-extras" style="display:flex;justify-content:flex-end;align-items:center;margin-bottom:20px;margin-top:-8px;">
    <a href="#" id="forgot-password-link" style="font-size:0.8rem;color:var(--green);">Forgot password?</a>
  </div>

  <button type="submit" class="btn-login" id="auth-submit-btn">Sign In to Archive</button>
</form>
```

- [ ] **Step 3: Replace the demo note and update the restricted access note**

Remove the "Access is restricted" div (the one mentioning "currently enrolled students and authorised staff") — this info is now redundant since we enforce it at signup.

Replace the demo helper note div (the one containing `<strong>Demo:</strong>`) with:

```html
<div style="margin-top:14px;background:var(--green-tint);border-radius:var(--r-sm);padding:12px 14px;font-size:0.8rem;color:var(--green);">
  <strong>Note:</strong> Only <code>@igdtuw.ac.in</code> email addresses can sign up. Your role (student or librarian) is assigned automatically.
</div>
```

- [ ] **Step 4: Add Firebase SDK script tags and auth module**

Before the closing `</body>` tag, replace the existing script tag with:

```html
<script type="module">
  import { login, signup, resetPassword, onAuthChange, checkIsLibrarian } from './auth.js';

  let isSignupMode = false;

  /* Toggle between login and signup */
  window.showLoginMode = function() {
    isSignupMode = false;
    document.getElementById('tab-login').classList.add('active');
    document.getElementById('tab-signup').classList.remove('active');
    document.getElementById('confirm-password-group').classList.add('hidden');
    document.getElementById('login-extras').style.display = 'flex';
    document.getElementById('auth-submit-btn').textContent = 'Sign In to Archive';
    document.getElementById('auth-error').classList.add('hidden');
  };

  window.showSignupMode = function() {
    isSignupMode = true;
    document.getElementById('tab-signup').classList.add('active');
    document.getElementById('tab-login').classList.remove('active');
    document.getElementById('confirm-password-group').classList.remove('hidden');
    document.getElementById('login-extras').style.display = 'none';
    document.getElementById('auth-submit-btn').textContent = 'Create Account';
    document.getElementById('auth-error').classList.add('hidden');
  };

  function showError(msg) {
    const el = document.getElementById('auth-error');
    el.textContent = msg;
    el.classList.remove('hidden');
  }

  function showToast(message) {
    let toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
  }

  /* If already logged in, redirect based on Firestore role check */
  onAuthChange(async (user) => {
    if (user) {
      const isLibrarian = await checkIsLibrarian(user.email);
      const role = isLibrarian ? 'librarian' : 'student';
      sessionStorage.setItem('userRole', role);
      sessionStorage.setItem('userEmail', user.email);
      window.location.href = role === 'librarian' ? 'librarian.html' : 'student.html';
    }
  });

  /* Form submit */
  document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email    = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const btn      = document.getElementById('auth-submit-btn');

    btn.disabled = true;
    btn.textContent = isSignupMode ? 'Creating account…' : 'Signing in…';

    try {
      if (isSignupMode) {
        const confirmPw = document.getElementById('confirm-password').value;
        if (password !== confirmPw) {
          throw new Error('Passwords do not match.');
        }
        await signup(email, password);
        showToast('Account created! Redirecting…');
        /* Firebase auto-signs-in after signup. Check role and redirect. */
        const isLibrarian = await checkIsLibrarian(email.trim().toLowerCase());
        const role = isLibrarian ? 'librarian' : 'student';
        sessionStorage.setItem('userRole', role);
        sessionStorage.setItem('userEmail', email.trim().toLowerCase());
        window.location.href = role === 'librarian' ? 'librarian.html' : 'student.html';
      } else {
        const { role } = await login(email, password);
        window.location.href = role === 'librarian' ? 'librarian.html' : 'student.html';
      }
    } catch (err) {
      let msg = err.message;
      /* Friendlier Firebase error messages */
      if (msg.includes('auth/user-not-found') || msg.includes('auth/invalid-credential')) {
        msg = 'Invalid email or password. Please try again.';
      } else if (msg.includes('auth/email-already-in-use')) {
        msg = 'An account with this email already exists. Try signing in instead.';
      } else if (msg.includes('auth/weak-password')) {
        msg = 'Password must be at least 6 characters.';
      } else if (msg.includes('auth/too-many-requests')) {
        msg = 'Too many attempts. Please try again later.';
      }
      showError(msg);
      btn.disabled = false;
      btn.textContent = isSignupMode ? 'Create Account' : 'Sign In to Archive';
    }
  });

  /* Forgot password */
  document.getElementById('forgot-password-link').addEventListener('click', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value.trim();
    if (!email) {
      showError('Enter your email address first, then click "Forgot password?"');
      return;
    }
    try {
      await resetPassword(email);
      showToast('Password reset email sent! Check your inbox.');
    } catch (err) {
      showError('Could not send reset email. Check the email address and try again.');
    }
  });
</script>
```

- [ ] **Step 5: Remove the old `<script src="script.js"></script>` tag from login.html**

The login page no longer needs `script.js` since auth is handled by the module above. Keep `script.js` only on student/librarian pages.

---

## Task 7: Modify `student.html` — Route Guard + Librarian Switch Button

**Files:**
- Modify: `student.html`

- [ ] **Step 1: Add `auth-ready` hide class to body**

Change `<body>` to:

```html
<body class="auth-guarded">
```

- [ ] **Step 2: Add "Switch to Librarian Dashboard" button in header actions**

Inside the `.header-actions` div, before the logout button, add:

```html
<a href="librarian.html" id="btn-switch-to-librarian" class="btn-logout hidden" style="border-color:var(--gold);color:var(--gold);">
  Librarian Dashboard
</a>
```

- [ ] **Step 3: Add route guard and Firebase logout script**

Replace `<script src="script.js"></script>` at the bottom with:

```html
<script src="script.js"></script>
<script type="module">
  import { guardPage } from './route-guard.js';
  import { logoutUser } from './auth.js';
  guardPage('student');
  window.logout = logoutUser;
</script>
```

---

## Task 8: Modify `librarian.html` — Route Guard (Librarian Only)

**Files:**
- Modify: `librarian.html`

- [ ] **Step 1: Add `auth-guarded` class to body**

Change `<body>` to:

```html
<body class="auth-guarded">
```

- [ ] **Step 2: Add a "Student View" link in header actions**

Inside the `.header-actions` div, before the logout button, add:

```html
<a href="student.html" class="btn-logout" style="border-color:var(--gold);color:var(--gold);">
  Student View
</a>
```

- [ ] **Step 3: Add route guard and Firebase logout script**

Replace `<script src="script.js"></script>` at the bottom with:

```html
<script src="script.js"></script>
<script type="module">
  import { guardPage } from './route-guard.js';
  import { logoutUser } from './auth.js';
  guardPage('librarian');
  window.logout = logoutUser;
</script>
```

---

## Task 9: Modify `index.html` — Auth-Aware Navigation

**Files:**
- Modify: `index.html`

- [ ] **Step 1: Remove `script.js` from index.html**

Remove the `<script src="script.js"></script>` tag — `index.html` doesn't use any of its functions. The only script it needs is the auth-aware module below.

- [ ] **Step 2: Add auth-aware nav script**

Before the closing `</body>` tag, add:

```html
<script type="module">
  import { onAuthChange, checkIsLibrarian } from './auth.js';

  onAuthChange(async (user) => {
    const navActions = document.querySelector('.index-nav .header-actions');
    if (!navActions) return;

    if (user) {
      const isLibrarian = await checkIsLibrarian(user.email);
      const dashUrl = isLibrarian ? 'librarian.html' : 'student.html';
      navActions.innerHTML = `
        <a href="${dashUrl}" class="btn-primary">Go to Dashboard</a>
      `;
    }
  });
</script>
```

---

## Task 10: Add CSS for Auth UI

**Files:**
- Modify: `styles.css`

- [ ] **Step 1: Add auth error and guarded page styles**

Add before the `/* UTILITY */` section:

```css
/* ================================================================
   AUTH UI
   ================================================================ */
/* Hide page content until auth check completes */
.auth-guarded { opacity: 0; transition: opacity 0.3s ease; }
.auth-guarded.auth-ready { opacity: 1; }

/* Auth error message */
.auth-error {
  background: #fef0f0;
  color: #b91c1c;
  border: 1px solid #fecaca;
  border-radius: var(--r-sm);
  padding: 12px 16px;
  font-size: 0.84rem;
  font-weight: 500;
  margin-bottom: 20px;
  line-height: 1.5;
}
```

---

## Task 11: Test the Full Flow

> **Note:** You must serve the project via a local server (not `file://`) because ES modules require HTTP.

- [ ] **Step 1: Start a local server**

You need a local server because ES modules don't work with `file://`. Run from `d:\librayrepoUI`:

```bash
npx serve .
```

Or if you have Python:

```bash
python -m http.server 8000
```

Or use the VS Code "Live Server" extension.

- [ ] **Step 2: Test signup with non-college email**

Go to login page → Switch to "Sign Up" → Enter `test@gmail.com` → Should show error: "Only @igdtuw.ac.in email addresses are allowed."

- [ ] **Step 3: Test signup with college email**

Enter a valid `@igdtuw.ac.in` email → Create password → Should create account and redirect to `student.html`.

- [ ] **Step 4: Test login**

Log out → Sign in with the same credentials → Should redirect to `student.html`.

- [ ] **Step 5: Test librarian access**

In Firebase Console → Firestore → `admins` collection → Add the email you just signed up with → Log out and log back in → Should redirect to `librarian.html`.

- [ ] **Step 6: Test route protection**

While logged out, navigate directly to `student.html` → Should redirect to `login.html`.
While logged in as student, navigate to `librarian.html` → Should redirect to `student.html`.

- [ ] **Step 7: Test librarian accessing student page**

Log in as librarian → Go to `student.html` → Should work + show "Librarian Dashboard" switch button in header.

---

## Summary of Access Control

| Role | `student.html` | `librarian.html` | Assigned How |
|------|:-:|:-:|---|
| **Student** | Yes | No (redirected) | Default for all signups |
| **Librarian** | Yes | Yes | Email added to Firestore `admins` collection |
| **Not logged in** | No (redirected) | No (redirected) | — |
