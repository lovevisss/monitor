<script setup>
import * as echarts from "echarts";
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  changePassword,
  clearStoredToken,
  createService,
  createMaintenanceLog,
  deleteService,
  getAlerts,
  getAuditLogs,
  getAuthMe,
  getHealth,
  getMaintenanceLogs,
  getMonitorLogs,
  getOverview,
  getServiceStatus,
  getSettings,
  getStoredToken,
  loginAdmin,
  runNow,
  runAllNow,
  sendTestAlert,
  setStoredToken,
  updateService,
  updateSettings,
} from "./api";

const loading = ref(false);
const saving = ref(false);
const backendOk = ref(false);
const lastUpdatedAt = ref("");
const statusChartEl = ref(null);
const latencyChartEl = ref(null);
const activeMenu = ref("overview");

let statusChart = null;
let latencyChart = null;
let timer = null;

const summary = reactive({ service_total: 0, service_enabled: 0, avg_latency_ms: null, log_count: 0 });
const serviceRows = ref([]);
const alertRows = ref([]);
const auditRows = ref([]);
const selectedTag = ref("");

const authReady = ref(false);
const adminName = ref("");
const loginVisible = ref(false);
const passwordVisible = ref(false);

const loginForm = reactive({ username: "admin", password: "" });
const passwordForm = reactive({ old_password: "", new_password: "" });

const serviceDialogVisible = ref(false);
const historyDialogVisible = ref(false);
const maintenanceDialogVisible = ref(false);
const editingServiceId = ref(null);
const maintenanceServiceId = ref(null);
const currentServiceName = ref("");
const historyRows = ref([]);
const maintenanceRows = ref([]);
const maintenanceContent = ref("");
const serviceTagSelection = ref([]);
const serviceForm = reactive({
  name: "",
  check_type: "http",
  target: "",
  keyword: "",
  interval_sec: 60,
  timeout_sec: 10,
  enabled: true,
});

const settingsForm = reactive({
  database_url: "",
  default_interval_seconds: 60,
  default_timeout_seconds: 10,
  alert_webhook_wechat: "",
  alert_webhook_dingtalk: "",
  alert_email_enabled: false,
  alert_email_host: "",
  alert_email_port: 25,
  alert_email_user: "",
  alert_email_password: "",
  alert_email_from: "",
  alert_email_to_text: "",
});

const onlineRate = computed(() => {
  if (!serviceRows.value.length) return 0;
  const online = serviceRows.value.filter((item) => item.latest_status === "online").length;
  return ((online / serviceRows.value.length) * 100).toFixed(1);
});

const isLoggedIn = computed(() => !!adminName.value);

const statusLabelMap = { online: "在线", slow: "卡顿", abnormal: "异常", offline: "离线", unknown: "未检测" };
const statusTypeMap = { online: "success", slow: "warning", abnormal: "danger", offline: "danger", unknown: "info" };

const availableTags = computed(() => {
  const found = new Set();
  for (const row of serviceRows.value) {
    for (const tag of parseTags(row.tags)) {
      found.add(tag);
    }
  }
  return Array.from(found);
});

const filteredServiceRows = computed(() => {
  if (!selectedTag.value) {
    return serviceRows.value;
  }
  return serviceRows.value.filter((row) => parseTags(row.tags).includes(selectedTag.value));
});

