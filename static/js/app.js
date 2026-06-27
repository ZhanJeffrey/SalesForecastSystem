let token = localStorage.getItem('token');
let currentUser = null;
let trendChart = null;
let categoryChart = null;
let forecastChart = null;

const PAGE_TITLES = {
  dashboard: '数据概览',
  sales: '数据管理',
  forecast: '销量预测',
  profile: '用户中心',
  system: '系统管理',
};

async function api(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    logout();
    throw new Error('登录已过期');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || '请求失败');
  return data;
}

function toast(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

function fmtMoney(n) {
  return '¥' + Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 2 });
}

function fmtDate(d) {
  return d ? new Date(d).toLocaleDateString('zh-CN') : '-';
}

function fmtDateTime(d) {
  return d ? new Date(d).toLocaleString('zh-CN') : '-';
}

// Auth
document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('loginUsername').value;
  const password = document.getElementById('loginPassword').value;
  try {
    const body = new URLSearchParams({ username, password });
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '登录失败');
    token = data.access_token;
    localStorage.setItem('token', token);
    await initApp();
  } catch (err) {
    toast(err.message, 'error');
  }
});

function logout() {
  token = null;
  localStorage.removeItem('token');
  document.getElementById('loginPage').classList.remove('hidden');
  document.getElementById('appLayout').classList.add('hidden');
}

async function initApp() {
  currentUser = await api('/api/auth/me');
  document.getElementById('loginPage').classList.add('hidden');
  document.getElementById('appLayout').classList.remove('hidden');
  document.getElementById('sidebarUser').textContent = currentUser.full_name || currentUser.username;
  document.getElementById('topbarUser').textContent = currentUser.username;

  if (currentUser.role !== 'admin') {
    document.getElementById('navSystem').classList.add('hidden');
  }

  fillProfileForm();
  navigate('dashboard');
}

// Navigation
document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', () => navigate(el.dataset.page));
});

function navigate(page) {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });
  document.querySelectorAll('.page-section').forEach(el => el.classList.add('hidden'));
  document.getElementById(`page-${page}`).classList.remove('hidden');
  document.getElementById('pageTitle').textContent = PAGE_TITLES[page];

  const loaders = {
    dashboard: loadDashboard,
    sales: loadSalesPage,
    forecast: loadForecastPage,
    profile: fillProfileForm,
    system: loadSystemPage,
  };
  if (loaders[page]) loaders[page]();
}

