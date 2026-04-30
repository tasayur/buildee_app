/* ===================================================
   BuildeeMgr — main.js  (Mobile-First)
   =================================================== */

// ===== SIDEBAR =====
const isMobile = () => window.innerWidth <= 768;

function toggleSidebar() {
  if (isMobile()) {
    toggleMobileSidebar();
  } else {
    // Desktop collapse
    const sidebar = document.getElementById('sidebar');
    const wrapper = document.getElementById('mainWrapper');
    sidebar.classList.toggle('collapsed');
    wrapper.classList.toggle('collapsed');
  }
}

function toggleMobileSidebar() {
  const sidebar  = document.getElementById('sidebar');
  const overlay  = document.getElementById('sidebarOverlay');
  sidebar.classList.toggle('mobile-open');
  overlay.classList.toggle('show');
  document.body.style.overflow = sidebar.classList.contains('mobile-open') ? 'hidden' : '';
}

function closeMobileSidebar() {
  const sidebar  = document.getElementById('sidebar');
  const overlay  = document.getElementById('sidebarOverlay');
  sidebar.classList.remove('mobile-open');
  overlay.classList.remove('show');
  document.body.style.overflow = '';
}

// Close sidebar on resize to desktop
window.addEventListener('resize', () => {
  if (!isMobile()) closeMobileSidebar();
});

// ===== MODAL =====
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
  document.body.style.overflow = '';
}

function openModalById(id) {
  document.getElementById(id).classList.add('open');
  document.body.style.overflow = 'hidden';
}

// Close on backdrop click
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal')) {
    e.target.classList.remove('open');
    document.body.style.overflow = '';
  }
});

// Close on Escape
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal.open').forEach(m => {
      m.classList.remove('open');
    });
    document.body.style.overflow = '';
  }
});

// ===== TOAST =====
let toastTimer = null;
function showToast(message, type = 'info', duration = 3000) {
  const toast = document.getElementById('toast');
  if (toastTimer) clearTimeout(toastTimer);
  toast.textContent = message;
  toast.className = `toast ${type} show`;
  toastTimer = setTimeout(() => { toast.classList.remove('show'); }, duration);
}

// ===== DATE DISPLAY =====
function setCurrentDate() {
  const el = document.getElementById('currentDate');
  if (el) {
    el.textContent = new Date().toLocaleDateString('ja-JP', {
      year: 'numeric', month: 'short', day: 'numeric', weekday: 'short'
    });
  }
}
setCurrentDate();

// ===== TAB SWITCH (generic) =====
// Page-specific tabs override this in their own <script>
function switchTab(name) {
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const target = document.getElementById('tab-' + name);
  if (target) target.classList.add('active');
  if (event && event.target) event.target.classList.add('active');
}

// ===== FAB (page-specific override) =====
// Each page defines fabAction() in its own <script>; default is no-op
if (typeof fabAction === 'undefined') {
  window.fabAction = function() {};
}

// ===== PULL-TO-REFRESH hint (mobile UX) =====
// Adds subtle bounce when user tries to pull past top — native feel
let startY = 0;
document.addEventListener('touchstart', e => { startY = e.touches[0].clientY; }, { passive: true });

// ===== HAPTIC-LIKE FEEDBACK via vibration API =====
function haptic(ms = 10) {
  if (navigator.vibrate) navigator.vibrate(ms);
}

// ===== UTIL: format time =====
function formatTime(hhmm) {
  if (!hhmm) return '-';
  return hhmm;
}

// ===== UTIL: elapsed minutes between two HH:MM strings =====
function elapsedMin(start, end) {
  if (!start || !end) return null;
  const [sh, sm] = start.split(':').map(Number);
  const [eh, em] = end.split(':').map(Number);
  return (eh * 60 + em) - (sh * 60 + sm);
}

function formatElapsed(mins) {
  if (mins == null || mins < 0) return '-';
  return `${Math.floor(mins / 60)}h${String(mins % 60).padStart(2,'0')}m`;
}