function parseTags(raw) {
  if (!raw) {
    return [];
  }
  return String(raw)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function resetServiceForm() {
  editingServiceId.value = null;
  serviceTagSelection.value = [];
  Object.assign(serviceForm, {
    name: "",
    check_type: "http",
    target: "",
    keyword: "",
    interval_sec: 60,
    timeout_sec: 10,
    enabled: true,
  });
}

function onCheckTypeChange(value) {
  if (value === "zufe_route" && !serviceForm.target) {
    serviceForm.target = "www.zufe.edu.cn";
  }
}

function openCreateServiceDialog() {
  if (!isLoggedIn.value) {
    loginVisible.value = true;
    return;
  }
  resetServiceForm();
  serviceDialogVisible.value = true;
}

function openEditServiceDialog(row) {
  if (!isLoggedIn.value) {
    loginVisible.value = true;
    return;
  }
  editingServiceId.value = row.service_id;
  serviceTagSelection.value = parseTags(row.tags);
  Object.assign(serviceForm, {
    name: row.name,
    check_type: row.check_type,
    target: row.target,
    keyword: row.keyword || "",
    interval_sec: row.interval_sec || 60,
    timeout_sec: row.timeout_sec || 10,
    enabled: row.enabled,
  });
  serviceDialogVisible.value = true;
}

async function loadAll() {
  loading.value = true;
  try {
    const [healthResp, overviewResp, statusResp, alertsResp] = await Promise.all([
      getHealth(),
      getOverview(),
      getServiceStatus(),
      getAlerts(30),
    ]);
    backendOk.value = healthResp.data?.status === "ok";
    Object.assign(summary, overviewResp.data || {});
    serviceRows.value = statusResp.data || [];
    alertRows.value = alertsResp.data || [];
    if (isLoggedIn.value) {
      const [auditResp, settingResp] = await Promise.all([getAuditLogs(30), getSettings()]);
      auditRows.value = auditResp.data || [];
      patchSettingsForm(settingResp.data || {});
    } else {
      auditRows.value = [];
    }
    lastUpdatedAt.value = new Date().toLocaleString();
    renderStatusChart();
    renderLatencyChart();
  } catch (error) {
    backendOk.value = false;
    ElMessage.error(`加载失败: ${error.message || "unknown"}`);
  } finally {
    loading.value = false;
  }
}

function patchSettingsForm(data) {
  settingsForm.database_url = data.database_url || "";
  settingsForm.default_interval_seconds = data.default_interval_seconds || 60;
  settingsForm.default_timeout_seconds = data.default_timeout_seconds || 10;
  settingsForm.alert_webhook_wechat = data.alert_webhook_wechat || "";
  settingsForm.alert_webhook_dingtalk = data.alert_webhook_dingtalk || "";
  settingsForm.alert_email_enabled = !!data.alert_email_enabled;
  settingsForm.alert_email_host = data.alert_email_host || "";
  settingsForm.alert_email_port = data.alert_email_port || 25;
  settingsForm.alert_email_user = data.alert_email_user || "";
  settingsForm.alert_email_password = data.alert_email_password || "";
  settingsForm.alert_email_from = data.alert_email_from || "";
  settingsForm.alert_email_to_text = Array.isArray(data.alert_email_to) ? data.alert_email_to.join(",") : "";
}

async function bootstrapAuth() {
  const token = getStoredToken();
  if (!token) {
    authReady.value = true;
    return;
  }
  try {
    const resp = await getAuthMe();
    adminName.value = resp.data?.username || "";
  } catch {
    clearStoredToken();
    adminName.value = "";
  } finally {
    authReady.value = true;
  }
}

async function doLogin() {
  try {
    const resp = await loginAdmin(loginForm);
    setStoredToken(resp.data.access_token);
    const me = await getAuthMe();
    adminName.value = me.data?.username || "";
    loginVisible.value = false;
    loginForm.password = "";
    ElMessage.success("管理员登录成功");
    await loadAll();
  } catch (error) {
    ElMessage.error(`登录失败: ${error.response?.data?.detail || error.message || "unknown"}`);
  }
}

function logout() {
  clearStoredToken();
  adminName.value = "";
  ElMessage.success("已退出登录");
}

async function doChangePassword() {
  try {
    await changePassword(passwordForm);
    passwordVisible.value = false;
    passwordForm.old_password = "";
    passwordForm.new_password = "";
    ElMessage.success("密码修改成功");
  } catch (error) {
    ElMessage.error(`修改失败: ${error.response?.data?.detail || error.message || "unknown"}`);
  }
}

async function saveService() {
  if (!isLoggedIn.value) {
    loginVisible.value = true;
    return;
  }
  saving.value = true;
  try {
    const payload = {
      ...serviceForm,
      keyword: serviceForm.keyword || null,
      tags: serviceTagSelection.value.join(",") || null,
    };
    if (editingServiceId.value) {
      await updateService(editingServiceId.value, payload);
      ElMessage.success("服务更新成功");
    } else {
      await createService(payload);
      ElMessage.success("服务新增成功");
    }
    serviceDialogVisible.value = false;
    resetServiceForm();
    await loadAll();
  } catch (error) {
    ElMessage.error(`保存失败: ${error.response?.data?.detail || error.message || "unknown"}`);
  } finally {
    saving.value = false;
  }
}

async function removeService(row) {
  if (!isLoggedIn.value) {
    loginVisible.value = true;
    return;
  }
  try {
    await ElMessageBox.confirm(`确认删除服务 ${row.name} ?`, "删除确认", { type: "warning" });
    await deleteService(row.service_id);
    ElMessage.success("服务已删除");
    await loadAll();
  } catch (error) {
    if (error !== "cancel") {
      ElMessage.error(`删除失败: ${error.response?.data?.detail || error.message || "unknown"}`);
    }
  }
}

async function triggerRunNow(row) {
  if (!isLoggedIn.value) {
    loginVisible.value = true;
    return;
  }
  try {
    await runNow(row.service_id);
    ElMessage.success(`${row.name} 已执行一次即时巡检`);
    await loadAll();
  } catch (error) {
    ElMessage.error(`执行失败: ${error.response?.data?.detail || error.message || "unknown"}`);
  }
}

async function triggerRunAllNow() {
  if (!isLoggedIn.value) {
    loginVisible.value = true;
    return;
  }
  try {
    const resp = await runAllNow();
    ElMessage.success(`一键巡检完成：共处理 ${resp.data.processed} 个服务`);
    await loadAll();
  } catch (error) {
    ElMessage.error(`一键巡检失败: ${error.response?.data?.detail || error.message || "unknown"}`);
  }
}

async function openHistoryDialog(row) {
  currentServiceName.value = row.name;
  historyDialogVisible.value = true;
  try {
    const resp = await getMonitorLogs(row.service_id, 200);
    historyRows.value = resp.data || [];
  } catch (error) {
    ElMessage.error(`历史状态加载失败: ${error.response?.data?.detail || error.message || "unknown"}`);
  }
}

async function openMaintenanceDialog(row) {
  if (!isLoggedIn.value) {
    loginVisible.value = true;
    return;
  }
  maintenanceServiceId.value = row.service_id;
  currentServiceName.value = row.name;
  maintenanceDialogVisible.value = true;
  maintenanceContent.value = "";
  try {
    const resp = await getMaintenanceLogs(maintenanceServiceId.value, 200);
    maintenanceRows.value = resp.data || [];
  } catch (error) {
    ElMessage.error(`维修日记加载失败: ${error.response?.data?.detail || error.message || "unknown"}`);
  }
}

async function submitMaintenanceLog() {
  if (!maintenanceServiceId.value || !maintenanceContent.value.trim()) {
    ElMessage.warning("请先填写维修内容");
    return;
  }
  try {
    await createMaintenanceLog({
      service_id: maintenanceServiceId.value,
      content: maintenanceContent.value.trim(),
    });
    maintenanceContent.value = "";
    const resp = await getMaintenanceLogs(maintenanceServiceId.value, 200);
    maintenanceRows.value = resp.data || [];
    ElMessage.success("维修日记已记录");
  } catch (error) {
    ElMessage.error(`保存失败: ${error.response?.data?.detail || error.message || "unknown"}`);
  }
}

async function saveAlertSettings() {
  if (!isLoggedIn.value) {
    loginVisible.value = true;
    return;
  }
  const payload = {
    alert_webhook_wechat: settingsForm.alert_webhook_wechat,
    alert_webhook_dingtalk: settingsForm.alert_webhook_dingtalk,
    alert_email_enabled: settingsForm.alert_email_enabled,
    alert_email_host: settingsForm.alert_email_host,
    alert_email_port: settingsForm.alert_email_port,
    alert_email_user: settingsForm.alert_email_user,
    alert_email_password: settingsForm.alert_email_password,
    alert_email_from: settingsForm.alert_email_from,
    alert_email_to: settingsForm.alert_email_to_text.split(",").map((x) => x.trim()).filter(Boolean),
  };
  try {
    await updateSettings(payload);
    ElMessage.success("告警配置已保存");
  } catch (error) {
    ElMessage.error(`保存失败: ${error.response?.data?.detail || error.message || "unknown"}`);
  }
}

async function triggerTestAlert() {
  if (!isLoggedIn.value) {
    loginVisible.value = true;
    return;
  }
  try {
    await sendTestAlert();
    ElMessage.success("测试告警已发送，请检查企业微信/钉钉/邮箱");
    await loadAll();
  } catch (error) {
    ElMessage.error(`测试告警发送失败: ${error.response?.data?.detail || error.message || "unknown"}`);
  }
}

async function saveSystemSettings() {
  if (!isLoggedIn.value) {
    loginVisible.value = true;
    return;
  }
  const payload = {
    database_url: settingsForm.database_url,
    default_interval_seconds: settingsForm.default_interval_seconds,
    default_timeout_seconds: settingsForm.default_timeout_seconds,
  };
  try {
    await updateSettings(payload);
    ElMessage.success("系统配置已保存（数据库变更需重启后端生效）");
  } catch (error) {
    ElMessage.error(`保存失败: ${error.response?.data?.detail || error.message || "unknown"}`);
  }
}

function renderStatusChart() {
  if (!statusChartEl.value) return;
  if (!statusChart) statusChart = echarts.init(statusChartEl.value);
  const counts = { online: 0, slow: 0, abnormal: 0, offline: 0, unknown: 0 };
  for (const row of serviceRows.value) counts[row.latest_status] = (counts[row.latest_status] || 0) + 1;
  statusChart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "item" },
    series: [{ type: "pie", radius: ["45%", "72%"], data: Object.entries(counts).map(([k, v]) => ({ name: statusLabelMap[k], value: v })), label: { color: "#e9f4ff" } }],
  });
}

