/**
 * POS Application Controller
 * Handles user interactions, reactive cart state, tender calculations,
 * barcode wedge scanning, item modifiers & notes, configurable sales tax,
 * in-app delete confirmation, edit product modal, CSV export, and parked orders.
 * Strict rule: No emojis.
 */

const AppState = {
  products: [],
  cart: [],
  parkedOrders: [],
  categories: ['All', 'Top Picks'],
  selectedCategory: 'All',
  searchQuery: '',
  inventorySearchQuery: '',
  catalogPagination: {
    page: 1,
    pageSize: 12,
    totalPages: 1
  },
  catalogSort: 'name-asc',
  catalogStockFilter: 'all',
  activeSubtotal: 0.0,
  activeTax: 0.0,
  activeTotal: 0.0,
  settings: {
    tax_enabled: true,
    tax_rate: 12.00,
    tax_name: 'VAT (12%)',
    store_name: 'METRO POINT OF SALE',
    branch: 'Terminal 01 - Manila BGC',
    currency_symbol: '₱'
  },
  editingCartItemIndex: null,
  productPendingDelete: null,
  lastSync: {
    products_mtime: 0,
    settings_mtime: 0,
    transactions_mtime: 0
  },
  isSyncing: false,
  inventoryStockFilter: 'all',
  inventoryCategoryFilter: 'all',
};

// --- DOM Cache ---
const DOM = {
  // Navigation & Header
  timeDisplay: document.getElementById('liveTime'),
  headerStoreName: document.getElementById('headerStoreName'),
  headerBranch: document.getElementById('headerBranch'),
  btnOpenBarcodeModal: document.getElementById('btnOpenBarcodeModal'),
  btnOpenConsole: document.getElementById('btnOpenConsole'),
  btnRecallOrder: document.getElementById('btnRecallOrder'),
  parkedOrderCount: document.getElementById('parkedOrderCount'),
  btnManualSync: document.getElementById('btnManualSync'),
  syncIcon: document.getElementById('syncIcon'),
  syncStatusText: document.getElementById('syncStatusText'),
  btnForceReloadDisk: document.getElementById('btnForceReloadDisk'),
  syncPythonVersion: document.getElementById('syncPythonVersion'),
  syncProductCount: document.getElementById('syncProductCount'),
  syncTransactionCount: document.getElementById('syncTransactionCount'),
  syncFilesTableBody: document.getElementById('syncFilesTableBody'),

  // Catalog
  searchInput: document.getElementById('searchInput'),
  searchClearBtn: document.getElementById('searchClearBtn'),
  categoryBar: document.getElementById('categoryBar'),
  btnCatScrollLeft: document.getElementById('btnCatScrollLeft'),
  btnCatScrollRight: document.getElementById('btnCatScrollRight'),
  catalogCountInfo: document.getElementById('catalogCountInfo'),
  catalogStockFilter: document.getElementById('catalogStockFilter'),
  catalogSortSelect: document.getElementById('catalogSortSelect'),
  catalogPageSize: document.getElementById('catalogPageSize'),
  productGrid: document.getElementById('productGrid'),
  catalogPaginationBar: document.getElementById('catalogPaginationBar'),
  btnCatalogPrev: document.getElementById('btnCatalogPrev'),
  btnCatalogNext: document.getElementById('btnCatalogNext'),
  catalogPageNumbers: document.getElementById('catalogPageNumbers'),

  // Ticket / Cart
  ticketId: document.getElementById('ticketId'),
  cartItemsContainer: document.getElementById('cartItemsContainer'),
  cartEmptyState: document.getElementById('cartEmptyState'),
  cartCountBadge: document.getElementById('cartCountBadge'),
  cartItemCountSummary: document.getElementById('cartItemCountSummary'),
  subtotalAmount: document.getElementById('subtotalAmount'),
  taxRow: document.getElementById('taxRow'),
  taxLabel: document.getElementById('taxLabel'),
  taxAmount: document.getElementById('taxAmount'),
  totalAmount: document.getElementById('totalAmount'),
  clearCartBtn: document.getElementById('clearCartBtn'),
  btnHoldOrder: document.getElementById('btnHoldOrder'),
  btnProceedPayment: document.getElementById('btnProceedPayment'),

  // Item Modifiers Modal
  modifierModal: document.getElementById('modifierModal'),
  modifierModalCard: document.getElementById('modifierModalCard'),
  modifierItemTitle: document.getElementById('modifierItemTitle'),
  modifierItemBasePrice: document.getElementById('modifierItemBasePrice'),
  modifiersSelectionList: document.getElementById('modifiersSelectionList'),
  modifierItemNotes: document.getElementById('modifierItemNotes'),
  btnSaveModifier: document.getElementById('btnSaveModifier'),
  btnCancelModifier: document.getElementById('btnCancelModifier'),
  btnCloseModifier: document.getElementById('btnCloseModifier'),

  // Cashier Identity
  topbarCashierName: document.getElementById('topbarCashierName'),
  checkoutCashierInput: document.getElementById('checkoutCashierInput'),

  // Barcode Lookup & Phone Camera Scanner
  barcodeModal: document.getElementById('barcodeModal'),
  barcodeModalCard: document.getElementById('barcodeModalCard'),
  barcodeManualInput: document.getElementById('barcodeManualInput'),
  btnSubmitBarcode: document.getElementById('btnSubmitBarcode'),
  btnCloseBarcode: document.getElementById('btnCloseBarcode'),
  cameraScannerVideo: document.getElementById('cameraScannerVideo'),
  cameraScannerReticle: document.getElementById('cameraScannerReticle'),
  barcodeDefaultPlaceholder: document.getElementById('barcodeDefaultPlaceholder'),
  barcodeScannerStatusNote: document.getElementById('barcodeScannerStatusNote'),
  btnToggleCameraScanner: document.getElementById('btnToggleCameraScanner'),
  btnToggleCameraText: document.getElementById('btnToggleCameraText'),
  phoneCameraFileInput: document.getElementById('phoneCameraFileInput'),
  btnPhoneSnapBarcode: document.getElementById('btnPhoneSnapBarcode'),
  phoneUrlDisplay: document.getElementById('phoneUrlDisplay'),
  btnCopyPhoneUrl: document.getElementById('btnCopyPhoneUrl'),

  // Delete Confirmation Modal
  deleteConfirmModal: document.getElementById('deleteConfirmModal'),
  deleteConfirmModalCard: document.getElementById('deleteConfirmModalCard'),
  deleteConfirmMessage: document.getElementById('deleteConfirmMessage'),
  btnConfirmDelete: document.getElementById('btnConfirmDelete'),
  btnCancelDelete: document.getElementById('btnCancelDelete'),
  btnCloseDeleteConfirm: document.getElementById('btnCloseDeleteConfirm'),

  // Edit Product Modal
  editProductModal: document.getElementById('editProductModal'),
  editProductModalCard: document.getElementById('editProductModalCard'),
  editProductForm: document.getElementById('editProductForm'),
  editProdId: document.getElementById('editProdId'),
  editProdName: document.getElementById('editProdName'),
  editProdCategory: document.getElementById('editProdCategory'),
  editProdPrice: document.getElementById('editProdPrice'),
  editProdStock: document.getElementById('editProdStock'),
  editProdBarcode: document.getElementById('editProdBarcode'),
  btnCancelEditProduct: document.getElementById('btnCancelEditProduct'),
  btnCloseEditProduct: document.getElementById('btnCloseEditProduct'),

  // Parked Orders Modal
  parkedOrdersModal: document.getElementById('parkedOrdersModal'),
  parkedOrdersModalCard: document.getElementById('parkedOrdersModalCard'),
  parkedOrdersList: document.getElementById('parkedOrdersList'),
  btnCloseParkedOrders: document.getElementById('btnCloseParkedOrders'),

  // Overhauled Back-Office Console
  consoleModal: document.getElementById('consoleModal'),
  consoleModalCard: document.getElementById('consoleModalCard'),
  btnCloseConsole: document.getElementById('btnCloseConsole'),
  consolePageTitle: document.getElementById('consolePageTitle'),
  consolePageDesc: document.getElementById('consolePageDesc'),
  consoleHeaderActions: document.getElementById('consoleHeaderActions'),
  btnExportCsv: document.getElementById('btnExportCsv'),
  btnToggleAddProduct: document.getElementById('btnToggleAddProduct'),
  collapsibleAddProduct: document.getElementById('collapsibleAddProduct'),
  btnCloseAddProduct: document.getElementById('btnCloseAddProduct'),
  btnCancelAddProduct: document.getElementById('btnCancelAddProduct'),
  inventorySummaryRibbon: document.getElementById('inventorySummaryRibbon'),
  kpiChipAll: document.getElementById('kpiChipAll'),
  kpiChipInStock: document.getElementById('kpiChipInStock'),
  kpiChipLowStock: document.getElementById('kpiChipLowStock'),
  kpiChipOutOfStock: document.getElementById('kpiChipOutOfStock'),
  kpiCountAll: document.getElementById('kpiCountAll'),
  kpiCountInStock: document.getElementById('kpiCountInStock'),
  kpiCountLowStock: document.getElementById('kpiCountLowStock'),
  kpiCountOutOfStock: document.getElementById('kpiCountOutOfStock'),
  inventoryFilterInput: document.getElementById('inventoryFilterInput'),
  inventoryCategoryFilter: document.getElementById('inventoryCategoryFilter'),
  btnQuickReorderLow: document.getElementById('btnQuickReorderLow'),
  inventoryTableCount: document.getElementById('inventoryTableCount'),
  navInventoryCount: document.getElementById('navInventoryCount'),
  navInventoryLowBadge: document.getElementById('navInventoryLowBadge'),
  navTaxStatus: document.getElementById('navTaxStatus'),
  navOrdersCount: document.getElementById('navOrdersCount'),
  inventoryTableBody: document.getElementById('inventoryTableBody'),
  newProductForm: document.getElementById('newProductForm'),
  newProdIconGrid: document.getElementById('newProdIconGrid'),
  newProdIcon: document.getElementById('newProdIcon'),
  newProdSelectedIconLabel: document.getElementById('newProdSelectedIconLabel'),
  categoryDatalist: document.getElementById('categoryDatalist'),
  editProdIconGrid: document.getElementById('editProdIconGrid'),
  editProdIcon: document.getElementById('editProdIcon'),
  editProdSelectedIconLabel: document.getElementById('editProdSelectedIconLabel'),
  settingsForm: document.getElementById('settingsForm'),
  settingsTaxToggle: document.getElementById('settingsTaxToggle'),
  settingsTaxRate: document.getElementById('settingsTaxRate'),
  settingsTaxName: document.getElementById('settingsTaxName'),
  settingsStoreName: document.getElementById('settingsStoreName'),
  settingsBranch: document.getElementById('settingsBranch'),
  settingsPhone: document.getElementById('settingsPhone'),
  settingsCashierName: document.getElementById('settingsCashierName'),
  dashboardCashierDisplay: document.getElementById('dashboardCashierDisplay'),
  dashboardActiveCashierName: document.getElementById('dashboardActiveCashierName'),
  analyticsStatsGrid: document.getElementById('analyticsStatsGrid'),
  transactionHistoryBody: document.getElementById('transactionHistoryBody'),

  // Checkout Modal
  checkoutModal: document.getElementById('checkoutModal'),
  checkoutModalCard: document.getElementById('checkoutModalCard'),
  checkoutDueDisplay: document.getElementById('checkoutDueDisplay'),
  tenderInput: document.getElementById('tenderInput'),
  changeFeedbackBox: document.getElementById('changeFeedbackBox'),
  changeAmountDisplay: document.getElementById('changeAmountDisplay'),
  changeBoxLabel: document.getElementById('changeBoxLabel'),
  quickCashGrid: document.getElementById('quickCashGrid'),
  btnCompleteSale: document.getElementById('btnCompleteSale'),
  btnCloseCheckout: document.getElementById('btnCloseCheckout'),

  // Receipt Modal
  receiptModal: document.getElementById('receiptModal'),
  receiptModalCard: document.getElementById('receiptModalCard'),
  receiptPaper: document.getElementById('receiptPaper'),
  receiptQrTxId: document.getElementById('receiptQrTxId'),
  btnPrintReceipt: document.getElementById('btnPrintReceipt'),
  btnNewOrder: document.getElementById('btnNewOrder'),
  btnCloseReceipt: document.getElementById('btnCloseReceipt'),

  // Toast Container
  toastContainer: document.getElementById('toastContainer'),
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', async () => {
  initClock();
  generateTicketId();
  await loadStoreSettings();
  await loadCatalog();
  setupEventListeners();
  setupBarcodeWedgeScanner();
  startStorageSyncDaemon();
});