// Dashboard
async function loadDashboard() {
  const data = await api('/api/forecast/analysis');

  document.getElementById('dashStats').innerHTML = `
    <div class="stat-card"><div class="label">销售记录</div><div class="value primary">${data.total_records}</div></div>
    <div class="stat-card"><div class="label">总销量</div><div class="value">${data.total_quantity.toLocaleString()}</div></div>
    <div class="stat-card"><div class="label">总销售额</div><div class="value">${fmtMoney(data.total_amount)}</div></div>
    <div class="stat-card"><div class="label">产品数</div><div class="value">${data.product_count}</div></div>
  `;

  const trendCtx = document.getElementById('trendChart').getContext('2d');
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(trendCtx, {
    type: 'line',
    data: {
      labels: data.monthly_trend.map(m => m.month),
      datasets: [{
        label: '销售额',
        data: data.monthly_trend.map(m => m.amount),
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37,99,235,.1)',
        fill: true,
        tension: .3,
      }],
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } },
  });

  const catCtx = document.getElementById('categoryChart').getContext('2d');
  if (categoryChart) categoryChart.destroy();
  categoryChart = new Chart(catCtx, {
    type: 'doughnut',
    data: {
      labels: data.category_stats.map(c => c.category),
      datasets: [{
        data: data.category_stats.map(c => c.amount),
        backgroundColor: ['#2563eb', '#16a34a', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'],
      }],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });

  document.getElementById('topProductsTable').innerHTML = data.top_products.map(p => `
    <tr>
      <td>${p.product_name}</td>
      <td>${p.quantity.toLocaleString()}</td>
      <td>${fmtMoney(p.amount)}</td>
    </tr>
  `).join('') || '<tr><td colspan="3" style="text-align:center;color:#64748b">暂无数据</td></tr>';
}

// Sales
async function loadSalesPage() {
  await loadCategories();
  await loadSales();
  await loadProductOptions();
}

async function loadCategories() {
  const cats = await api('/api/sales/categories');
  const sel = document.getElementById('filterCategory');
  sel.innerHTML = '<option value="">全部分类</option>' +
    cats.map(c => `<option value="${c}">${c}</option>`).join('');
}

async function loadProductOptions() {
  const products = await api('/api/sales/products');
  const sel = document.getElementById('fcProduct');
  sel.innerHTML = '<option value="">自动选择</option>' +
    products.map(p => `<option value="${p}">${p}</option>`).join('');
}

async function loadSales() {
  const product = document.getElementById('filterProduct')?.value || '';
  const category = document.getElementById('filterCategory')?.value || '';
  let url = '/api/sales?limit=100';
  if (product) url += `&product_name=${encodeURIComponent(product)}`;
  if (category) url += `&category=${encodeURIComponent(category)}`;

  const records = await api(url);
  document.getElementById('salesTable').innerHTML = records.map(r => `
    <tr>
      <td>${r.product_name}</td>
      <td>${r.category}</td>
      <td>${r.region}</td>
      <td>${fmtDate(r.sale_date)}</td>
      <td>${r.quantity}</td>
      <td>${fmtMoney(r.unit_price)}</td>
      <td>${fmtMoney(r.amount)}</td>
      <td class="actions">
        <button class="btn btn-outline btn-sm" onclick="editSales(${r.id})">编辑</button>
        <button class="btn btn-danger btn-sm" onclick="deleteSales(${r.id})">删除</button>
      </td>
    </tr>
  `).join('') || '<tr><td colspan="8" style="text-align:center;color:#64748b">暂无数据</td></tr>';
}

function showSalesForm(record) {
  document.getElementById('salesFormCard').classList.remove('hidden');
  document.getElementById('importCard').classList.add('hidden');
  if (record) {
    document.getElementById('salesFormTitle').textContent = '编辑销售记录';
    document.getElementById('salesEditId').value = record.id;
    document.getElementById('sfProduct').value = record.product_name;
    document.getElementById('sfCategory').value = record.category;
    document.getElementById('sfRegion').value = record.region;
    document.getElementById('sfDate').value = record.sale_date.split('T')[0];
    document.getElementById('sfQty').value = record.quantity;
    document.getElementById('sfPrice').value = record.unit_price;
    document.getElementById('sfRemark').value = record.remark || '';
  } else {
    document.getElementById('salesFormTitle').textContent = '新增销售记录';
    document.getElementById('salesForm').reset();
    document.getElementById('salesEditId').value = '';
    document.getElementById('sfCategory').value = '未分类';
    document.getElementById('sfRegion').value = '全国';
  }
}

function hideSalesForm() {
  document.getElementById('salesFormCard').classList.add('hidden');
}

function showImportModal() {
  document.getElementById('importCard').classList.remove('hidden');
  document.getElementById('salesFormCard').classList.add('hidden');
}

function hideImportModal() {
  document.getElementById('importCard').classList.add('hidden');
}

document.getElementById('salesForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    product_name: document.getElementById('sfProduct').value,
    category: document.getElementById('sfCategory').value,
    region: document.getElementById('sfRegion').value,
    sale_date: document.getElementById('sfDate').value + 'T00:00:00',
    quantity: parseInt(document.getElementById('sfQty').value),
    unit_price: parseFloat(document.getElementById('sfPrice').value),
    remark: document.getElementById('sfRemark').value,
  };
  const editId = document.getElementById('salesEditId').value;
  try {
    if (editId) {
      await api(`/api/sales/${editId}`, { method: 'PUT', body: JSON.stringify(payload) });
      toast('更新成功');
    } else {
      await api('/api/sales', { method: 'POST', body: JSON.stringify(payload) });
      toast('添加成功');
    }
    hideSalesForm();
    loadSales();
  } catch (err) {
    toast(err.message, 'error');
  }
});

async function editSales(id) {
  const records = await api('/api/sales?limit=200');
  const record = records.find(r => r.id === id);
  if (record) showSalesForm(record);
}

async function deleteSales(id) {
  if (!confirm('确定删除此记录？')) return;
  try {
    await api(`/api/sales/${id}`, { method: 'DELETE' });
    toast('删除成功');
    loadSales();
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function importSales() {
  const fileInput = document.getElementById('importFile');
  if (!fileInput.files.length) return toast('请选择文件', 'error');
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  try {
    const data = await api('/api/sales/import', { method: 'POST', body: formData });
    toast(data.message);
    hideImportModal();
    loadSales();
  } catch (err) {
    toast(err.message, 'error');
  }
}

// Forecast
async function loadForecastPage() {
  await loadProductOptions();
}

async function runForecast() {
  const payload = {
    product_name: document.getElementById('fcProduct').value || null,
    periods: parseInt(document.getElementById('fcPeriods').value),
    model_type: document.getElementById('fcModel').value,
  };
  try {
    const result = await api('/api/forecast/predict', { method: 'POST', body: JSON.stringify(payload) });
    document.getElementById('forecastResult').classList.remove('hidden');

    document.getElementById('fcStats').innerHTML = `
      <div class="stat-card"><div class="label">预测产品</div><div class="value" style="font-size:1.1rem">${result.product_name}</div></div>
      <div class="stat-card"><div class="label">预测模型</div><div class="value" style="font-size:1.1rem">${result.model_type === 'linear' ? '线性回归' : '移动平均'}</div></div>
      <div class="stat-card"><div class="label">模型置信度</div><div class="value primary">${(result.confidence * 100).toFixed(1)}%</div></div>
      <div class="stat-card"><div class="label">历史数据点</div><div class="value">${result.history_points} 个月</div></div>
    `;

    document.getElementById('forecastTable').innerHTML = result.forecasts.map(f => `
      <tr>
        <td>${fmtDate(f.forecast_date)}</td>
        <td>${f.predicted_quantity.toLocaleString()}</td>
        <td>${fmtMoney(f.predicted_amount)}</td>
      </tr>
    `).join('');

    const ctx = document.getElementById('forecastChart').getContext('2d');
    if (forecastChart) forecastChart.destroy();
    forecastChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: result.forecasts.map(f => fmtDate(f.forecast_date)),
        datasets: [
          { label: '预测销量', data: result.forecasts.map(f => f.predicted_quantity), backgroundColor: '#2563eb' },
          { label: '预测销售额', data: result.forecasts.map(f => f.predicted_amount), backgroundColor: '#16a34a' },
        ],
      },
      options: { responsive: true, maintainAspectRatio: false },
    });
    toast('预测完成');
  } catch (err) {
    toast(err.message, 'error');
  }
}