function renderLatencyChart() {
  if (!latencyChartEl.value) return;
  if (!latencyChart) latencyChart = echarts.init(latencyChartEl.value);
  const rows = [...serviceRows.value].filter((i) => i.latest_latency_ms !== null).sort((a, b) => (b.latest_latency_ms || 0) - (a.latest_latency_ms || 0)).slice(0, 12);
  latencyChart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: rows.map((i) => i.name), axisLabel: { color: "#d7e8ff", rotate: 20 } },
    yAxis: { type: "value", axisLabel: { color: "#d7e8ff" } },
    series: [{ type: "bar", data: rows.map((i) => Number(i.latest_latency_ms.toFixed(2))) }],
  });
}

onMounted(async () => {
  await bootstrapAuth();
  await loadAll();
  timer = window.setInterval(loadAll, 20000);
  window.addEventListener("resize", () => {
    statusChart?.resize();
    latencyChart?.resize();
  });
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
  statusChart?.dispose();
  latencyChart?.dispose();
});
</script>

<template>
  <div class="page-shell">
    <header class="hero">
      <div>
        <h1>校园业务系统监控后台</h1>
        <p>可视化运维：总览、服务管理、告警配置、系统配置</p>
      </div>
      <div class="hero-actions">
        <el-tag :type="backendOk ? 'success' : 'danger'" effect="dark">后端: {{ backendOk ? "正常" : "异常" }}</el-tag>
        <el-tag v-if="isLoggedIn" type="success" effect="dark">管理员: {{ adminName }}</el-tag>
        <el-button v-if="!isLoggedIn" @click="loginVisible = true">登录</el-button>
        <el-button v-if="isLoggedIn" @click="passwordVisible = true">改密</el-button>
        <el-button v-if="isLoggedIn" @click="logout">退出</el-button>
      </div>
    </header>

    <el-menu mode="horizontal" :default-active="activeMenu" @select="(v) => (activeMenu = v)">
      <el-menu-item index="overview">总览</el-menu-item>
      <el-menu-item index="services">服务管理</el-menu-item>
      <el-menu-item index="alerts">告警配置</el-menu-item>
      <el-menu-item index="settings">系统配置</el-menu-item>
    </el-menu>

    <template v-if="activeMenu === 'overview'">
      <section class="summary-grid" v-loading="loading">
        <article class="metric-card"><span class="label">服务总数</span><strong>{{ summary.service_total }}</strong></article>
        <article class="metric-card"><span class="label">启用服务</span><strong>{{ summary.service_enabled }}</strong></article>
        <article class="metric-card"><span class="label">平均响应</span><strong>{{ summary.avg_latency_ms ?? "-" }} ms</strong></article>
        <article class="metric-card"><span class="label">在线率</span><strong>{{ onlineRate }}%</strong></article>
      </section>
      <section class="chart-grid">
        <div class="panel"><h3>状态分布</h3><div ref="statusChartEl" class="chart"></div></div>
        <div class="panel"><h3>响应耗时 Top12</h3><div ref="latencyChartEl" class="chart"></div></div>
      </section>
      <section class="panel">
        <h3>告警记录（最近30条）</h3>
        <el-table :data="alertRows" size="small">
          <el-table-column prop="service_id" label="服务ID" width="90" />
          <el-table-column prop="alert_type" label="告警类型" width="120" />
          <el-table-column prop="reason" label="原因" min-width="260" />
          <el-table-column prop="last_occur_at" label="最近发生" min-width="180" />
        </el-table>
      </section>
    </template>

    <template v-else-if="activeMenu === 'services'">
      <section class="panel">
        <div class="panel-header">
          <h3>服务管理</h3>
          <div>
            <el-select v-model="selectedTag" clearable placeholder="按标签筛选" style="width: 200px; margin-right: 10px">
              <el-option v-for="tag in availableTags" :key="tag" :label="tag" :value="tag" />
            </el-select>
            <el-button style="margin-right: 10px" type="success" plain @click="triggerRunAllNow">一键巡检</el-button>
            <el-button type="primary" @click="openCreateServiceDialog">新增服务</el-button>
            <el-button @click="loadAll">刷新</el-button>
          </div>
        </div>
        <el-table :data="filteredServiceRows" stripe>
          <el-table-column prop="name" label="服务名称" min-width="170" />
          <el-table-column prop="check_type" label="类型" width="90" />
          <el-table-column label="标签" min-width="170">
            <template #default="{ row }">
              <el-tag v-for="tag in parseTags(row.tags)" :key="`${row.service_id}-${tag}`" style="margin-right: 6px">{{ tag }}</el-tag>
              <span v-if="!parseTags(row.tags).length">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="target" label="监控地址" min-width="250" />
          <el-table-column label="状态" width="120">
            <template #default="{ row }"><el-tag :type="statusTypeMap[row.latest_status] || 'info'">{{ statusLabelMap[row.latest_status] || row.latest_status }}</el-tag></template>
          </el-table-column>
          <el-table-column label="操作" width="460" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" plain @click="triggerRunNow(row)">立即巡检</el-button>
              <el-button size="small" type="warning" plain @click="openEditServiceDialog(row)">编辑</el-button>
              <el-button size="small" type="info" plain @click="openHistoryDialog(row)">历史状态</el-button>
              <el-button size="small" type="success" plain @click="openMaintenanceDialog(row)">维修日记</el-button>
              <el-button size="small" type="danger" @click="removeService(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </template>

    <template v-else-if="activeMenu === 'alerts'">
      <section class="panel channel-panel">
        <h3>告警渠道配置</h3>
        <el-form label-width="170px" style="max-width: 900px">
          <el-form-item label="企业微信 Webhook"><el-input v-model="settingsForm.alert_webhook_wechat" /></el-form-item>
          <el-form-item label="钉钉 Webhook"><el-input v-model="settingsForm.alert_webhook_dingtalk" /></el-form-item>
          <el-form-item label="启用邮箱告警"><el-switch v-model="settingsForm.alert_email_enabled" /></el-form-item>
          <el-form-item label="SMTP Host"><el-input v-model="settingsForm.alert_email_host" /></el-form-item>
          <el-form-item label="SMTP Port"><el-input-number v-model="settingsForm.alert_email_port" :min="1" :max="65535" /></el-form-item>
          <el-form-item label="邮箱账号"><el-input v-model="settingsForm.alert_email_user" /></el-form-item>
          <el-form-item label="邮箱密码"><el-input v-model="settingsForm.alert_email_password" type="password" show-password /></el-form-item>
          <el-form-item label="发件人"><el-input v-model="settingsForm.alert_email_from" /></el-form-item>
          <el-form-item label="收件人(逗号分隔)"><el-input v-model="settingsForm.alert_email_to_text" /></el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveAlertSettings">保存告警配置</el-button>
            <el-button style="margin-left: 10px" type="success" plain @click="triggerTestAlert">发送测试告警</el-button>
          </el-form-item>
        </el-form>
      </section>
    </template>

    <template v-else>
      <section class="panel">
        <h3>系统配置</h3>
        <el-form label-width="170px" style="max-width: 900px">
          <el-form-item label="数据库连接"><el-input v-model="settingsForm.database_url" /></el-form-item>
          <el-form-item label="默认巡检间隔(s)"><el-input-number v-model="settingsForm.default_interval_seconds" :min="10" :max="3600" /></el-form-item>
          <el-form-item label="默认超时(s)"><el-input-number v-model="settingsForm.default_timeout_seconds" :min="1" :max="120" /></el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveSystemSettings">保存系统配置</el-button>
            <span style="margin-left: 12px; color: #a2c0e8">数据库/JWT等配置变更后建议重启后端</span>
          </el-form-item>
        </el-form>
      </section>
      <section class="panel" v-if="isLoggedIn">
        <h3>操作审计（最近30条）</h3>
        <el-table :data="auditRows" size="small">
          <el-table-column prop="admin_username" label="管理员" width="120" />
          <el-table-column prop="action" label="动作" width="180" />
          <el-table-column prop="target_type" label="目标" width="120" />
          <el-table-column prop="detail" label="详情" min-width="240" />
          <el-table-column prop="created_at" label="时间" min-width="180" />
        </el-table>
      </section>
    </template>

    <el-dialog v-model="serviceDialogVisible" :title="editingServiceId ? '编辑服务' : '新增服务'" width="560px">
      <el-form label-width="110px">
        <el-form-item label="服务名称"><el-input v-model="serviceForm.name" /></el-form-item>
        <el-form-item label="监控类型">
          <el-select v-model="serviceForm.check_type" style="width: 100%" @change="onCheckTypeChange">
            <el-option label="HTTP/HTTPS" value="http" />
            <el-option label="TCP" value="tcp" />
            <el-option label="PING" value="ping" />
            <el-option label="本部光路测试" value="zufe_route" />
          </el-select>
        </el-form-item>
        <el-form-item label="监控地址">
          <el-input
            v-model="serviceForm.target"
            :placeholder="serviceForm.check_type === 'zufe_route' ? 'www.zufe.edu.cn' : '请输入URL或IP:端口'"
          />
        </el-form-item>
        <el-form-item v-if="serviceForm.check_type === 'http'" label="关键词"><el-input v-model="serviceForm.keyword" /></el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="serviceTagSelection"
            multiple
            filterable
            allow-create
            collapse-tags
            collapse-tags-tooltip
            default-first-option
            placeholder="选择已有标签或输入新标签"
            style="width: 100%"
          >
            <el-option v-for="tag in availableTags" :key="`select-${tag}`" :label="tag" :value="tag" />
          </el-select>
        </el-form-item>
        <el-form-item label="巡检间隔(s)"><el-input-number v-model="serviceForm.interval_sec" :min="10" :max="3600" /></el-form-item>
        <el-form-item label="超时(s)"><el-input-number v-model="serviceForm.timeout_sec" :min="1" :max="120" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="serviceForm.enabled" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="serviceDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveService">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="historyDialogVisible" :title="`历史状态 - ${currentServiceName}`" width="900px">
      <el-table :data="historyRows" size="small" max-height="460">
        <el-table-column prop="checked_at" label="检测时间" min-width="180" />
        <el-table-column prop="result_status" label="状态" width="120" />
        <el-table-column prop="latency_ms" label="响应(ms)" width="120" />
        <el-table-column prop="http_code" label="状态码" width="90" />
        <el-table-column prop="error_msg" label="备注" min-width="260" />
      </el-table>
    </el-dialog>

    <el-dialog v-model="maintenanceDialogVisible" :title="`维修日记 - ${currentServiceName}`" width="920px">
      <el-form label-width="95px">
        <el-form-item label="维修记录">
          <el-input
            v-model="maintenanceContent"
            type="textarea"
            :rows="3"
            placeholder="记录故障处理过程、替换部件、恢复时间、责任人等"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="submitMaintenanceLog">保存日记</el-button>
        </el-form-item>
      </el-form>
      <el-table :data="maintenanceRows" size="small" max-height="360">
        <el-table-column prop="created_at" label="记录时间" min-width="180" />
        <el-table-column prop="admin_username" label="记录人" width="120" />
        <el-table-column prop="content" label="内容" min-width="420" />
      </el-table>
    </el-dialog>

    <el-dialog v-model="loginVisible" title="管理员登录" width="420px">
      <el-form label-width="95px">
        <el-form-item label="用户名"><el-input v-model="loginForm.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="loginForm.password" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="loginVisible = false">取消</el-button>
        <el-button type="primary" @click="doLogin">登录</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="passwordVisible" title="修改管理员密码" width="440px">
      <el-form label-width="110px">
        <el-form-item label="旧密码"><el-input v-model="passwordForm.old_password" type="password" show-password /></el-form-item>
        <el-form-item label="新密码"><el-input v-model="passwordForm.new_password" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordVisible = false">取消</el-button>
        <el-button type="primary" @click="doChangePassword">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

