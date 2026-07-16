# Authenticated Home Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a high-atmosphere authenticated home page between login and Studio, with local time, configurable rotating quotes, module launchers, and the three most recent Studio conversations.

**Architecture:** Add a protected Vue route and keep all new behavior frontend-only. Isolate time, quote, and recent-conversation transformations as tested pure functions; keep API loading inside a focused recent-conversations component and page composition inside `AuthenticatedHomeView.vue`.

**Tech Stack:** Vue 3, Vue Router, Pinia, TypeScript, CSS, Vitest.

## Global Constraints

- Preserve `/` as the public landing page and `/login` as the login page.
- Do not add backend routes, database fields, or persistence.
- Do not stage, commit, push, or overwrite unrelated working-tree changes.
- Use the existing warm black, paper white, and acid yellow-green visual language without producing a generic card dashboard.
- Respect `prefers-reduced-motion`.

---

### Task 1: Pure Home Data Logic

**Files:**
- Create: `Agent-vue/src/home/home-time.ts`
- Create: `Agent-vue/src/home/home-time.test.ts`
- Create: `Agent-vue/src/home/home-quotes.ts`
- Create: `Agent-vue/src/home/home-quotes.test.ts`
- Create: `Agent-vue/src/home/home-recent.ts`
- Create: `Agent-vue/src/home/home-recent.test.ts`
- Create: `Agent-vue/src/content/home-quotes.json`

**Interfaces:**
- Produces `greetingForHour(hour)`, `formatHomeDate(date)`, and `formatRelativeTime(value, now)`.
- Produces `initialQuoteIndex(length, random)` and `nextQuoteIndex(current, length)`.
- Produces `mergeRecentConversations(assistants, groups, limit)` returning title, assistant name, timestamp, and chat link.

- [ ] Write failing Vitest cases for greeting boundaries, invalid dates, quote index bounds, cross-assistant sorting, and missing assistant names.
- [ ] Run `npm run test:unit -- --run src/home/home-time.test.ts src/home/home-quotes.test.ts src/home/home-recent.test.ts` and confirm failures from missing modules.
- [ ] Implement the pure functions with deterministic optional `now` and `random` inputs.
- [ ] Add project-owned quotes using `{ text, source, speaker }` objects.
- [ ] Re-run the focused tests and confirm they pass.

### Task 2: Home Components and Page

**Files:**
- Create: `Agent-vue/src/components/home/HomeModuleEntry.vue`
- Create: `Agent-vue/src/components/home/HomeRecentConversations.vue`
- Create: `Agent-vue/src/views/AuthenticatedHomeView.vue`

**Interfaces:**
- `HomeModuleEntry` consumes route, index, title, description, accent, and layout variant props.
- `HomeRecentConversations` consumes `userId`, loads assistants and their conversations with `Promise.allSettled`, and renders partial successes.
- `AuthenticatedHomeView` consumes `useAuthStore`, local clock helpers, and `home-quotes.json`.

- [ ] Build semantic router-link module entries for Studio, Live, Test, and Toolbox.
- [ ] Build the recent-conversations component with three-line skeleton, empty state, default-assistant fallback, and quiet total-failure fallback.
- [ ] Build the editorial home composition with status line, oversized time, personalized greeting, rotating quote, asymmetric module grid, recent conversations, and secondary links.
- [ ] Add timer cleanup, page-visibility pause, random quote start, and reduced-motion CSS behavior.

### Task 3: Routing and Login Flow

**Files:**
- Modify: `Agent-vue/src/router/index.ts`
- Modify: `Agent-vue/src/views/HomeView.vue`

**Interfaces:**
- Adds protected route `/home` named `authenticated-home`.
- Login uses a safe explicit `redirect` target when present, otherwise `/home`.
- Authenticated visits to `/` and `/login` resolve to `/home`.

- [ ] Register the new lazy-loaded route with `requiresAuth` metadata and title.
- [ ] Change router guard authenticated redirects from `/chat` to `/home`.
- [ ] Change login success and mounted-auth redirects to the requested protected destination or `/home`.

### Task 4: Return-to-Home Affordances

**Files:**
- Modify: `Agent-vue/src/views/ChatView.vue`
- Modify: `Agent-vue/src/views/LiveView.vue`
- Modify: `Agent-vue/src/views/TestView.vue`
- Modify: `Agent-vue/src/views/ToolboxView.vue`

**Interfaces:**
- Existing brand marks become semantic buttons that navigate to `/home` without changing mode-switcher structure.

- [ ] Make the Studio rail brand navigate to `/home` and preserve its existing geometry.
- [ ] Make Live and Test brand marks navigate to `/home` with keyboard-visible focus styles.
- [ ] Change the Toolbox wordmark destination from `/chat` to `/home`.

### Task 5: Verification

**Files:**
- No additional production files.

**Interfaces:**
- Verifies the complete route and visual behavior.

- [ ] Run `npm run test:unit` and require all Vitest tests to pass.
- [ ] Run `npm run type-check` and `npm run build`.
- [ ] Use Chrome at `http://localhost:5173/home` to verify login routing, time and quote rendering, module links, recent conversation deep links, keyboard focus, desktop layout, and narrow viewport behavior.
- [ ] Run `git diff --check` on only the touched files and leave the branch uncommitted for the user.
