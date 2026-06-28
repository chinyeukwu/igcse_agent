# Browser Testing Guide

Complete guide for testing the Agentic AI Tutor dashboard in a web browser.

---

## Starting the Application

### Step 1: Start the Server

```bash
cd C:\projects\agenticaitutor
.\mytutor\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8001
```

Expected output:
```
INFO:     Started server process [PID]
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete
```

### Step 2: Open in Browser

- **Chrome/Edge:** http://127.0.0.1:8001/dashboard
- **Firefox:** http://127.0.0.1:8001/dashboard
- **Safari:** http://127.0.0.1:8001/dashboard

---

## Desktop Browser Testing (1920×1080)

### ✅ Page Load

- [ ] Dashboard loads without errors
- [ ] All CSS loads (no styling issues)
- [ ] Header displays correctly
- [ ] Navigation is visible
- [ ] No console errors (F12 → Console)

### ✅ Performance Charts

#### Score Trend Chart (Line Chart)
- [ ] Renders on page load
- [ ] Shows title "Score Trend (Last 10 Quizzes)"
- [ ] Green line visible
- [ ] Area under curve filled
- [ ] Chart is interactive (hover shows tooltip)
- [ ] X-axis shows dates
- [ ] Y-axis shows 0-100 scale
- [ ] Average score displayed below chart
- [ ] Responsive sizing (doesn't overflow)

#### Accuracy by Subject Chart (Bar Chart)
- [ ] Renders on page load
- [ ] Shows title "Accuracy by Subject"
- [ ] Horizontal bars visible
- [ ] Color-coded by subject (green, gold, etc.)
- [ ] Responsive sizing
- [ ] Legend shows subject names
- [ ] Values display on bars
- [ ] Interactive (hover shows details)

### ✅ Quiz History Table

- [ ] Table loads with sample data
- [ ] Columns: Date, Subject, Topic, Score, Difficulty, Time
- [ ] Score badges color-coded (green 85+%, yellow 70-84%, red <70%)
- [ ] Data is readable
- [ ] Table scrolls horizontally on smaller widths
- [ ] Borders and spacing are clean

### ✅ Dashboard Sections

- [ ] "Performance Analytics" section visible
- [ ] "Complete Quiz History" section visible
- [ ] "Topics Due for Review" section visible
- [ ] "Personalized Practice Plan" section visible
- [ ] "Study Schedule" section visible
- [ ] All sections properly spaced
- [ ] Section titles have icons

### ✅ Dark Mode

Press F12 and run in console:
```javascript
document.documentElement.style.colorScheme = 'dark';
```

- [ ] Background turns dark
- [ ] Text remains readable
- [ ] Charts visible in dark mode
- [ ] Colors adjust properly

---

## Tablet Testing (768×1024)

Open DevTools (F12) and toggle device toolbar (Ctrl+Shift+M)

### ✅ Layout Reflow

- [ ] Grid changes to 1 column
- [ ] Content doesn't overflow
- [ ] Charts stack vertically
- [ ] Font sizes remain readable
- [ ] Spacing adjusts appropriately
- [ ] No horizontal scrolling (except tables)

### ✅ Charts on Tablet

- [ ] Charts responsive to 768px width
- [ ] Legend moves (doesn't overflow)
- [ ] Touch-friendly (can select)
- [ ] Labels don't overlap
- [ ] Still interactive

### ✅ Table on Tablet

- [ ] Horizontal scroll if needed
- [ ] Can scroll table without scrolling page
- [ ] All columns visible when scrolled
- [ ] Content readable at smaller font size

---

## Mobile Testing (375×812)

### ✅ Layout

- [ ] Single column layout
- [ ] No horizontal scrolling (except table)
- [ ] Spacing reduced but not cramped
- [ ] Font sizes appropriate
- [ ] Header collapses properly

### ✅ Charts on Mobile

- [ ] Charts render at mobile width
- [ ] Canvas max-height: 200px applied
- [ ] Legend is readable
- [ ] No text overflow
- [ ] Touch interactions work

### ✅ Buttons & Interactions

- [ ] All buttons min 44×44px (touch-friendly)
- [ ] Buttons don't overlap
- [ ] Quiz buttons clickable
- [ ] Links tappable
- [ ] No hover states on tap (no :hover)

### ✅ Tables on Mobile

- [ ] Table becomes stacked layout
- [ ] Each row becomes a card
- [ ] Column labels show (data-label)
- [ ] Values readable
- [ ] Can still scroll through data

### ✅ Performance

- [ ] Page loads in <2 seconds
- [ ] Charts render in <500ms
- [ ] No layout shifts after load
- [ ] Smooth scrolling
- [ ] No jank when interacting

---

## Browser-Specific Testing

### Chrome/Edge

```bash
# Open DevTools
F12

# Test features:
1. Responsive design mode (Ctrl+Shift+M)
2. Light/dark theme (F12 → ⋮ → Appearance)
3. Simulate slow network (F12 → Network → Throttling)
4. Check console for errors
5. Lighthouse audit (F12 → Lighthouse)
```

**Issues to watch for:**
- Chart rendering glitches
- CSS custom properties not supported
- Flexbox/Grid layout issues

### Firefox

```bash
# Open DevTools
F12

# Test features:
1. Responsive design mode (Ctrl+Shift+M)
2. Dark mode (about:preferences → Browser → Appearance)
3. Check console errors
4. Test CSS Grid support
```

**Issues to watch for:**
- Color space support (oklch colors)
- Chart.js compatibility
- Flexbox alignment

### Safari (macOS)

```bash
# Open DevTools
Cmd+Option+I

# Test features:
1. Responsive design
2. Dark appearance (System Preferences → General)
3. Chart rendering
4. Color space support
```

**Issues to watch for:**
- oklch color support (may not work)
- Chart.js rendering
- Touch interactions

---

## API Testing

### Test 1: Get Performance Data

**Endpoint:** `GET /quiz/performance`

```bash
curl -X GET http://127.0.0.1:8001/quiz/performance \
  -H "Authorization: Bearer test-token" 2>&1 | jq .
```

**Expected:** Returns quiz data or auth error

### Test 2: Get Notification History

**Endpoint:** `GET /notifications/history`

```bash
curl -X GET "http://127.0.0.1:8001/notifications/history?limit=10" \
  -H "Authorization: Bearer test-token" 2>&1 | jq .
```

**Expected:** Returns notification list or auth error

### Test 3: Get Notification Stats

**Endpoint:** `GET /notifications/stats`

```bash
curl -X GET http://127.0.0.1:8001/notifications/stats \
  -H "Authorization: Bearer test-token" 2>&1 | jq .
```

**Expected:** Returns stats with total, unread, by_type, by_status

---

## Performance Testing

### Lighthouse Audit

1. Open DevTools (F12)
2. Go to "Lighthouse" tab
3. Click "Generate report"
4. Check metrics:
   - **First Contentful Paint:** <1.5s
   - **Largest Contentful Paint:** <2.5s
   - **Cumulative Layout Shift:** <0.1
   - **Time to Interactive:** <3.5s

### Network Performance

1. DevTools → Network tab
2. Throttle to "Slow 4G"
3. Reload page
4. Check load times:
   - HTML: <500ms
   - CSS: <100ms
   - JS: <200ms
   - Charts: <1s

### Memory Usage

1. DevTools → Memory tab
2. Take heap snapshot
3. Check for:
   - Memory leaks
   - Detached DOM nodes
   - Excessive listeners

---

## Accessibility Testing

### Keyboard Navigation

- [ ] Tab navigates through interactive elements
- [ ] Focus indicators visible
- [ ] Can submit forms without mouse
- [ ] No keyboard traps
- [ ] Tab order logical

### Color Contrast

1. DevTools → Elements
2. Right-click element → Inspect
3. Check "Contrast" in Styles

**Requirements:**
- Normal text: 4.5:1 ratio
- Large text: 3:1 ratio
- UI components: 3:1 ratio

### Screen Reader Testing

```bash
# Windows Narrator
Win + Ctrl + N

# Listen for:
- Page title announced
- Section headings read
- Charts described (if available)
- Form labels associated
```

---

## Error Scenarios

### Test: Missing Authentication

```bash
curl http://127.0.0.1:8001/notifications/history
```

Expected: 403 Forbidden or auth error

### Test: Invalid Notification ID

```bash
curl http://127.0.0.1:8001/notifications/mark-read/99999 \
  -X POST \
  -H "Authorization: Bearer test-token"
```

Expected: 404 Not Found

### Test: Database Error

1. Stop database server
2. Try to load dashboard
3. Check for graceful error handling
4. Verify error logged

---

## Checklist Summary

### Desktop ✅
- [ ] Charts render correctly
- [ ] All sections visible
- [ ] Dark mode works
- [ ] No console errors
- [ ] Responsive (tested at 1920px)

### Tablet ✅
- [ ] Responsive to 768px width
- [ ] Charts resize properly
- [ ] Touch interactions work
- [ ] No horizontal scrolling (except table)
- [ ] Font sizes readable

### Mobile ✅
- [ ] Responsive to 375px width
- [ ] Buttons are 44×44px minimum
- [ ] Charts render at mobile size
- [ ] Table becomes stacked
- [ ] Fast performance

### Accessibility ✅
- [ ] Keyboard navigation works
- [ ] Color contrast adequate
- [ ] Screen reader compatible
- [ ] Focus visible

### API ✅
- [ ] Endpoints respond
- [ ] Authentication enforced
- [ ] Error handling works
- [ ] Data formatted correctly

### Performance ✅
- [ ] Lighthouse score >90
- [ ] First paint <1.5s
- [ ] Charts render <1s
- [ ] No memory leaks

---

## Bug Report Template

If you find an issue:

```
### Title
Brief description of the issue

### Environment
- Browser: Chrome 120.0
- OS: Windows 11
- Device: Desktop (1920×1080)

### Steps to Reproduce
1. Load dashboard
2. Scroll to charts
3. Observe issue

### Expected Behavior
Charts should render smoothly

### Actual Behavior
Charts flicker/don't render

### Screenshots
[Attach screenshot]

### Console Errors
```
[Paste any console errors]
```
```

---

## Next Steps

1. ✅ Open browser to http://127.0.0.1:8001/dashboard
2. ✅ Test all sections render
3. ✅ Test responsive design (resize browser)
4. ✅ Test on mobile device or simulator
5. ✅ Check console for errors
6. ✅ Test API endpoints
7. ✅ Verify performance metrics