// --- Currency & Formatting Helpers ---
function formatMoney(amount) {
  const sym = AppState.settings?.currency_symbol || '₱';
  const num = typeof amount === 'number' ? amount : (parseFloat(amount) || 0.0);
  return `${sym}${num.toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// --- Storage & Live Sync Daemon ---
function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`;
}

function renderStorageSyncDashboard(syncMeta) {
  if (!syncMeta) return;

  if (DOM.syncPythonVersion) {
    DOM.syncPythonVersion.textContent = `Python ${syncMeta.python_version || '3.14'} Online`;
  }
  if (DOM.syncProductCount) {
    DOM.syncProductCount.textContent = `${syncMeta.products_count ?? AppState.products.length} Products`;
  }
  if (DOM.syncTransactionCount) {
    DOM.syncTransactionCount.textContent = `${syncMeta.transactions_count ?? 0} Orders`;
  }

  if (DOM.syncFilesTableBody && syncMeta.files) {
    const roles = [
      { key: 'products', name: 'Product Catalog Database', desc: 'Active inventory, barcodes & pricing' },
      { key: 'transactions', name: 'Sales Transactions Ledger', desc: 'Audit log & completed receipts' },
      { key: 'settings', name: 'Terminal Configuration', desc: 'Tax rates, store branding & register info' },
      { key: 'receipt', name: 'Thermal Receipt Spool', desc: 'Last formatted thermal printout' }
    ];

    DOM.syncFilesTableBody.innerHTML = roles.map(r => {
      const f = syncMeta.files[r.key];
      if (!f) return '';
      const sizeStr = formatBytes(f.size_bytes);
      const mtimeStr = f.mtime_str || '--';
      return `
        <tr>
          <td>
            <div style="font-weight: 600; color: var(--text-primary);">${escapeHtml(r.name)}</div>
            <div style="font-size: 11px; color: var(--text-secondary);">${escapeHtml(r.desc)}</div>
          </td>
          <td><code>${escapeHtml(f.filename)}</code></td>
          <td class="tabular-num">${sizeStr}</td>
          <td><span class="badge badge-success"><span class="badge-dot pulse"></span>Synced</span></td>
          <td class="tabular-num" style="color: var(--text-secondary);">${mtimeStr}</td>
        </tr>
      `;
    }).join('');
  }
}

async function checkLiveSync(isManual = false) {
  if (AppState.isSyncing) return;
  AppState.isSyncing = true;
  if (DOM.syncIcon) DOM.syncIcon.style.animation = 'spin 0.6s linear infinite';

  try {
    const syncMeta = await API.checkSync();
    let hasChanges = false;

    if (isManual || (AppState.lastSync.products_mtime && syncMeta.products_mtime !== AppState.lastSync.products_mtime)) {
      await loadCatalog();
      renderInventoryTable();
      reconcileCartStock();
      hasChanges = true;
    }

    if (isManual || (AppState.lastSync.settings_mtime && syncMeta.settings_mtime !== AppState.lastSync.settings_mtime)) {
      await loadStoreSettings();
      renderCart();
      hasChanges = true;
    }

    if (isManual || (AppState.lastSync.transactions_mtime && syncMeta.transactions_mtime !== AppState.lastSync.transactions_mtime)) {
      renderAnalyticsTab();
      hasChanges = true;
    }

    AppState.lastSync = syncMeta;
    renderStorageSyncDashboard(syncMeta);

    if (syncMeta.phone_connect_url && DOM.phoneUrlDisplay) {
      DOM.phoneUrlDisplay.textContent = syncMeta.phone_connect_url;
    }

    if (DOM.syncStatusText) {
      DOM.syncStatusText.textContent = 'Synced';
    }

    if (isManual) {
      showToast('Storage verified: 100% in sync with Python & JSON files.');
    }
  } catch (err) {
    if (DOM.syncStatusText) DOM.syncStatusText.textContent = 'Offline';
  } finally {
    if (DOM.syncIcon) DOM.syncIcon.style.animation = 'none';
    AppState.isSyncing = false;
  }
}

function reconcileCartStock() {
  let cartAdjusted = false;
  AppState.cart.forEach(item => {
    const diskItem = AppState.products.find(p => p.id === item.id);
    if (!diskItem || diskItem.stock <= 0) {
      showToast(`Item "${item.name}" was modified or out of stock on disk.`, true);
    } else if (item.qty > diskItem.stock) {
      item.qty = diskItem.stock;
      item.stock = diskItem.stock;
      item.total = Math.round(item.qty * item.unitPrice * 100) / 100;
      cartAdjusted = true;
    }
  });
  if (cartAdjusted) {
    renderCart();
    showToast('Cart quantities synchronized with current inventory on disk.');
  }
}

function startStorageSyncDaemon() {
  checkLiveSync(false);
  setInterval(() => checkLiveSync(false), 4000);
  window.addEventListener('focus', () => checkLiveSync(false));
}

function initClock() {
  const update = () => {
    const now = new Date();
    DOM.timeDisplay.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  };
  update();
  setInterval(update, 1000);
}

function generateTicketId() {
  const code = Math.floor(1000 + Math.random() * 9000);
  DOM.ticketId.textContent = `#ORD-${code}`;
}

// --- Settings Management ---
async function loadStoreSettings() {
  try {
    const settings = await API.getSettings();
    AppState.settings = settings;

    DOM.headerStoreName.textContent = settings.store_name || 'Metro Point of Sale';
    DOM.headerBranch.textContent = `${settings.branch || 'Terminal 01'} • Active Shift`;

    DOM.settingsTaxToggle.checked = Boolean(settings.tax_enabled);
    DOM.settingsTaxRate.value = settings.tax_rate ?? 8.25;
    DOM.settingsTaxName.value = settings.tax_name || 'Sales Tax';
    DOM.settingsStoreName.value = settings.store_name || '';
    DOM.settingsBranch.value = settings.branch || '';
    DOM.settingsPhone.value = settings.phone || '';

    updateTaxLabels();
  } catch (err) {
    console.error('Failed to load settings:', err);
  }
}

function updateTaxLabels() {
  const s = AppState.settings;
  if (!s.tax_enabled) {
    DOM.taxRow.style.display = 'none';
    if (DOM.navTaxStatus) {
      DOM.navTaxStatus.textContent = 'Disabled';
      DOM.navTaxStatus.style.color = 'var(--text-muted)';
    }
  } else {
    DOM.taxRow.style.display = 'flex';
    DOM.taxLabel.textContent = `${s.tax_name || 'Sales Tax'} (${s.tax_rate}%)`;
    if (DOM.navTaxStatus) {
      DOM.navTaxStatus.textContent = `${s.tax_rate}%`;
      DOM.navTaxStatus.style.color = '#38BDF8';
    }
  }
}

// --- Data Loading ---
async function loadCatalog() {
  try {
    const products = await API.getProducts();
    AppState.products = products;

    if (DOM.navInventoryCount) {
      DOM.navInventoryCount.textContent = products.length;
    }

    const catSet = new Set(['All', 'Top Picks']);
    products.forEach(p => {
      if (p.category) catSet.add(p.category);
    });
    AppState.categories = Array.from(catSet);

    if (DOM.categoryDatalist) {
      DOM.categoryDatalist.innerHTML = AppState.categories
        .filter(c => c !== 'All' && c !== 'Top Picks')
        .map(c => `<option value="${escapeHtml(c)}">`)
        .join('');
    }

    renderCategories();
    renderProducts();
  } catch (err) {
    showToast('Failed to load products: ' + err.message, true);
  }
}