// Profile
function fillProfileForm() {
  if (!currentUser) return;
  document.getElementById('pfUsername').value = currentUser.username;
  document.getElementById('pfName').value = currentUser.full_name || '';
  document.getElementById('pfEmail').value = currentUser.email;
  document.getElementById('pfRole').value = currentUser.role === 'admin' ? '管理员' : '普通用户';
}

document.getElementById('profileForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    currentUser = await api('/api/auth/me', {
      method: 'PUT',
      body: JSON.stringify({
        full_name: document.getElementById('pfName').value,
        email: document.getElementById('pfEmail').value,
      }),
    });
    toast('个人信息已更新');
    document.getElementById('sidebarUser').textContent = currentUser.full_name || currentUser.username;
  } catch (err) {
    toast(err.message, 'error');
  }
});

document.getElementById('passwordForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    await api('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({
        old_password: document.getElementById('pwOld').value,
        new_password: document.getElementById('pwNew').value,
      }),
    });
    toast('密码修改成功');
    document.getElementById('passwordForm').reset();
  } catch (err) {
    toast(err.message, 'error');
  }
});

// System
async function loadSystemPage() {
  const stats = await api('/api/system/stats');
  document.getElementById('sysStats').innerHTML = `
    <div class="stat-card"><div class="label">用户数</div><div class="value primary">${stats.user_count}</div></div>
    <div class="stat-card"><div class="label">销售记录</div><div class="value">${stats.sales_count}</div></div>
    <div class="stat-card"><div class="label">预测记录</div><div class="value">${stats.forecast_count}</div></div>
    <div class="stat-card"><div class="label">总销售额</div><div class="value">${fmtMoney(stats.total_sales_amount)}</div></div>
  `;

  const users = await api('/api/system/users');
  document.getElementById('usersTable').innerHTML = users.map(u => `
    <tr>
      <td>${u.username}</td>
      <td>${u.full_name || '-'}</td>
      <td>${u.email}</td>
      <td><span class="badge badge-${u.role}">${u.role === 'admin' ? '管理员' : '用户'}</span></td>
      <td><span class="badge badge-${u.is_active ? 'active' : 'inactive'}">${u.is_active ? '正常' : '禁用'}</span></td>
      <td class="actions">
        ${u.id !== currentUser.id ? `<button class="btn btn-outline btn-sm" onclick="toggleUser(${u.id})">${u.is_active ? '禁用' : '启用'}</button>` : ''}
        <button class="btn btn-outline btn-sm" onclick="resetPassword(${u.id})">重置密码</button>
      </td>
    </tr>
  `).join('');

  const logs = await api('/api/system/logs');
  document.getElementById('logsTable').innerHTML = logs.map(l => `
    <tr>
      <td>${fmtDateTime(l.created_at)}</td>
      <td>${l.action}</td>
      <td>${l.detail}</td>
    </tr>
  `).join('') || '<tr><td colspan="3" style="text-align:center;color:#64748b">暂无日志</td></tr>';
}

async function toggleUser(id) {
  try {
    const data = await api(`/api/system/users/${id}/toggle`, { method: 'PUT' });
    toast(data.message);
    loadSystemPage();
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function resetPassword(id) {
  if (!confirm('确定重置该用户密码为 123456？')) return;
  try {
    const data = await api(`/api/system/users/${id}/reset-password`, { method: 'PUT' });
    toast(data.message);
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function clearLogs() {
  if (!confirm('确定清空所有系统日志？')) return;
  try {
    const data = await api('/api/system/logs', { method: 'DELETE' });
    toast(data.message);
    loadSystemPage();
  } catch (err) {
    toast(err.message, 'error');
  }
}

// Init
if (token) {
  initApp().catch(() => logout());
}