// --- 24 Curated Retail Vector Icons (Zero Emojis) ---
const RETAIL_ICONS = [
  { id: 'coffee', label: 'Coffee / Mug', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8h1a4 4 0 0 1 0 8h-1"></path><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"></path><line x1="6" y1="1" x2="6" y2="4"></line><line x1="10" y1="1" x2="10" y2="4"></line><line x1="14" y1="1" x2="14" y2="4"></line></svg>` },
  { id: 'tea', label: 'Tea / Cup', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 8h1a4 4 0 1 1 0 8h-1"></path><path d="M3 8h14v7a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V8z"></path><line x1="6" y1="2" x2="6" y2="4"></line><line x1="10" y1="2" x2="10" y2="4"></line><line x1="14" y1="2" x2="14" y2="4"></line></svg>` },
  { id: 'glass', label: 'Cold Drink', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 2h14l-2 18H7L5 2z"></path><line x1="6" y1="8" x2="18" y2="8"></line></svg>` },
  { id: 'croissant', label: 'Bakery / Pastry', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 7.5A4.5 4.5 0 0 0 15.5 3H8.5A4.5 4.5 0 0 0 4 7.5V11a7 7 0 0 0 7 7h2a7 7 0 0 0 7-7V7.5z"></path><line x1="8" y1="11" x2="8.01" y2="11"></line><line x1="12" y1="11" x2="12.01" y2="11"></line><line x1="16" y1="11" x2="16.01" y2="11"></line></svg>` },
  { id: 'cake', label: 'Cake / Dessert', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-8a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8"></path><path d="M4 16s2-1 4-1 4 1 4 1 2-1 4-1 4 1 4 1"></path><path d="M2 21h20"></path><line x1="12" y1="4" x2="12" y2="7"></line></svg>` },
  { id: 'cookie', label: 'Cookie / Treat', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"></circle><path d="M12 3a9 9 0 0 0 0 18"></path><line x1="3" y1="12" x2="21" y2="12"></line></svg>` },
  { id: 'bowl', label: 'Rice / Meal Bowl', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 11c0 4.418 3.582 8 8 8s8-3.582 8-8H3z"></path><path d="M11 2v5M7 4v3M15 4v3"></path><line x1="7" y1="19" x2="15" y2="19"></line></svg>` },
  { id: 'utensils', label: 'Dining / Entree', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 2v20"></path><path d="M21 2v6a3 3 0 0 1-3 3"></path><path d="M3 2v7c0 1.66 1.34 3 3 3v10"></path><path d="M9 2v7c0 1.66-1.34 3-3 3"></path></svg>` },
  { id: 'pizza', label: 'Pizza / Fast Food', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 19.5A11 11 0 0 0 22 19.5L12 2z"></path><circle cx="12" cy="13" r="1.5"></circle><circle cx="9" cy="16" r="1"></circle><circle cx="15" cy="16" r="1"></circle></svg>` },
  { id: 'burger', label: 'Burger / Sandwich', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 11a8 8 0 0 1 16 0H4z"></path><rect x="3" y="14" width="18" height="3" rx="1"></rect><path d="M5 20h14a2 2 0 0 0 2-2v-1H3v1a2 2 0 0 0 2 2z"></path></svg>` },
  { id: 'leaf', label: 'Produce / Salad', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"></path><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"></path></svg>` },
  { id: 'apple', label: 'Fruit / Fresh', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20.94c1.5 0 2.75 1.06 4 1.06 3 0 6-8 6-12.22A4.91 4.91 0 0 0 17 5c-2.22 0-4 1.44-5 2-1-.56-2.78-2-5-2a4.9 4.9 0 0 0-5 4.78C2 14 5 22 8 22c1.25 0 2.5-1.06 4-1.06Z"></path><path d="M10 2c1 .5 2 2 2 5"></path></svg>` },
  { id: 'package', label: 'Packaged / Snack', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"></line><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>` },
  { id: 'shopping-bag', label: 'Merchandise / Bag', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path><line x1="3" y1="6" x2="21" y2="6"></line><path d="M16 10a4 4 0 0 1-8 0"></path></svg>` },
  { id: 'tag', label: 'Discount / Promo', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path><line x1="7" y1="7" x2="7.01" y2="7"></line></svg>` },
  { id: 'star', label: 'Top Pick / Featured', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>` },
  { id: 'heart', label: 'House Favorite', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>` },
  { id: 'zap', label: 'Energy / Quick Grab', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>` },
  { id: 'flame', label: 'Hot / Spicy Special', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"></path></svg>` },
  { id: 'snowflake', label: 'Cold / Chilled', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="2" x2="12" y2="22"></line><line x1="2" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line><line x1="19.07" y1="4.93" x2="4.93" y2="19.07"></line></svg>` },
  { id: 'sparkles', label: 'Signature / Premium', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l1.912 5.885L20 10l-5.088 1.115L13 17l-1.912-5.885L6 10l5.088-1.115z"></path></svg>` },
  { id: 'box', label: 'Case / Bulk Item', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>` },
  { id: 'award', label: 'Award Winning', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="7"></circle><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>` },
  { id: 'grid', label: 'General / SKU', svg: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>` }
];

function getIconSvg(keyOrCat) {
  if (!keyOrCat) return RETAIL_ICONS[0].svg;
  const found = RETAIL_ICONS.find(item => item.id === keyOrCat);
  if (found) return found.svg;
  return getCategoryIconSvg(keyOrCat);
}

function inferIconFromCategory(cat) {
  const c = String(cat || '').toLowerCase();
  if (c.includes('beverage') || c.includes('coffee') || c.includes('tea')) return 'coffee';
  if (c.includes('bakery') || c.includes('pastr') || c.includes('bread')) return 'croissant';
  if (c.includes('rice') || c.includes('silog') || c.includes('meal')) return 'bowl';
  if (c.includes('snack') || c.includes('dessert')) return 'cookie';
  if (c.includes('produce') || c.includes('fruit')) return 'apple';
  return 'grid';
}

function populateIconPicker(gridEl, hiddenInputEl, labelEl, selectedId = 'coffee') {
  if (!gridEl) return;
  gridEl.innerHTML = '';
  if (hiddenInputEl) hiddenInputEl.value = selectedId;
  const currentIcon = RETAIL_ICONS.find(i => i.id === selectedId) || RETAIL_ICONS[0];
  if (labelEl) labelEl.textContent = `Selected: ${currentIcon.label}`;

  RETAIL_ICONS.forEach(icon => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `icon-picker-btn ${icon.id === selectedId ? 'active' : ''}`;
    btn.title = icon.label;
    btn.innerHTML = icon.svg;
    btn.addEventListener('click', () => {
      gridEl.querySelectorAll('.icon-picker-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (hiddenInputEl) hiddenInputEl.value = icon.id;
      if (labelEl) labelEl.textContent = `Selected: ${icon.label}`;
    });
    gridEl.appendChild(btn);
  });
}

// --- Category Iconography (Zero Emojis, Crisp Vector Geometry) ---
function getCategoryIconSvg(cat) {
  const c = String(cat).toLowerCase().trim();
  if (c === 'all') {
    return `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>`;
  }
  if (c.includes('top pick') || c.includes('favorite') || c.includes('star')) {
    return `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>`;
  }
  if (c.includes('beverage') || c.includes('drink') || c.includes('coffee') || c.includes('tea')) {
    return `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M18 8h1a4 4 0 0 1 0 8h-1"></path><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"></path><line x1="6" y1="1" x2="6" y2="4"></line><line x1="10" y1="1" x2="10" y2="4"></line><line x1="14" y1="1" x2="14" y2="4"></line></svg>`;
  }
  if (c.includes('bakery') || c.includes('pastr') || c.includes('bread') || c.includes('cake')) {
    return `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M20 7.5A4.5 4.5 0 0 0 15.5 3H8.5A4.5 4.5 0 0 0 4 7.5V11a7 7 0 0 0 7 7h2a7 7 0 0 0 7-7V7.5z"></path><line x1="8" y1="11" x2="8.01" y2="11"></line><line x1="12" y1="11" x2="12.01" y2="11"></line><line x1="16" y1="11" x2="16.01" y2="11"></line></svg>`;
  }
  if (c.includes('rice') || c.includes('silog') || c.includes('meal') || c.includes('food')) {
    return `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M3 11c0 4.418 3.582 8 8 8s8-3.582 8-8H3z"></path><path d="M11 2v5M7 4v3M15 4v3"></path><line x1="7" y1="19" x2="15" y2="19"></line></svg>`;
  }
  if (c.includes('snack') || c.includes('dessert') || c.includes('sweet') || c.includes('candy')) {
    return `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="9"></circle><path d="M12 3a9 9 0 0 0 0 18"></path><line x1="3" y1="12" x2="21" y2="12"></line></svg>`;
  }
  if (c.includes('produce') || c.includes('fruit') || c.includes('veg') || c.includes('fresh')) {
    return `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"></path><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"></path></svg>`;
  }
  return `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path><line x1="7" y1="7" x2="7.01" y2="7"></line></svg>`;
}

function updateCategoryScrollButtons() {
  if (!DOM.btnCatScrollLeft || !DOM.btnCatScrollRight || !DOM.categoryBar) return;
  const { scrollLeft, scrollWidth, clientWidth } = DOM.categoryBar;
  DOM.btnCatScrollLeft.disabled = scrollLeft <= 2;
  DOM.btnCatScrollRight.disabled = Math.ceil(scrollLeft + clientWidth) >= scrollWidth - 2;
}

// --- Render Catalog ---
function renderCategories() {
  DOM.categoryBar.innerHTML = '';
  
  // Calculate item counts per category
  const counts = { 'All': AppState.products.length };
  counts['Top Picks'] = Math.min(4, AppState.products.length);

  AppState.products.forEach(p => {
    const cat = p.category || 'General';
    counts[cat] = (counts[cat] || 0) + 1;
  });

  AppState.categories.forEach(cat => {
    const chip = document.createElement('button');
    const isActive = cat === AppState.selectedCategory;
    chip.type = 'button';
    chip.className = `category-chip ${isActive ? 'active' : ''}`;
    chip.setAttribute('data-category', cat);
    const count = counts[cat] !== undefined ? counts[cat] : 0;
    const iconSvg = getCategoryIconSvg(cat);
    chip.innerHTML = `
      <span class="category-chip-icon">${iconSvg}</span>
      <span class="category-chip-label">${escapeHtml(cat)}</span>
      <span class="category-chip-count">${count}</span>
    `;
    chip.addEventListener('click', () => {
      AppState.selectedCategory = cat;
      AppState.catalogPagination.page = 1;
      renderCategories();
      renderProducts();
      chip.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    });
    DOM.categoryBar.appendChild(chip);
  });

  setTimeout(updateCategoryScrollButtons, 40);
}

function renderProducts() {
  const container = DOM.productGrid;
  container.innerHTML = '';

  let list = AppState.products;

  // 1. Category Filter
  if (AppState.selectedCategory === 'Top Picks') {
    list = list.slice(0, 4);
  } else if (AppState.selectedCategory !== 'All') {
    list = list.filter(p => p.category === AppState.selectedCategory);
  }

  // 2. Search Keyword Filter
  const s = AppState.searchQuery.toLowerCase().trim();
  if (s) {
    list = list.filter(p => 
      p.name.toLowerCase().includes(s) || 
      String(p.id).includes(s) || 
      String(p.barcode || '').toLowerCase().includes(s) ||
      String(p.category || '').toLowerCase().includes(s)
    );
  }

  // 3. Stock Status Filter
  if (AppState.catalogStockFilter === 'in-stock') {
    list = list.filter(p => p.stock > 0);
  } else if (AppState.catalogStockFilter === 'low-stock') {
    list = list.filter(p => p.stock <= 10);
  }

  // 4. Multi-field Sorting
  const sort = AppState.catalogSort;
  list = [...list].sort((a, b) => {
    if (sort === 'name-asc') return a.name.localeCompare(b.name);
    if (sort === 'name-desc') return b.name.localeCompare(a.name);
    if (sort === 'price-asc') return a.price - b.price;
    if (sort === 'price-desc') return b.price - a.price;
    if (sort === 'stock-asc') return a.stock - b.stock;
    if (sort === 'stock-desc') return b.stock - a.stock;
    return 0;
  });

  const totalFiltered = list.length;
  const pageSizeVal = AppState.catalogPagination.pageSize;
  const isAll = pageSizeVal === 'all';
  const pageSize = isAll ? totalFiltered || 1 : parseInt(pageSizeVal, 10);
  const totalPages = Math.max(1, Math.ceil(totalFiltered / pageSize));
  
  AppState.catalogPagination.totalPages = totalPages;
  if (AppState.catalogPagination.page > totalPages) {
    AppState.catalogPagination.page = totalPages;
  }
  const currentPage = AppState.catalogPagination.page;

  // Calculate slice range for active page
  const startIdx = (currentPage - 1) * pageSize;
  const endIdx = isAll ? totalFiltered : Math.min(startIdx + pageSize, totalFiltered);
  const pageItems = list.slice(startIdx, endIdx);

  // Update Count Badge
  if (DOM.catalogCountInfo) {
    if (totalFiltered === 0) {
      DOM.catalogCountInfo.textContent = 'Showing 0 items';
    } else {
      DOM.catalogCountInfo.textContent = `Showing ${startIdx + 1}–${endIdx} of ${totalFiltered} items`;
    }
  }

  // Render Pagination Bar
  renderCatalogPaginationBar(currentPage, totalPages, totalFiltered);

  if (totalFiltered === 0) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 48px 0; color: var(--text-muted);">
        <p style="font-size: 14.5px; font-weight: 600; color: var(--text-secondary);">No products match your criteria</p>
        <p style="font-size: 12px; margin-top: 6px;">Try adjusting filters, clearing search, or selecting another category.</p>
      </div>
    `;
    return;
  }

  pageItems.forEach(p => {
    const card = document.createElement('div');
    const isOutOfStock = p.stock <= 0;
    const isLowStock = p.stock > 0 && p.stock <= 15;
    card.className = `product-card ${isOutOfStock ? 'out-of-stock' : ''} ${isLowStock ? 'card-low-stock' : ''}`;

    let stockTagClass = 'in-stock';
    let stockLabel = 'In Stock';
    if (isOutOfStock) {
      stockTagClass = 'sold-out';
      stockLabel = 'Sold Out';
    } else if (isLowStock) {
      stockTagClass = 'low-stock';
      stockLabel = `Low (${p.stock})`;
    }

    card.innerHTML = `
      <div>
        <div class="card-top">
          <span class="product-barcode-pill">${p.barcode || '#' + p.id}</span>
          <span class="stock-tag ${stockTagClass}"><span class="badge-dot"></span>${stockLabel}</span>
        </div>
        <div class="product-name">${escapeHtml(p.name)}</div>
        <div class="product-category-label">
          <span class="product-card-icon">${getIconSvg(p.icon || p.category)}</span>
          <span>${escapeHtml(p.category || 'General')}</span>
        </div>
      </div>
      <div class="card-bottom">
        <span class="product-price tabular-num">${formatMoney(p.price)}</span>
        <span class="product-units tabular-num" style="${isLowStock ? 'color: var(--accent-amber); font-weight: 700;' : (isOutOfStock ? 'color: var(--accent-rose); font-weight: 700;' : '')}">
          ${isOutOfStock ? 'Sold Out' : (isLowStock ? `Low: ${p.stock} left` : `${p.stock} left`)}
        </span>
      </div>
    `;

    if (!isOutOfStock) {
      card.addEventListener('click', () => {
        animateCardClick(card);
        addToCart(p);
      });
    }

    container.appendChild(card);
  });
}

function renderCatalogPaginationBar(currentPage, totalPages, totalItems) {
  if (!DOM.catalogPaginationBar) return;

  if (totalItems <= 12 && totalPages <= 1) {
    DOM.catalogPaginationBar.style.display = 'none';
    return;
  }
  DOM.catalogPaginationBar.style.display = 'flex';

  if (DOM.btnCatalogPrev) {
    DOM.btnCatalogPrev.disabled = currentPage <= 1;
  }
  if (DOM.btnCatalogNext) {
    DOM.btnCatalogNext.disabled = currentPage >= totalPages;
  }

  if (DOM.catalogPageNumbers) {
    DOM.catalogPageNumbers.innerHTML = '';
    
    const maxButtons = 5;
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
    if (endPage - startPage < maxButtons - 1) {
      startPage = Math.max(1, endPage - maxButtons + 1);
    }

    if (startPage > 1) {
      DOM.catalogPageNumbers.appendChild(createPageBtn(1, currentPage));
      if (startPage > 2) {
        const ell = document.createElement('span');
        ell.className = 'page-num-ellipsis';
        ell.textContent = '…';
        DOM.catalogPageNumbers.appendChild(ell);
      }
    }

    for (let i = startPage; i <= endPage; i++) {
      DOM.catalogPageNumbers.appendChild(createPageBtn(i, currentPage));
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        const ell = document.createElement('span');
        ell.className = 'page-num-ellipsis';
        ell.textContent = '…';
        DOM.catalogPageNumbers.appendChild(ell);
      }
      DOM.catalogPageNumbers.appendChild(createPageBtn(totalPages, currentPage));
    }
  }
}

function createPageBtn(pageNum, activePage) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = `page-num-btn ${pageNum === activePage ? 'active' : ''}`;
  btn.textContent = pageNum;
  btn.addEventListener('click', () => {
    AppState.catalogPagination.page = pageNum;
    renderProducts();
    const container = document.querySelector('.product-grid-container');
    if (container) container.scrollTop = 0;
  });
  return btn;
}

function animateCardClick(element) {
  if (window.gsap) {
    gsap.fromTo(element, 
      { scale: 0.96 }, 
      { scale: 1, duration: 0.15, ease: 'power2.out' }
    );
  }
}

// --- Cart Operations ---
function addToCart(product, modifiers = [], notes = '') {
  const existing = AppState.cart.find(item => 
    item.id === product.id && 
    JSON.stringify(item.modifiers) === JSON.stringify(modifiers) && 
    item.notes === notes
  );

  if (existing) {
    if (existing.qty + 1 > product.stock) {
      showToast(`Stock limit (${product.stock}) reached for ${product.name}.`, true);
      return;
    }
    existing.qty += 1;
    existing.total = Math.round(existing.qty * existing.unitPrice * 100) / 100;
  } else {
    if (product.stock <= 0) {
      showToast(`${product.name} is out of stock.`, true);
      return;
    }

    const modSum = modifiers.reduce((acc, m) => acc + m.price, 0);
    const unitPrice = Math.round((product.price + modSum) * 100) / 100;

    AppState.cart.push({
      id: product.id,
      name: product.name,
      basePrice: product.price,
      unitPrice: unitPrice,
      stock: product.stock,
      available_modifiers: product.available_modifiers || [],
      modifiers: modifiers,
      notes: notes,
      qty: 1,
      total: unitPrice
    });
  }

  renderCart();
}

function updateCartQty(index, delta) {
  const item = AppState.cart[index];
  if (!item) return;

  const newQty = item.qty + delta;
  if (newQty <= 0) {
    removeFromCart(index);
    return;
  }

  if (newQty > item.stock) {
    showToast(`Only ${item.stock} available in stock.`, true);
    return;
  }

  item.qty = newQty;
  item.total = Math.round(item.qty * item.unitPrice * 100) / 100;
  renderCart();
}

function removeFromCart(index) {
  AppState.cart.splice(index, 1);
  renderCart();
}

function clearCart() {
  if (AppState.cart.length === 0) return;
  AppState.cart = [];
  renderCart();
  generateTicketId();
}

function renderCart() {
  const container = DOM.cartItemsContainer;
  const items = AppState.cart;

  if (items.length === 0) {
    DOM.cartEmptyState.style.display = 'flex';
    DOM.btnProceedPayment.disabled = true;
    DOM.btnHoldOrder.disabled = true;
    DOM.cartCountBadge.textContent = '0 items';
    DOM.cartItemCountSummary.textContent = '0 items';
    updateFinancialDisplay(0.0);
    container.querySelectorAll('.cart-item-row').forEach(r => r.remove());
    return;
  }

  DOM.cartEmptyState.style.display = 'none';
  DOM.btnProceedPayment.disabled = false;
  DOM.btnHoldOrder.disabled = false;

  const totalItemCount = items.reduce((acc, curr) => acc + curr.qty, 0);
  DOM.cartCountBadge.textContent = `${totalItemCount} item${totalItemCount === 1 ? '' : 's'}`;
  DOM.cartItemCountSummary.textContent = `${totalItemCount} item${totalItemCount === 1 ? '' : 's'}`;

  container.querySelectorAll('.cart-item-row').forEach(r => r.remove());

  let subtotal = 0.0;

  items.forEach((item, index) => {
    subtotal += item.total;
    const row = document.createElement('div');
    row.className = 'cart-item-row';

    let tagsHtml = '';
    if (item.modifiers && item.modifiers.length > 0) {
      tagsHtml += item.modifiers.map(m => 
        `<span class="modifier-tag">+ ${escapeHtml(m.name)}${m.price > 0 ? ' (+' + formatMoney(m.price) + ')' : ''}</span>`
      ).join(' ');
    }
    if (item.notes) {
      tagsHtml += `<span class="cart-note-tag">&bull; Note: ${escapeHtml(item.notes)}</span>`;
    }

    row.innerHTML = `
      <div class="cart-item-primary">
        <div class="item-info">
          <span class="item-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</span>
          <span class="item-rate">${formatMoney(item.unitPrice)} each</span>
        </div>
        <div class="item-stepper">
          <button class="step-btn minus-btn" aria-label="Decrease quantity">-</button>
          <span class="step-qty tabular-num">${item.qty}</span>
          <button class="step-btn plus-btn" aria-label="Increase quantity">+</button>
        </div>
        <span class="item-total-price tabular-num">${formatMoney(item.total)}</span>
        <button class="item-remove-btn" aria-label="Remove item" title="Remove line item">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      <div class="cart-item-meta">
        <div class="cart-item-tags">
          ${tagsHtml || '<span style="color: var(--text-muted); font-size: 11px;">Standard prep</span>'}
        </div>
        <button class="btn-edit-modifiers" type="button">Customize</button>
      </div>
    `;

    row.querySelector('.minus-btn').addEventListener('click', () => updateCartQty(index, -1));
    row.querySelector('.plus-btn').addEventListener('click', () => updateCartQty(index, 1));
    row.querySelector('.item-remove-btn').addEventListener('click', () => removeFromCart(index));
    row.querySelector('.btn-edit-modifiers').addEventListener('click', () => openModifierModal(index));

    container.appendChild(row);
  });

  updateFinancialDisplay(subtotal);
}

function updateFinancialDisplay(subtotal) {
  const prevTotal = AppState.activeTotal;
  AppState.activeSubtotal = subtotal;

  const taxEnabled = AppState.settings.tax_enabled;
  const taxRate = taxEnabled ? AppState.settings.tax_rate : 0.0;
  const tax = taxEnabled ? Math.round(subtotal * (taxRate / 100) * 100) / 100 : 0.0;
  const grandTotal = Math.round((subtotal + tax) * 100) / 100;

  AppState.activeTax = tax;
  AppState.activeTotal = grandTotal;

  DOM.subtotalAmount.textContent = formatMoney(subtotal);
  DOM.taxAmount.textContent = formatMoney(tax);

  if (window.gsap) {
    const dummy = { val: prevTotal };
    gsap.to(dummy, {
      val: grandTotal,
      duration: 0.25,
      ease: 'power1.out',
      onUpdate: () => {
        DOM.totalAmount.textContent = formatMoney(dummy.val);
      }
    });
  } else {
    DOM.totalAmount.textContent = formatMoney(grandTotal);
  }
}

// --- Park / Hold Order Flow ---
function holdCurrentOrder() {
  if (AppState.cart.length === 0) return;

  const heldOrder = {
    ticketId: DOM.ticketId.textContent,
    cart: JSON.parse(JSON.stringify(AppState.cart)),
    subtotal: AppState.activeSubtotal,
    tax: AppState.activeTax,
    total: AppState.activeTotal,
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  };

  AppState.parkedOrders.push(heldOrder);
  clearCart();
  updateParkedBadge();
  showToast(`Order ${heldOrder.ticketId} parked successfully.`);
}

function updateParkedBadge() {
  const count = AppState.parkedOrders.length;
  DOM.parkedOrderCount.textContent = count;
  DOM.btnRecallOrder.style.display = count > 0 ? 'inline-flex' : 'none';
}

function openParkedOrdersModal() {
  const container = DOM.parkedOrdersList;
  container.innerHTML = '';

  if (AppState.parkedOrders.length === 0) {
    container.innerHTML = `<span style="text-align: center; color: var(--text-muted); padding: 24px;">No parked orders currently held.</span>`;
    return;
  }

  AppState.parkedOrders.forEach((order, index) => {
    const card = document.createElement('div');
    card.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; background: var(--bg-surface-subtle); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);';
    card.innerHTML = `
      <div>
        <div style="font-weight: 700; font-size: 14px;">${order.ticketId} <span style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">(${order.timestamp})</span></div>
        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">${order.cart.length} items &bull; Total: ${formatMoney(order.total)}</div>
      </div>
      <div style="display: flex; gap: 8px;">
        <button type="button" class="btn btn-secondary discard-parked-btn" style="padding: 6px 10px; font-size: 12px;">Discard</button>
        <button type="button" class="btn btn-primary resume-parked-btn" style="padding: 6px 12px; font-size: 12px;">Resume</button>
      </div>
    `;

    card.querySelector('.resume-parked-btn').addEventListener('click', () => {
      AppState.cart = order.cart;
      DOM.ticketId.textContent = order.ticketId;
      AppState.parkedOrders.splice(index, 1);
      updateParkedBadge();
      closeModal(DOM.parkedOrdersModal, DOM.parkedOrdersModalCard);
      renderCart();
      showToast(`Resumed order ${order.ticketId}.`);
    });

    card.querySelector('.discard-parked-btn').addEventListener('click', () => {
      AppState.parkedOrders.splice(index, 1);
      updateParkedBadge();
      openParkedOrdersModal();
      showToast(`Discarded order ${order.ticketId}.`);
    });

    container.appendChild(card);
  });

  openModal(DOM.parkedOrdersModal, DOM.parkedOrdersModalCard);
}

// --- Item Modifiers Flow ---
function openModifierModal(cartIndex) {
  AppState.editingCartItemIndex = cartIndex;
  const item = AppState.cart[cartIndex];
  if (!item) return;

  DOM.modifierItemTitle.textContent = `Customize: ${item.name}`;
  DOM.modifierItemBasePrice.textContent = `Base Unit Price: ${formatMoney(item.basePrice)}`;
  DOM.modifierItemNotes.value = item.notes || '';

  const container = DOM.modifiersSelectionList;
  container.innerHTML = '';

  const avail = item.available_modifiers || [];
  if (avail.length === 0) {
    container.innerHTML = `<span style="font-size: 12px; color: var(--text-muted);">No preset modifiers for this item. You can still add special preparation notes below.</span>`;
  } else {
    avail.forEach((mod) => {
      const isSelected = item.modifiers.some(m => m.name === mod.name);
      const label = document.createElement('label');
      label.className = `modifier-checkbox-label ${isSelected ? 'selected' : ''}`;
      label.innerHTML = `
        <div class="mod-info">
          <input type="checkbox" value="${escapeHtml(mod.name)}" data-price="${mod.price}" ${isSelected ? 'checked' : ''} style="accent-color: var(--accent-primary);">
          <span style="font-size: 13.5px; font-weight: 600;">${escapeHtml(mod.name)}</span>
        </div>
        <span class="mod-price tabular-num">${mod.price > 0 ? '+ ' + formatMoney(mod.price) : 'Free'}</span>
      `;

      label.querySelector('input').addEventListener('change', (e) => {
        if (e.target.checked) {
          label.classList.add('selected');
        } else {
          label.classList.remove('selected');
        }
      });

      container.appendChild(label);
    });
  }

  openModal(DOM.modifierModal, DOM.modifierModalCard);
}

function handleSaveModifiers() {
  const index = AppState.editingCartItemIndex;
  if (index === null || !AppState.cart[index]) {
    closeModal(DOM.modifierModal, DOM.modifierModalCard);
    return;
  }

  const item = AppState.cart[index];
  const selectedMods = [];
  DOM.modifiersSelectionList.querySelectorAll('input:checked').forEach(cb => {
    selectedMods.push({
      name: cb.value,
      price: parseFloat(cb.getAttribute('data-price')) || 0.0
    });
  });

  const notes = DOM.modifierItemNotes.value.trim();

  item.modifiers = selectedMods;
  item.notes = notes;

  const modSum = selectedMods.reduce((acc, m) => acc + m.price, 0);
  item.unitPrice = Math.round((item.basePrice + modSum) * 100) / 100;
  item.total = Math.round(item.unitPrice * item.qty * 100) / 100;

  closeModal(DOM.modifierModal, DOM.modifierModalCard);
  renderCart();
  showToast(`Updated customization for ${item.name}.`);
}

// --- Barcode Wedge Scanner Listener ---
let barcodeBuffer = '';
let lastKeyTime = 0;

function setupBarcodeWedgeScanner() {
  window.addEventListener('keydown', (e) => {
    const activeEl = document.activeElement;
    if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA')) {
      if (e.key === 'Enter' && activeEl === DOM.barcodeManualInput) {
        e.preventDefault();
        handleManualBarcodeLookup();
      }
      return;
    }

    const currentTime = Date.now();
    const diff = currentTime - lastKeyTime;
    lastKeyTime = currentTime;

    if (diff > 50) {
      barcodeBuffer = '';
    }

    if (e.key === 'Enter') {
      if (barcodeBuffer.length >= 2) {
        e.preventDefault();
        resolveBarcodeScan(barcodeBuffer);
        barcodeBuffer = '';
      }
    } else if (e.key.length === 1) {
      barcodeBuffer += e.key;
    }
  });
}

async function resolveBarcodeScan(code) {
  const cleanCode = code.trim();
  if (!cleanCode) return;

  // If scanning a transaction QR code from a printed receipt
  if (cleanCode.startsWith('TX-')) {
    try {
      const res = await API.request(`/api/receipt/${cleanCode}`);
      if (res && res.receipt) {
        openReceiptModal(res.receipt);
        showToast(`Retrieved transaction receipt: ${cleanCode}`, false, true);
        return;
      }
    } catch (e) {
      showToast(`Transaction receipt ${cleanCode} not found.`, true);
      return;
    }
  }

  try {
    const product = await API.lookupBarcode(cleanCode);
    if (product) {
      addToCart(product);
      showToast(`Scanned: ${product.name} (#${cleanCode})`, false, true);
    } else {
      showToast(`Barcode "${cleanCode}" not found in catalog.`, true);
    }
  } catch (err) {
    showToast(`Scan error: ${err.message}`, true);
  }
}

function handleManualBarcodeLookup() {
  const code = DOM.barcodeManualInput.value.trim();
  if (!code) return;

  stopCameraScanner();
  resolveBarcodeScan(code);
  DOM.barcodeManualInput.value = '';
  closeModal(DOM.barcodeModal, DOM.barcodeModalCard);
}

// --- Phone Camera Barcode Scanner Subsystem ---
let cameraMediaStream = null;
let cameraDetectorTimer = null;

async function startCameraScanner() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showToast('Camera API is not supported on this device/browser.', true);
    return;
  }

  try {
    if (DOM.btnToggleCameraText) DOM.btnToggleCameraText.textContent = 'Requesting Camera...';
    cameraMediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 1280 },
        height: { ideal: 720 }
      }
    });

    if (DOM.cameraScannerVideo) {
      DOM.cameraScannerVideo.srcObject = cameraMediaStream;
      DOM.cameraScannerVideo.style.display = 'block';
    }
    if (DOM.cameraScannerReticle) DOM.cameraScannerReticle.style.display = 'block';
    if (DOM.barcodeDefaultPlaceholder) DOM.barcodeDefaultPlaceholder.style.display = 'none';
    if (DOM.btnToggleCameraText) DOM.btnToggleCameraText.textContent = 'Stop Phone Camera';
    if (DOM.barcodeScannerStatusNote) {
      DOM.barcodeScannerStatusNote.textContent = 'Camera active. Center barcode inside viewfinder.';
    }

    if ('BarcodeDetector' in window) {
      const barcodeDetector = new BarcodeDetector({
        formats: ['ean_13', 'code_128', 'code_39', 'qr_code', 'upc_a', 'upc_e']
      });

      cameraDetectorTimer = setInterval(async () => {
        if (!cameraMediaStream || !DOM.cameraScannerVideo || DOM.cameraScannerVideo.readyState < 2) return;
        try {
          const detectedBarcodes = await barcodeDetector.detect(DOM.cameraScannerVideo);
          if (detectedBarcodes && detectedBarcodes.length > 0) {
            const scannedCode = detectedBarcodes[0].rawValue;
            if (navigator.vibrate) navigator.vibrate(100);
            stopCameraScanner();
            closeModal(DOM.barcodeModal, DOM.barcodeModalCard);
            resolveBarcodeScan(scannedCode);
          }
        } catch (err) {}
      }, 250);
    } else {
      if (DOM.barcodeScannerStatusNote) {
        DOM.barcodeScannerStatusNote.textContent = 'Viewfinder active. Tap "Snap Photo" or enter SKU to decode.';
      }
    }
  } catch (err) {
    console.warn('Camera access denied or unavailable:', err);
    showToast('Camera permission denied or camera not found.', true);
    stopCameraScanner();
  }
}

function stopCameraScanner() {
  if (cameraDetectorTimer) {
    clearInterval(cameraDetectorTimer);
    cameraDetectorTimer = null;
  }
  if (cameraMediaStream) {
    cameraMediaStream.getTracks().forEach(track => track.stop());
    cameraMediaStream = null;
  }
  if (DOM.cameraScannerVideo) {
    DOM.cameraScannerVideo.srcObject = null;
    DOM.cameraScannerVideo.style.display = 'none';
  }
  if (DOM.cameraScannerReticle) {
    DOM.cameraScannerReticle.style.display = 'none';
  }
  if (DOM.barcodeDefaultPlaceholder) {
    DOM.barcodeDefaultPlaceholder.style.display = 'flex';
  }
  if (DOM.btnToggleCameraText) {
    DOM.btnToggleCameraText.textContent = 'Start Phone Camera';
  }
  if (DOM.barcodeScannerStatusNote) {
    DOM.barcodeScannerStatusNote.textContent = 'Hardware wedge active or click below to launch phone camera';
  }
}

function toggleCameraScanner() {
  if (cameraMediaStream) {
    stopCameraScanner();
  } else {
    startCameraScanner();
  }
}

async function handlePhoneImageSnap(file) {
  if (!file) return;

  if (!('BarcodeDetector' in window)) {
    showToast('BarcodeDetector not available. Enter barcode number directly.', true);
    return;
  }

  try {
    showToast('Analyzing barcode photo...');
    const bitmap = await createImageBitmap(file);
    const detector = new BarcodeDetector({
      formats: ['ean_13', 'code_128', 'code_39', 'qr_code', 'upc_a', 'upc_e']
    });
    const detected = await detector.detect(bitmap);
    if (detected && detected.length > 0) {
      const code = detected[0].rawValue;
      if (navigator.vibrate) navigator.vibrate(100);
      stopCameraScanner();
      closeModal(DOM.barcodeModal, DOM.barcodeModalCard);
      resolveBarcodeScan(code);
    } else {
      showToast('No barcode detected in photo. Try higher contrast.', true);
    }
  } catch (err) {
    showToast('Photo decode error: ' + err.message, true);
  }
}

// --- In-App Delete Product Flow (100% Reliable, Replaces Browser Confirm) ---
function triggerDeleteProduct(product) {
  AppState.productPendingDelete = product;
  DOM.deleteConfirmMessage.innerHTML = `Are you sure you want to permanently delete <strong>${escapeHtml(product.name)}</strong> (ID #${product.id})?`;
  openModal(DOM.deleteConfirmModal, DOM.deleteConfirmModalCard);
}

async function confirmDeleteProduct() {
  if (!AppState.productPendingDelete) return;
  const p = AppState.productPendingDelete;
  DOM.btnConfirmDelete.disabled = true;
  DOM.btnConfirmDelete.textContent = 'Deleting...';

  try {
    await API.deleteProduct(p.id);
    closeModal(DOM.deleteConfirmModal, DOM.deleteConfirmModalCard);
    showToast(`Product "${p.name}" deleted successfully.`);
    await loadCatalog();
    renderInventoryTable();
  } catch (err) {
    showToast(`Failed to delete: ${err.message}`, true);
  } finally {
    DOM.btnConfirmDelete.disabled = false;
    DOM.btnConfirmDelete.textContent = 'Delete Product';
    AppState.productPendingDelete = null;
  }
}

// --- Edit Product Flow ---
function triggerEditProduct(product) {
  DOM.editProdId.value = product.id;
  DOM.editProdName.value = product.name;
  DOM.editProdCategory.value = product.category || '';
  DOM.editProdPrice.value = product.price.toFixed(2);
  DOM.editProdStock.value = product.stock;
  DOM.editProdBarcode.value = product.barcode || '';

  const activeIcon = product.icon || inferIconFromCategory(product.category);
  populateIconPicker(DOM.editProdIconGrid, DOM.editProdIcon, DOM.editProdSelectedIconLabel, activeIcon);

  openModal(DOM.editProductModal, DOM.editProductModalCard);
  setTimeout(() => DOM.editProdName.focus(), 100);
}

async function handleSaveEditedProduct(e) {
  e.preventDefault();
  const id = parseInt(DOM.editProdId.value);
  const name = DOM.editProdName.value.trim();
  const category = DOM.editProdCategory.value.trim();
  const price = parseFloat(DOM.editProdPrice.value);
  const stock = parseInt(DOM.editProdStock.value);
  const barcode = DOM.editProdBarcode.value.trim();
  const icon = DOM.editProdIcon ? DOM.editProdIcon.value : undefined;

  if (!name || isNaN(price) || isNaN(stock)) {
    showToast('Please enter valid product details.', true);
    return;
  }

  try {
    await API.updateProduct(id, { name, category, price, stock, barcode: barcode || undefined, icon });
    closeModal(DOM.editProductModal, DOM.editProductModalCard);
    showToast(`Updated product "${name}".`);
    await loadCatalog();
    renderInventoryTable();
  } catch (err) {
    showToast(`Update failed: ${err.message}`, true);
  }
}

// --- Export Catalog to CSV ---
function exportCatalogToCsv() {
  if (!AppState.products.length) {
    showToast('No products to export.', true);
    return;
  }

  const headers = ['ID', 'Barcode', 'Name', 'Category', 'Price', 'Stock'];
  const rows = AppState.products.map(p => [
    p.id,
    `"${(p.barcode || '').replace(/"/g, '""')}"`,
    `"${p.name.replace(/"/g, '""')}"`,
    `"${(p.category || 'General').replace(/"/g, '""')}"`,
    p.price.toFixed(2),
    p.stock
  ]);

  const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `inventory_catalog_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast('Inventory exported to CSV.');
}

// --- Checkout Modal Flow ---
function openCheckoutModal() {
  if (AppState.cart.length === 0) return;

  const due = AppState.activeTotal;
  DOM.checkoutDueDisplay.textContent = formatMoney(due);
  DOM.tenderInput.value = due.toFixed(2);

  renderQuickCashButtons(due);
  validateTender();
  openModal(DOM.checkoutModal, DOM.checkoutModalCard);

  setTimeout(() => {
    DOM.tenderInput.focus();
    DOM.tenderInput.select();
  }, 100);
}

function renderQuickCashButtons(due) {
  const container = DOM.quickCashGrid;
  container.innerHTML = '';

  const sym = AppState.settings?.currency_symbol || '₱';

  const suggestions = [
    { label: 'Exact Cash', value: due }
  ];

  // Common Philippine Peso banknotes
  const phpNotes = [20, 50, 100, 200, 500, 1000];
  const higherNotes = phpNotes.filter(n => n > due);

  const next50 = Math.ceil(due / 50) * 50;
  const next100 = Math.ceil(due / 100) * 100;
  const next500 = Math.ceil(due / 500) * 500;
  const next1000 = Math.ceil(due / 1000) * 1000;

  const candidateValues = Array.from(new Set([
    ...higherNotes,
    next50,
    next100,
    next500,
    next1000
  ])).filter(v => v >= due).sort((a, b) => a - b);

  candidateValues.slice(0, 4).forEach(val => {
    if (val !== due) {
      suggestions.push({
        label: `${sym}${val.toLocaleString('en-PH')}`,
        value: val
      });
    }
  });

  if (suggestions.length < 5) {
    [500, 1000].forEach(note => {
      if (!suggestions.some(s => s.value === note)) {
        suggestions.push({
          label: `${sym}${note.toLocaleString('en-PH')}`,
          value: note
        });
      }
    });
  }

  suggestions.slice(0, 5).forEach(d => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn-denomination';
    btn.textContent = d.label;
    btn.addEventListener('click', () => {
      DOM.tenderInput.value = d.value.toFixed(2);
      validateTender();
    });
    container.appendChild(btn);
  });
}

function validateTender() {
  const due = AppState.activeTotal;
  const tender = parseFloat(DOM.tenderInput.value) || 0.0;

  if (tender < due) {
    const short = due - tender;
    DOM.changeFeedbackBox.className = 'change-feedback-box insufficient';
    DOM.changeBoxLabel.textContent = 'Remaining Due';
    DOM.changeAmountDisplay.textContent = formatMoney(short);
    DOM.btnCompleteSale.disabled = true;
    DOM.btnCompleteSale.style.opacity = '0.5';
  } else {
    const change = tender - due;
    DOM.changeFeedbackBox.className = 'change-feedback-box';
    DOM.changeBoxLabel.textContent = 'Change Due';
    DOM.changeAmountDisplay.textContent = formatMoney(change);
    DOM.btnCompleteSale.disabled = false;
    DOM.btnCompleteSale.style.opacity = '1';
  }
}

async function handleCompleteSale() {
  const due = AppState.activeTotal;
  const tender = parseFloat(DOM.tenderInput.value) || 0.0;

  if (tender < due) {
    showToast('Tender is less than total due.', true);
    return;
  }

  DOM.btnCompleteSale.disabled = true;
  DOM.btnCompleteSale.textContent = 'Processing...';

  try {
    const itemsPayload = AppState.cart.map(i => ({
      id: i.id,
      qty: i.qty,
      modifiers: i.modifiers || [],
      notes: i.notes || ''
    }));

    const cashierName = (DOM.checkoutCashierInput ? DOM.checkoutCashierInput.value.trim() : '') ||
                        (DOM.topbarCashierName ? DOM.topbarCashierName.value.trim() : '') ||
                        localStorage.getItem('pos_cashier_name') ||
                        'Maria Santos';

    localStorage.setItem('pos_cashier_name', cashierName);
    if (DOM.topbarCashierName) DOM.topbarCashierName.value = cashierName;
    if (DOM.checkoutCashierInput) DOM.checkoutCashierInput.value = cashierName;

    const tx = await API.checkout(itemsPayload, tender, cashierName);

    closeModal(DOM.checkoutModal, DOM.checkoutModalCard);
    clearCart();
    await loadCatalog();

    openReceiptModal(tx);
    showToast('Transaction settled successfully.');
  } catch (err) {
    showToast('Checkout failed: ' + err.message, true);
  } finally {
    DOM.btnCompleteSale.disabled = false;
    DOM.btnCompleteSale.textContent = 'Complete Transaction';
  }
}

// --- Receipt Modal Flow ---
function openReceiptModal(tx) {
  DOM.receiptPaper.textContent = tx.receipt_text;
  DOM.receiptQrTxId.textContent = tx.id;

  const qrContainer = document.getElementById('receiptQrCode');
  if (qrContainer) {
    qrContainer.innerHTML = '';
    if (typeof QRCode !== 'undefined') {
      try {
        new QRCode(qrContainer, {
          text: tx.id,
          width: 96,
          height: 96,
          colorDark: '#0B0F19',
          colorLight: '#FFFFFF',
          correctLevel: QRCode.CorrectLevel.M
        });
      } catch (err) {
        console.error('QR generation error:', err);
      }
    }
  }

  openModal(DOM.receiptModal, DOM.receiptModalCard);
}

// Cashier Identity Synchronizer
function syncCashierUI(name) {
  const cashierName = name || localStorage.getItem('pos_cashier_name') || 'Maria Santos';
  localStorage.setItem('pos_cashier_name', cashierName);
  if (DOM.topbarCashierName) DOM.topbarCashierName.value = cashierName;
  if (DOM.checkoutCashierInput) DOM.checkoutCashierInput.value = cashierName;
  if (DOM.settingsCashierName) DOM.settingsCashierName.value = cashierName;
  if (DOM.dashboardCashierDisplay) DOM.dashboardCashierDisplay.textContent = cashierName;
  if (DOM.dashboardActiveCashierName) DOM.dashboardActiveCashierName.textContent = cashierName;
}

// --- Back-Office Console ---
function openConsoleModal(targetTab = 'tab-inventory') {
  syncCashierUI();
  populateIconPicker(DOM.newProdIconGrid, DOM.newProdIcon, DOM.newProdSelectedIconLabel, 'coffee');
  switchConsoleTab(targetTab);
  renderInventoryTable();
  renderAnalyticsTab();
  openModal(DOM.consoleModal, DOM.consoleModalCard);
}

function switchConsoleTab(tabId) {
  const navItems = DOM.consoleModal.querySelectorAll('.console-nav-item');
  navItems.forEach(btn => {
    const isActive = btn.getAttribute('data-tab') === tabId;
    btn.classList.toggle('active', isActive);
    if (isActive) {
      DOM.consolePageTitle.textContent = btn.getAttribute('data-title');
      DOM.consolePageDesc.textContent = btn.getAttribute('data-desc');
    }
  });

  if (DOM.consoleHeaderActions) {
    DOM.consoleHeaderActions.style.display = tabId === 'tab-inventory' ? 'flex' : 'none';
  }

  const panes = DOM.consoleModal.querySelectorAll('.console-tab-pane');
  panes.forEach(pane => {
    const isTarget = pane.id === tabId;
    pane.classList.toggle('active', isTarget);
    if (isTarget && window.gsap) {
      gsap.fromTo(pane, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.18, ease: 'power2.out' });
    }
  });

  if (tabId === 'tab-settings') {
    renderStorageSyncDashboard(AppState.lastSync);
  }
}

function renderInventoryTable() {
  const tbody = DOM.inventoryTableBody;
  if (!tbody) return;

  tbody.innerHTML = '';
  const filter = (DOM.inventoryFilterInput?.value || '').toLowerCase().trim();
  const categoryFilter = AppState.inventoryCategoryFilter || 'all';
  const stockFilter = AppState.inventoryStockFilter || 'all';

  // Compute live stock health metrics
  const totalCount = AppState.products.length;
  const inStockCount = AppState.products.filter(p => p.stock > 15).length;
  const lowStockCount = AppState.products.filter(p => p.stock > 0 && p.stock <= 15).length;
  const outOfStockCount = AppState.products.filter(p => p.stock <= 0).length;

  // Update summary ribbon KPIs
  if (DOM.kpiCountAll) DOM.kpiCountAll.textContent = totalCount;
  if (DOM.kpiCountInStock) DOM.kpiCountInStock.textContent = inStockCount;
  if (DOM.kpiCountLowStock) DOM.kpiCountLowStock.textContent = lowStockCount;
  if (DOM.kpiCountOutOfStock) DOM.kpiCountOutOfStock.textContent = outOfStockCount;

  // Update sidebar navigation badges
  if (DOM.navInventoryCount) {
    DOM.navInventoryCount.textContent = totalCount;
  }
  if (DOM.navInventoryLowBadge) {
    if (lowStockCount > 0) {
      DOM.navInventoryLowBadge.textContent = `${lowStockCount} Low`;
      DOM.navInventoryLowBadge.style.display = 'inline-block';
    } else {
      DOM.navInventoryLowBadge.style.display = 'none';
    }
  }

  // Populate category filter dropdown if options count changed
  if (DOM.inventoryCategoryFilter) {
    const categories = Array.from(new Set(AppState.products.map(p => p.category || 'General'))).sort();
    const currentVal = DOM.inventoryCategoryFilter.value || 'all';
    DOM.inventoryCategoryFilter.innerHTML = `<option value="all">All Categories (${totalCount})</option>` +
      categories.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
    DOM.inventoryCategoryFilter.value = currentVal;
  }

  // Filter list
  const list = AppState.products.filter(p => {
    const matchesSearch = !filter || 
      p.name.toLowerCase().includes(filter) || 
      String(p.id).includes(filter) || 
      String(p.barcode || '').toLowerCase().includes(filter) ||
      String(p.category || '').toLowerCase().includes(filter);

    const matchesCategory = categoryFilter === 'all' || (p.category || 'General') === categoryFilter;

    let matchesStock = true;
    if (stockFilter === 'in-stock') matchesStock = p.stock > 15;
    else if (stockFilter === 'low-stock') matchesStock = p.stock > 0 && p.stock <= 15;
    else if (stockFilter === 'out-of-stock') matchesStock = p.stock <= 0;

    return matchesSearch && matchesCategory && matchesStock;
  });

  if (DOM.inventoryTableCount) {
    DOM.inventoryTableCount.textContent = list.length;
  }

  if (list.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 48px 24px;">
          <div style="font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">No products match current filters</div>
          <div style="font-size: 12px; color: var(--text-secondary);">Try changing the stock health chip, category dropdown, or search keyword.</div>
        </td>
      </tr>
    `;
    return;
  }

  list.forEach(p => {
    const isOut = p.stock <= 0;
    const isLow = p.stock > 0 && p.stock <= 15;

    let badgeHtml = '';
    let fillClass = 'in-stock';
    let trClass = '';
    let pct = Math.min(100, Math.round((p.stock / 50) * 100));

    if (isOut) {
      badgeHtml = '<span class="badge badge-danger badge-pill"><span class="badge-dot pulse"></span>Out of Stock (0)</span>';
      fillClass = 'out-of-stock';
      trClass = 'row-out-of-stock';
      pct = 0;
    } else if (isLow) {
      badgeHtml = `<span class="badge badge-warning badge-pill"><span class="badge-dot pulse-amber"></span>Low Stock (${p.stock} left)</span>`;
      fillClass = 'low-stock';
      trClass = 'row-low-stock';
    } else {
      badgeHtml = `<span class="badge badge-success badge-pill"><span class="badge-dot"></span>In Stock (${p.stock})</span>`;
      fillClass = 'in-stock';
      trClass = '';
    }

    const tr = document.createElement('tr');
    tr.className = trClass;
    tr.innerHTML = `
      <td class="tabular-num" style="font-family: var(--font-mono); font-weight: 700; color: var(--text-secondary);">#${p.id}</td>
      <td class="tabular-num" style="font-family: var(--font-mono); font-size: 11px;">
        <span class="product-barcode-pill">${escapeHtml(p.barcode || '-')}</span>
      </td>
      <td>
        <div style="display: flex; align-items: center; gap: 10px;">
          <div class="table-sku-icon">${getIconSvg(p.icon || p.category)}</div>
          <div>
            <div style="font-weight: 600; color: var(--text-primary); font-size: 13.5px; line-height: 1.25;">${escapeHtml(p.name)}</div>
            <div style="font-size: 11px; color: var(--text-muted); font-family: var(--font-mono); margin-top: 2px;">${escapeHtml(p.category || 'General')}</div>
          </div>
        </div>
      </td>
      <td class="tabular-num" style="font-weight: 700; font-size: 13.5px;">${formatMoney(p.price)}</td>
      <td>
        <div class="stock-meter-wrap">
          <div>${badgeHtml}</div>
          <div class="stock-meter-bar">
            <div class="stock-meter-fill ${fillClass}" style="width: ${pct}%;"></div>
          </div>
        </div>
      </td>
      <td>
        <div style="display: flex; align-items: center; gap: 5px; white-space: nowrap;">
          <button type="button" class="btn btn-secondary btn-icon-only dec-stock-btn" style="width: 26px; height: 26px; min-width: 26px; padding: 0; font-size: 13px; line-height: 1;">-</button>
          <input type="number" class="form-input stock-input-${p.id}" value="${p.stock}" min="0" style="width: 52px; height: 30px; padding: 0 4px; font-family: var(--font-mono); text-align: center; font-size: 12px;">
          <button type="button" class="btn btn-secondary btn-icon-only inc-stock-btn" style="width: 26px; height: 26px; min-width: 26px; padding: 0; font-size: 13px; line-height: 1;">+</button>
          <button type="button" class="btn btn-primary btn-icon-only save-stock-btn" title="Save Stock" style="height: 30px; padding: 0 8px; font-size: 11px; white-space: nowrap;">Save</button>
        </div>
      </td>
      <td style="text-align: right;">
        <div class="table-actions-cell" style="white-space: nowrap; justify-content: flex-end;">
          <button class="btn btn-secondary btn-icon-only edit-product-btn" title="Edit Product Details" style="width: 28px; height: 28px; padding: 0; display: inline-flex; align-items: center; justify-content: center;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
          </button>
          <button class="btn btn-danger btn-icon-only delete-product-btn" title="Delete Product" style="width: 28px; height: 28px; padding: 0; display: inline-flex; align-items: center; justify-content: center;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </td>
    `;

    const input = tr.querySelector(`.stock-input-${p.id}`);
    tr.querySelector('.dec-stock-btn').addEventListener('click', () => {
      const v = Math.max(0, parseInt(input.value || 0) - 1);
      input.value = v;
    });
    tr.querySelector('.inc-stock-btn').addEventListener('click', () => {
      const v = parseInt(input.value || 0) + 1;
      input.value = v;
    });

    tr.querySelector('.save-stock-btn').addEventListener('click', async () => {
      const newStock = parseInt(input.value);
      if (isNaN(newStock) || newStock < 0) {
        showToast('Stock must be a positive integer.', true);
        return;
      }
      try {
        await API.updateProduct(p.id, { stock: newStock });
        showToast(`Stock updated for ${p.name}.`);
        await loadCatalog();
        renderInventoryTable();
      } catch (err) {
        showToast(err.message, true);
      }
    });

    tr.querySelector('.edit-product-btn').addEventListener('click', () => triggerEditProduct(p));
    tr.querySelector('.delete-product-btn').addEventListener('click', () => triggerDeleteProduct(p));

    tbody.appendChild(tr);
  });
}

async function handleCreateProduct(e) {
  e.preventDefault();
  const name = document.getElementById('newProdName').value.trim();
  const category = document.getElementById('newProdCategory').value.trim();
  const price = parseFloat(document.getElementById('newProdPrice').value);
  const stock = parseInt(document.getElementById('newProdStock').value);
  const barcode = document.getElementById('newProdBarcode').value.trim();
  const icon = document.getElementById('newProdIcon') ? document.getElementById('newProdIcon').value : 'coffee';

  if (!name || isNaN(price) || isNaN(stock)) {
    showToast('Please provide valid name, price, and stock.', true);
    return;
  }

  try {
    await API.addProduct({ name, category, price, stock, barcode: barcode || undefined, icon });
    DOM.newProductForm.reset();
    populateIconPicker(DOM.newProdIconGrid, DOM.newProdIcon, DOM.newProdSelectedIconLabel, 'coffee');
    DOM.collapsibleAddProduct.classList.remove('open');
    showToast(`Added product "${name}".`);
    await loadCatalog();
    renderInventoryTable();
  } catch (err) {
    showToast('Failed to add product: ' + err.message, true);
  }
}

async function handleSaveSettings(e) {
  e.preventDefault();
  const tax_enabled = DOM.settingsTaxToggle.checked;
  const tax_rate = parseFloat(DOM.settingsTaxRate.value) || 0.0;
  const tax_name = DOM.settingsTaxName.value.trim() || 'Sales Tax';
  const store_name = DOM.settingsStoreName.value.trim() || 'METRO POINT OF SALE';
  const branch = DOM.settingsBranch.value.trim() || 'Terminal 01';
  const phone = DOM.settingsPhone.value.trim();

  try {
    const updated = await API.updateSettings({
      tax_enabled,
      tax_rate,
      tax_name,
      store_name,
      branch,
      phone
    });
    const cashier_name = DOM.settingsCashierName ? DOM.settingsCashierName.value.trim() : '';
    if (cashier_name) {
      syncCashierUI(cashier_name);
    }

    AppState.settings = updated;
    DOM.headerStoreName.textContent = updated.store_name;
    DOM.headerBranch.textContent = `${updated.branch} • Active Shift`;
    updateTaxLabels();
    renderCart();
    showToast('Settings & taxation rules saved.');
  } catch (err) {
    showToast('Failed to update settings: ' + err.message, true);
  }
}

async function renderAnalyticsTab() {
  try {
    const stats = await API.getStats();
    const transactions = await API.getTransactions();

    if (DOM.navOrdersCount) {
      DOM.navOrdersCount.textContent = stats.transaction_count;
    }

    const hasAlerts = stats.low_stock_count > 0;
    DOM.analyticsStatsGrid.innerHTML = `
      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-titles">
            <span class="stat-label">Gross Revenue</span>
            <span class="stat-sublabel">Total Shift Sales</span>
          </div>
          <div class="stat-icon-wrap stat-icon-emerald">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="1" x2="12" y2="23"></line>
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
            </svg>
          </div>
        </div>
        <div class="stat-card-body">
          <span class="stat-value">${formatMoney(stats.total_revenue)}</span>
        </div>
        <div class="stat-card-footer">
          <span class="badge badge-success badge-pill"><span class="badge-dot"></span>Settled</span>
          <span class="stat-footnote">All registers reconciled</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-titles">
            <span class="stat-label">Completed Orders</span>
            <span class="stat-sublabel">Transaction Volume</span>
          </div>
          <div class="stat-icon-wrap stat-icon-primary">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
          </div>
        </div>
        <div class="stat-card-body">
          <span class="stat-value">${stats.transaction_count}</span>
        </div>
        <div class="stat-card-footer">
          <span class="badge badge-primary badge-pill"><span class="badge-dot"></span>100% Success</span>
          <span class="stat-footnote">Audit receipts filed</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-titles">
            <span class="stat-label">Average Basket</span>
            <span class="stat-sublabel">Ticket Benchmark</span>
          </div>
          <div class="stat-icon-wrap stat-icon-indigo">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
          </div>
        </div>
        <div class="stat-card-body">
          <span class="stat-value">${formatMoney(stats.average_ticket)}</span>
        </div>
        <div class="stat-card-footer">
          <span class="badge badge-indigo badge-pill"><span class="badge-dot"></span>Per Customer</span>
          <span class="stat-footnote">Active shift average</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-titles">
            <span class="stat-label">Inventory Health</span>
            <span class="stat-sublabel">Stock Monitor</span>
          </div>
          <div class="stat-icon-wrap ${hasAlerts ? 'stat-icon-amber' : 'stat-icon-emerald'}">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
              <line x1="12" y1="9" x2="12" y2="13"></line>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
          </div>
        </div>
        <div class="stat-card-body">
          <span class="stat-value" style="color: ${hasAlerts ? 'var(--accent-amber)' : 'inherit'};">
            ${stats.low_stock_count}
          </span>
        </div>
        <div class="stat-card-footer">
          ${hasAlerts 
            ? `<span class="badge badge-warning badge-pill"><span class="badge-dot pulse-amber"></span>Action Needed</span><span class="stat-footnote">${stats.low_stock_count} SKUs low</span>`
            : `<span class="badge badge-success badge-pill"><span class="badge-dot"></span>Optimal</span><span class="stat-footnote">All 30 SKUs stocked</span>`
          }
        </div>
      </div>
    `;

    const tbody = DOM.transactionHistoryBody;
    tbody.innerHTML = '';

    if (transactions.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 36px;">No transactions recorded yet.</td>
        </tr>
      `;
    } else {
      transactions.slice(0, 30).forEach(tx => {
        const tr = document.createElement('tr');
        const itemCount = tx.items ? tx.items.reduce((a, b) => a + b.qty, 0) : 0;
        const total = tx.total_due ?? tx.subtotal;
        tr.innerHTML = `
          <td class="tabular-num" style="font-family: var(--font-mono); font-weight: 700; color: var(--text-primary);">${tx.id}</td>
          <td style="font-size: 12px; color: var(--text-secondary);">${tx.timestamp}</td>
          <td style="font-family: var(--font-mono); font-weight: 600; font-size: 11.5px; color: var(--text-primary);">${escapeHtml(tx.cashier || 'Terminal 01')}</td>
          <td><span class="badge badge-neutral">${itemCount} items</span></td>
          <td class="tabular-num">${formatMoney(tx.subtotal)}</td>
          <td class="tabular-num" style="font-weight: 700; color: var(--text-primary); font-size: 14px;">${formatMoney(total)}</td>
          <td><span class="badge badge-success"><span class="badge-dot"></span>Settled</span></td>
          <td style="text-align: right;">
            <button class="btn btn-secondary btn-icon-only view-receipt-btn" title="View Thermal Receipt" style="padding: 6px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
            </button>
          </td>
        `;
        tr.querySelector('.view-receipt-btn').addEventListener('click', () => {
          closeModal(DOM.consoleModal, DOM.consoleModalCard);
          openReceiptModal(tx);
        });
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    console.error('Failed to load analytics:', err);
  }
}

// --- Modal Transitions (GSAP) ---
function openModal(overlay, card) {
  overlay.classList.add('active');
  if (window.gsap) {
    gsap.fromTo(overlay, { opacity: 0 }, { opacity: 1, duration: 0.2 });
    gsap.fromTo(card, 
      { scale: 0.95, y: 15, opacity: 0 }, 
      { scale: 1, y: 0, opacity: 1, duration: 0.25, ease: 'power2.out' }
    );
  }
}

function closeModal(overlay, card) {
  if (window.gsap) {
    gsap.to(card, {
      scale: 0.96,
      opacity: 0,
      duration: 0.15,
      ease: 'power2.in',
      onComplete: () => {
        overlay.classList.remove('active');
      }
    });
  } else {
    overlay.classList.remove('active');
  }
}

// --- Toast Notifications ---
function showToast(message, isError = false, isScan = false) {
  const toast = document.createElement('div');
  let extraClass = '';
  if (isError) extraClass = 'toast-error';
  else if (isScan) extraClass = 'toast-scan';

  toast.className = `toast ${extraClass}`;
  
  let iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
  if (isError) {
    iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
  } else if (isScan) {
    iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 5v4m18-4v4M3 19v-4m18 4v-4M7 9v6m4-6v6m4-6v6"></path></svg>`;
  }

  toast.innerHTML = `${iconSvg}<span>${escapeHtml(message)}</span>`;
  DOM.toastContainer.appendChild(toast);

  if (window.gsap) {
    gsap.from(toast, { y: 20, opacity: 0, duration: 0.2, ease: 'power2.out' });
  }

  setTimeout(() => {
    if (window.gsap) {
      gsap.to(toast, {
        opacity: 0,
        y: 10,
        duration: 0.2,
        onComplete: () => toast.remove()
      });
    } else {
      toast.remove();
    }
  }, 3200);
}

// --- Utilities ---
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// --- Event Listeners Setup ---
function setupEventListeners() {
  // Main search
  DOM.searchInput.addEventListener('input', (e) => {
    AppState.searchQuery = e.target.value;
    DOM.searchClearBtn.classList.toggle('active', Boolean(e.target.value));
    renderProducts();
  });

  DOM.searchClearBtn.addEventListener('click', () => {
    DOM.searchInput.value = '';
    AppState.searchQuery = '';
    DOM.searchClearBtn.classList.remove('active');
    renderProducts();
    DOM.searchInput.focus();
  });

  // Category Bar Scrolling & Nav Buttons
  if (DOM.btnCatScrollLeft) {
    DOM.btnCatScrollLeft.addEventListener('click', () => {
      DOM.categoryBar.scrollBy({ left: -220, behavior: 'smooth' });
    });
  }
  if (DOM.btnCatScrollRight) {
    DOM.btnCatScrollRight.addEventListener('click', () => {
      DOM.categoryBar.scrollBy({ left: 220, behavior: 'smooth' });
    });
  }
  if (DOM.categoryBar) {
    DOM.categoryBar.addEventListener('scroll', updateCategoryScrollButtons, { passive: true });
    DOM.categoryBar.addEventListener('wheel', (e) => {
      if (e.deltaY !== 0) {
        e.preventDefault();
        DOM.categoryBar.scrollLeft += e.deltaY;
        updateCategoryScrollButtons();
      }
    }, { passive: false });
  }

  // Catalog subtoolbar filters, sorting & pagination
  if (DOM.catalogStockFilter) {
    DOM.catalogStockFilter.addEventListener('change', (e) => {
      AppState.catalogStockFilter = e.target.value;
      AppState.catalogPagination.page = 1;
      renderProducts();
    });
  }

  if (DOM.catalogSortSelect) {
    DOM.catalogSortSelect.addEventListener('change', (e) => {
      AppState.catalogSort = e.target.value;
      AppState.catalogPagination.page = 1;
      renderProducts();
    });
  }

  if (DOM.catalogPageSize) {
    DOM.catalogPageSize.addEventListener('change', (e) => {
      AppState.catalogPagination.pageSize = e.target.value;
      AppState.catalogPagination.page = 1;
      renderProducts();
    });
  }

  if (DOM.btnCatalogPrev) {
    DOM.btnCatalogPrev.addEventListener('click', () => {
      if (AppState.catalogPagination.page > 1) {
        AppState.catalogPagination.page--;
        renderProducts();
        const container = document.querySelector('.product-grid-container');
        if (container) container.scrollTop = 0;
      }
    });
  }

  if (DOM.btnCatalogNext) {
    DOM.btnCatalogNext.addEventListener('click', () => {
      if (AppState.catalogPagination.page < AppState.catalogPagination.totalPages) {
        AppState.catalogPagination.page++;
        renderProducts();
        const container = document.querySelector('.product-grid-container');
        if (container) container.scrollTop = 0;
      }
    });
  }

  // Global keyboard shortcuts
  window.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== DOM.searchInput && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
      e.preventDefault();
      DOM.searchInput.focus();
    }
    if (e.key === 'F3') {
      e.preventDefault();
      openModal(DOM.barcodeModal, DOM.barcodeModalCard);
      setTimeout(() => DOM.barcodeManualInput.focus(), 100);
    }
    if (e.key === 'F2') {
      e.preventDefault();
      if (DOM.consoleModal && DOM.consoleModal.classList.contains('active')) {
        closeModal(DOM.consoleModal, DOM.consoleModalCard);
      } else {
        openConsoleModal('tab-inventory');
      }
    }
    if (e.key === 'Escape') {
      stopCameraScanner();
      closeModal(DOM.checkoutModal, DOM.checkoutModalCard);
      closeModal(DOM.receiptModal, DOM.receiptModalCard);
      closeModal(DOM.consoleModal, DOM.consoleModalCard);
      closeModal(DOM.modifierModal, DOM.modifierModalCard);
      closeModal(DOM.barcodeModal, DOM.barcodeModalCard);
      closeModal(DOM.deleteConfirmModal, DOM.deleteConfirmModalCard);
      closeModal(DOM.editProductModal, DOM.editProductModalCard);
      closeModal(DOM.parkedOrdersModal, DOM.parkedOrdersModalCard);
    }
  });

  // Manual storage sync
  if (DOM.btnManualSync) {
    DOM.btnManualSync.addEventListener('click', () => checkLiveSync(true));
  }
  if (DOM.btnForceReloadDisk) {
    DOM.btnForceReloadDisk.addEventListener('click', () => checkLiveSync(true));
  }

  // Cashier Name Synchronization
  syncCashierUI();
  if (DOM.topbarCashierName) {
    DOM.topbarCashierName.addEventListener('change', (e) => {
      const name = e.target.value.trim() || 'Maria Santos';
      syncCashierUI(name);
      showToast(`Active Cashier set to: ${name}`);
    });
  }
  if (DOM.checkoutCashierInput) {
    DOM.checkoutCashierInput.addEventListener('change', (e) => {
      const name = e.target.value.trim() || 'Maria Santos';
      syncCashierUI(name);
    });
  }
  if (DOM.settingsCashierName) {
    DOM.settingsCashierName.addEventListener('change', (e) => {
      const name = e.target.value.trim() || 'Maria Santos';
      syncCashierUI(name);
    });
  }

  // Cart actions
  DOM.clearCartBtn.addEventListener('click', clearCart);
  DOM.btnHoldOrder.addEventListener('click', holdCurrentOrder);
  DOM.btnRecallOrder.addEventListener('click', openParkedOrdersModal);
  DOM.btnCloseParkedOrders.addEventListener('click', () => closeModal(DOM.parkedOrdersModal, DOM.parkedOrdersModalCard));
  DOM.btnProceedPayment.addEventListener('click', openCheckoutModal);

  // Modifiers modal
  DOM.btnSaveModifier.addEventListener('click', handleSaveModifiers);
  DOM.btnCancelModifier.addEventListener('click', () => closeModal(DOM.modifierModal, DOM.modifierModalCard));
  DOM.btnCloseModifier.addEventListener('click', () => closeModal(DOM.modifierModal, DOM.modifierModalCard));

  // Barcode modal & Camera Scanner
  DOM.btnOpenBarcodeModal.addEventListener('click', () => {
    openModal(DOM.barcodeModal, DOM.barcodeModalCard);
    setTimeout(() => DOM.barcodeManualInput.focus(), 100);
  });
  DOM.btnCloseBarcode.addEventListener('click', () => {
    stopCameraScanner();
    closeModal(DOM.barcodeModal, DOM.barcodeModalCard);
  });
  DOM.btnSubmitBarcode.addEventListener('click', handleManualBarcodeLookup);

  if (DOM.btnToggleCameraScanner) {
    DOM.btnToggleCameraScanner.addEventListener('click', toggleCameraScanner);
  }

  if (DOM.btnPhoneSnapBarcode && DOM.phoneCameraFileInput) {
    DOM.btnPhoneSnapBarcode.addEventListener('click', () => DOM.phoneCameraFileInput.click());
    DOM.phoneCameraFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        handlePhoneImageSnap(e.target.files[0]);
      }
    });
  }

  if (DOM.btnCopyPhoneUrl) {
    DOM.btnCopyPhoneUrl.addEventListener('click', () => {
      const url = (DOM.phoneUrlDisplay ? DOM.phoneUrlDisplay.textContent : '') || window.location.href;
      navigator.clipboard.writeText(url).then(() => {
        showToast('Phone connection URL copied to clipboard.');
      }).catch(() => {
        showToast('Open on phone: ' + url);
      });
    });
  }

  document.querySelectorAll('.quick-barcode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const code = btn.getAttribute('data-code');
      DOM.barcodeManualInput.value = code;
      handleManualBarcodeLookup();
    });
  });

  // Delete Confirmation Modal
  DOM.btnConfirmDelete.addEventListener('click', confirmDeleteProduct);
  DOM.btnCancelDelete.addEventListener('click', () => closeModal(DOM.deleteConfirmModal, DOM.deleteConfirmModalCard));
  DOM.btnCloseDeleteConfirm.addEventListener('click', () => closeModal(DOM.deleteConfirmModal, DOM.deleteConfirmModalCard));

  // Edit Product Modal
  DOM.editProductForm.addEventListener('submit', handleSaveEditedProduct);
  DOM.btnCancelEditProduct.addEventListener('click', () => closeModal(DOM.editProductModal, DOM.editProductModalCard));
  DOM.btnCloseEditProduct.addEventListener('click', () => closeModal(DOM.editProductModal, DOM.editProductModalCard));

  // Overhauled Back-Office Console
  DOM.btnOpenConsole.addEventListener('click', () => openConsoleModal('tab-inventory'));
  DOM.btnCloseConsole.addEventListener('click', () => closeModal(DOM.consoleModal, DOM.consoleModalCard));

  DOM.consoleModal.querySelectorAll('.console-nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      switchConsoleTab(targetTab);
    });
  });

  // Collapsible Add Product Form
  if (DOM.btnToggleAddProduct) {
    DOM.btnToggleAddProduct.addEventListener('click', () => {
      DOM.collapsibleAddProduct.classList.toggle('open');
      if (DOM.collapsibleAddProduct.classList.contains('open')) {
        document.getElementById('newProdName').focus();
      }
    });
  }
  if (DOM.btnCloseAddProduct) {
    DOM.btnCloseAddProduct.addEventListener('click', () => DOM.collapsibleAddProduct.classList.remove('open'));
  }
  if (DOM.btnCancelAddProduct) {
    DOM.btnCancelAddProduct.addEventListener('click', () => DOM.collapsibleAddProduct.classList.remove('open'));
  }

  // Export CSV
  if (DOM.btnExportCsv) {
    DOM.btnExportCsv.addEventListener('click', exportCatalogToCsv);
  }

  // Inventory search filter
  if (DOM.inventoryFilterInput) {
    DOM.inventoryFilterInput.addEventListener('input', (e) => {
      renderInventoryTable();
    });
  }

  // Inventory category filter
  if (DOM.inventoryCategoryFilter) {
    DOM.inventoryCategoryFilter.addEventListener('change', (e) => {
      AppState.inventoryCategoryFilter = e.target.value;
      renderInventoryTable();
    });
  }

  // Inventory Health summary ribbon KPI chips
  if (DOM.inventorySummaryRibbon) {
    DOM.inventorySummaryRibbon.querySelectorAll('.inventory-kpi-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        DOM.inventorySummaryRibbon.querySelectorAll('.inventory-kpi-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        AppState.inventoryStockFilter = chip.dataset.stockFilter || 'all';
        renderInventoryTable();
      });
    });
  }

  // Quick Restock Low-Stock Items (+20)
  if (DOM.btnQuickReorderLow) {
    DOM.btnQuickReorderLow.addEventListener('click', async () => {
      const lowItems = AppState.products.filter(p => p.stock <= 15);
      if (lowItems.length === 0) {
        showToast('All inventory items are currently at optimal stock levels.');
        return;
      }
      try {
        for (const item of lowItems) {
          await API.updateProduct(item.id, { stock: item.stock + 20 });
        }
        showToast(`Restocked ${lowItems.length} low-stock items with +20 units each!`);
        await loadCatalog();
        renderInventoryTable();
      } catch (err) {
        showToast('Failed to restock: ' + err.message, true);
      }
    });
  }

  DOM.newProductForm.addEventListener('submit', handleCreateProduct);
  DOM.settingsForm.addEventListener('submit', handleSaveSettings);

  // Checkout modal
  DOM.tenderInput.addEventListener('input', validateTender);
  DOM.btnCompleteSale.addEventListener('click', handleCompleteSale);
  DOM.btnCloseCheckout.addEventListener('click', () => closeModal(DOM.checkoutModal, DOM.checkoutModalCard));

  // Receipt modal
  DOM.btnPrintReceipt.addEventListener('click', () => window.print());
  DOM.btnNewOrder.addEventListener('click', () => closeModal(DOM.receiptModal, DOM.receiptModalCard));
  DOM.btnCloseReceipt.addEventListener('click', () => closeModal(DOM.receiptModal, DOM.receiptModalCard));

  // Close modals on overlay backdrop click
  [
    DOM.checkoutModal, DOM.receiptModal, DOM.consoleModal,
    DOM.modifierModal, DOM.barcodeModal, DOM.deleteConfirmModal,
    DOM.editProductModal, DOM.parkedOrdersModal
  ].forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        const card = modal.querySelector('.modal-card') || modal.querySelector('.console-container');
        closeModal(modal, card);
      }
    });
  });
}
