"use strict";

const DATA = window.GUARDSYNTH_PORTAL_DATA;

function node(tag, className, text) {
  const value = document.createElement(tag);
  if (className) value.className = className;
  if (text !== undefined) value.textContent = text;
  return value;
}

function setText(id, value) {
  const target = document.getElementById(id);
  if (target) target.textContent = value;
}

function statusClass(status) {
  const value = status.toLowerCase();
  if (value.includes("complete") || value.includes("manuscript_ready")) return "complete";
  if (value.includes("blocked") || value.includes("scope_rework")) return "blocked";
  if (value.includes("active")) return "active";
  if (value.includes("ready")) return "ready";
  if (value.includes("partial") || value.includes("writing") || value.includes("planning")) return "partial";
  return "queued";
}

function statusPill(status) {
  return node("span", `status ${statusClass(status)}`, status);
}

function projectByOrder() {
  const order = Number(document.body.dataset.projectOrder);
  const project = DATA.research_projects.find(item => item.order === order);
  if (!project) throw new Error(`project data missing for order ${order}`);
  return project;
}

function metricCard(label, value, note) {
  const card = node("article", "card");
  card.append(node("div", "metric-label", label), node("div", "metric-value", value), node("div", "metric-note", note));
  return card;
}

function projectCard(project, reviewMode = false) {
  const card = node("article", "card project-card");
  const head = node("div", "section-head");
  head.append(node("span", "structure-order", String(project.order).padStart(2, "0")), statusPill(project.state));
  card.append(head, node("h3", "", project.title));
  if (reviewMode) {
    const count = project.review_pages.length;
    card.append(
      node("p", "", count ? `${count}개 검토 패키지가 등록되어 있습니다.` : "현재 등록된 검토 패키지가 없습니다.")
    );
  } else {
    card.append(
      node("p", "", project.overview),
      node("p", "metric-note", `현재 ${project.active_milestone_id} · ${project.active_milestone.title}`),
      node("p", "current-task-preview", project.current_task),
    );
  }
  const actions = node("div", "paper-actions");
  const link = node("a", "button", reviewMode ? "검토 열기" : "연구 현황 열기");
  link.href = reviewMode ? project.review_page : project.page;
  actions.append(link);
  if (!reviewMode) {
    const review = node("a", "button ghost", `검토 ${project.review_pages.length}개`);
    review.href = project.review_page;
    actions.append(review);
  }
  card.append(actions);
  return card;
}

function milestoneDetails(item, open = false) {
  const details = node("details", "milestone");
  details.open = open;
  const summary = node("summary");
  summary.append(node("span", "milestone-id", item.id), node("span", "milestone-title", item.title), node("span", "milestone-phase", item.phase || ""), statusPill(item.status));
  const body = node("div", "milestone-body");
  body.append(node("p", "", item.summary));
  if (item.task_count) {
    const progress = node("progress", "progress");
    progress.max = item.task_count;
    progress.value = item.done_tasks;
    body.append(node("small", "metric-note", `Todo ${item.done_tasks}/${item.task_count}`), progress);
    const tasks = node("ul", "tasks");
    item.tasks.forEach(task => {
      const entry = node("li", `task ${task.done ? "done" : ""}`);
      entry.append(node("span", "task-mark", task.done ? "✓" : ""), node("span", "", task.text));
      tasks.append(entry);
    });
    body.append(tasks);
  }
  details.append(summary, body);
  return details;
}

function renderCommon() {
  setText("generated-date", DATA.generated_date);
}

function renderOverview() {
  const metrics = document.getElementById("portfolio-metrics");
  metrics.append(
    metricCard("연구영역", String(DATA.portfolio.project_count), "독립 원장과 상태"),
    metricCard("전체 마일스톤", String(DATA.portfolio.milestone_count), "영역별 ledger 합계"),
    metricCard("검토 패키지", String(DATA.portfolio.review_package_count), "소유 project별 분리"),
    metricCard("완성 원고", String(DATA.papers.length), "PDF 직접 연결"),
  );
  const list = document.getElementById("project-card-list");
  DATA.research_projects.forEach(project => list.append(projectCard(project)));
  const platforms = document.getElementById("overview-platform-list");
  DATA.platforms.forEach(platform => {
    const card = node("article", "card");
    card.append(statusPill(platform.raw_state), node("h3", "", platform.title), node("p", "", `소비 프로젝트: ${platform.consumers.join(", ")}`));
    const link = node("a", "button ghost", "공용 플랫폼 보기");
    link.href = "platform.html";
    card.append(link);
    platforms.append(card);
  });
}

function renderProjects() {
  const list = document.getElementById("project-card-list");
  DATA.research_projects.forEach(project => list.append(projectCard(project)));
  renderRelations();
}

function renderRelations() {
  const map = document.getElementById("relation-map");
  const table = document.getElementById("relation-table");
  const platform = DATA.projection.platforms[0];
  const platformCard = node("article", "card relation-platform");
  platformCard.append(node("strong", "", `◆ ${platform.title}`), node("small", "metric-note", platform.platform_id));
  const consumers = node("div", "relation-consumers");
  DATA.projection.projects.forEach(project => {
    const dependencies = Array.isArray(project.dependencies) ? project.dependencies : [];
    const row = document.createElement("tr");
    const projectCell = node("td", "", project.title);
    const targetCell = node("td", "", dependencies.join(", ") || "없음");
    const relationCell = node("td", "", dependencies.length ? "구현 의존성" : "독립");
    row.append(projectCell, targetCell, relationCell); table.append(row);
    if (dependencies.includes(platform.platform_id)) {
      const edge = node("div", "relation-edge");
      edge.append(node("div", "card", `■ ${project.title}`));
      consumers.append(edge);
    }
  });
  map.append(platformCard, consumers);
  let scale = 1;
  const apply = () => map.style.setProperty("--relation-scale", String(scale));
  document.getElementById("relation-zoom-out").addEventListener("click", () => { scale = Math.max(.7, scale - .1); apply(); });
  document.getElementById("relation-zoom-in").addEventListener("click", () => { scale = Math.min(1.5, scale + .1); apply(); });
  document.getElementById("relation-fit").addEventListener("click", () => { scale = 1; apply(); });
}

function renderPlatform() {
  const list = document.getElementById("platform-list");
  DATA.platforms.forEach(platform => {
    const card = node("article", "card");
    card.append(
      statusPill(platform.raw_state),
      node("h2", "", platform.title),
      node("p", "metric-note", `Platform ID · ${platform.platform_id}`),
      node("p", "", `소비 연구영역: ${platform.consumers.join(", ")}`),
    );
    list.append(card);
  });
}

function renderMeetings() {
  const list = document.getElementById("meeting-project-list");
  DATA.projection.projects.forEach(project => {
    const card = node("article", "card");
    const fields = project.status.fields;
    card.append(
      statusPill(project.gate_state), node("h2", "", project.title),
      node("p", "metric-note", `${project.active_milestone_id} · raw state ${project.raw_state}`),
      node("h3", "", "실행 결과·근거"),
      node("p", "", (fields.evidence || ["canonical 문서에 기록되지 않음"])[0]),
      node("h3", "", "현재 blocker"),
      node("p", "", (fields.blocker || ["기록된 blocker 없음"])[0]),
      node("h3", "", "다음 단일 작업"),
      node("p", "", (fields.next || ["execution tracker 확인"])[0]),
    );
    const decisions = node("ul", "compact-list");
    project.decisions.forEach(item => decisions.append(node("li", "", `${item.decision_id} · ${item.status} · ${item.title}`)));
    if (!project.decisions.length) decisions.append(node("li", "", "project-owned decision record 없음"));
    card.append(node("h3", "", "관련 decision records"), decisions);
    const link = node("a", "button ghost", "프로젝트 원장 열기");
    link.href = `project_${String(project.order).padStart(2, "0")}.html`;
    card.append(link);
    list.append(card);
  });
}

function renderEvidence() {
  setText("artifact-count", String(DATA.artifact_registry.length));
  const owners = new Map();
  DATA.artifact_registry.forEach(item => {
    const key = `${item.owner_id}:${item.classification}`;
    owners.set(key, (owners.get(key) || 0) + 1);
  });
  const list = document.getElementById("evidence-owner-list");
  Array.from(owners.entries()).sort().forEach(([key, count]) => {
    const [owner, classification] = key.split(":");
    list.append(metricCard(owner, String(count), classification.toUpperCase()));
  });
}

async function renderArtifacts() {
  const list = document.getElementById("artifact-list");
  const selectedId = new URLSearchParams(location.search).get("id");
  if (selectedId) {
    document.getElementById("artifact-filters").hidden = true;
    try {
      const item = await apiJson(`/api/artifacts/${encodeURIComponent(selectedId)}`);
      const card = node("article", "card artifact-card");
      card.append(statusPill(item.classification), node("h2", "", item.run_label), node("p", "metric-note", `${item.owner_id} · ${item.artifact_id}`));
      if (item.claim_scope) card.append(node("p", "", item.claim_scope));
      const assets = node("div", "paper-actions");
      item.assets.forEach(asset => {
        const link = node("a", "button ghost", asset.label);
        link.href = `/assets/${item.artifact_id}/${asset.asset_id}`;
        assets.append(link);
      });
      card.append(assets);
      list.append(card);
    } catch (error) {
      list.append(node("div", "notice danger", error.message));
    }
    return;
  }
  const owner = document.getElementById("artifact-owner");
  const classification = document.getElementById("artifact-class");
  const search = document.getElementById("artifact-search");
  const count = document.getElementById("artifact-filter-count");
  Array.from(new Set(DATA.artifact_registry.map(item => item.owner_id))).sort().forEach(value => {
    const option = node("option", "", value); option.value = value; owner.append(option);
  });
  Array.from(new Set(DATA.artifact_registry.map(item => item.classification))).sort().forEach(value => {
    const option = node("option", "", value.toUpperCase()); option.value = value; classification.append(option);
  });
  const render = () => {
    list.replaceChildren();
    const query = search.value.trim().toLowerCase();
    const filtered = DATA.artifact_registry.filter(item =>
      (!owner.value || item.owner_id === owner.value) &&
      (!classification.value || item.classification === classification.value) &&
      (!query || `${item.run_label} ${item.experiment_id} ${item.owner_id}`.toLowerCase().includes(query))
    );
    count.textContent = `${filtered.length} / ${DATA.artifact_registry.length}개 실행`;
    filtered.forEach(item => {
      const card = node("article", "card artifact-card");
      const link = node("a", "button ghost", "상세·파일");
      link.href = `artifact.html?id=${encodeURIComponent(item.artifact_id)}`;
      card.append(
        statusPill(item.classification), node("h3", "", item.run_label),
        node("p", "metric-note", `${item.owner_id} · ${item.artifact_id}`),
        node("p", "", `RESULT ${item.has_result ? "있음" : "없음"} · REPORT ${item.has_report ? "있음" : "없음"}`), link,
      );
      list.append(card);
    });
    if (!filtered.length) list.append(node("div", "empty-state", "조건에 맞는 등록 실행이 없습니다."));
  };
  [owner, classification, search].forEach(control => control.addEventListener("input", render));
  render();
}

function apiMessage(target, message, error = false) {
  target.textContent = message;
  target.className = error ? "notice danger" : "notice info";
}

async function apiJson(path, options = {}) {
  const response = await fetch(path, {credentials: "same-origin", ...options});
  const data = await response.json().catch(() => ({error: "서버 응답을 읽을 수 없습니다."}));
  if (!response.ok) throw new Error(data.error || "요청이 거부됐습니다.");
  return data;
}

function renderLogin() {
  const form = document.getElementById("login-form");
  const message = document.getElementById("login-message");
  form.addEventListener("submit", async event => {
    event.preventDefault();
    try {
      const data = await apiJson("/api/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          actor_id: document.getElementById("actor-id").value,
          secret: document.getElementById("access-secret").value,
        }),
      });
      sessionStorage.setItem("gs_csrf_token", data.csrf_token);
      sessionStorage.setItem("gs_roles", JSON.stringify(data.roles || []));
      location.href = "review_round.html";
    } catch (error) {
      apiMessage(message, error.message, true);
    }
  });
}

async function renderReviewRounds() {
  const list = document.getElementById("round-list");
  const message = document.getElementById("round-message");
  const roles = JSON.parse(sessionStorage.getItem("gs_roles") || "[]");
  if (roles.includes("RESEARCH_LEAD")) renderLeadOperations();
  try {
    const data = await apiJson("/api/rounds");
    const leadRound = data.rounds.find(round => round.capability === "LEAD");
    if (leadRound) {
      document.querySelectorAll(".lead-round-id").forEach(input => {
        if (!input.value) input.value = leadRound.review_round_id;
      });
    }
    if (!data.rounds.length) {
      apiMessage(message, "배정된 검토 라운드가 없습니다.");
      return;
    }
    data.rounds.forEach(round => {
      const card = node("article", "card");
      card.append(statusPill(round.state), node("h2", "", round.purpose), node("p", "metric-note", `${round.review_type} · ${round.capability}`));
      if (round.capability === "REVIEW") {
        const link = node("a", "button", "내 배정 열기");
        link.href = `review_sample.html?round=${encodeURIComponent(round.review_round_id)}`;
        card.append(link);
      }
      if (round.capability === "ADJUDICATE") {
        const link = node("a", "button", "판정 대기열 열기");
        link.href = `review_adjudication.html?round=${encodeURIComponent(round.review_round_id)}`;
        card.append(link);
      }
      list.append(card);
    });
  } catch (error) {
    apiMessage(message, `${error.message} 로그인 후 다시 시도하십시오.`, true);
  }
}

function csrfHeaders() {
  return {"Content-Type": "application/json", "X-CSRF-Token": sessionStorage.getItem("gs_csrf_token") || ""};
}

async function postJson(path, body) {
  return apiJson(path, {method: "POST", headers: csrfHeaders(), body: JSON.stringify(body)});
}

function renderLeadOperations() {
  const section = document.getElementById("lead-operations");
  const message = document.getElementById("lead-message");
  const output = document.getElementById("lead-output");
  section.hidden = false;
  const report = data => {
    output.textContent = JSON.stringify(data, null, 2);
    apiMessage(message, "요청이 서버 audit에 기록되었습니다.");
  };
  const fail = error => apiMessage(message, error.message, true);
  const roundId = form => form.querySelector(".lead-round-id").value;

  document.getElementById("round-create-form").addEventListener("submit", async event => {
    event.preventDefault();
    try {
      const data = await postJson("/api/rounds", {
        review_round_id: document.getElementById("new-round-id").value,
        review_type: document.getElementById("new-round-type").value,
        purpose: document.getElementById("new-round-purpose").value,
      });
      document.querySelectorAll(".lead-round-id").forEach(input => { input.value = data.review_round_id; });
      report(data);
    } catch (error) { fail(error); }
  });
  document.getElementById("round-membership-form").addEventListener("submit", async event => {
    event.preventDefault();
    try { report(await postJson(`/api/rounds/${encodeURIComponent(roundId(event.currentTarget))}/memberships`, {actor_id: document.getElementById("member-actor-id").value, capability: document.getElementById("member-capability").value})); } catch (error) { fail(error); }
  });
  document.getElementById("manifest-form").addEventListener("submit", async event => {
    event.preventDefault();
    try { report(await postJson(`/api/rounds/${encodeURIComponent(roundId(event.currentTarget))}/manifest`, JSON.parse(document.getElementById("manifest-json").value))); } catch (error) { fail(error); }
  });
  document.getElementById("assignment-form").addEventListener("submit", async event => {
    event.preventDefault();
    try { report(await postJson(`/api/rounds/${encodeURIComponent(roundId(event.currentTarget))}/assignments`, {reviewers_per_sample: Number(document.getElementById("reviewers-per-sample").value), seed: document.getElementById("assignment-seed").value})); } catch (error) { fail(error); }
  });
  document.getElementById("guideline-form").addEventListener("submit", async event => {
    event.preventDefault();
    try { report(await postJson(`/api/rounds/${encodeURIComponent(roundId(event.currentTarget))}/guidelines`, {content_hash: document.getElementById("guideline-hash").value})); } catch (error) { fail(error); }
  });
  const gateId = () => encodeURIComponent(document.getElementById("gate-round-id").value);
  document.getElementById("calibration-start").addEventListener("click", async () => { try { report(await postJson(`/api/rounds/${gateId()}/calibration/start`, {schema_ui_export_validated: true})); } catch (error) { fail(error); } });
  document.getElementById("calibration-complete").addEventListener("click", async () => { try { report(await postJson(`/api/rounds/${gateId()}/calibration/complete`, {calibration_complete: true, reviewer_training_complete: true, baseline_model_split_manifest_frozen: true})); } catch (error) { fail(error); } });
  document.getElementById("empirical-start").addEventListener("click", async () => { try { report(await postJson(`/api/rounds/${gateId()}/empirical/start`, {})); } catch (error) { fail(error); } });
  document.getElementById("round-metrics").addEventListener("click", async () => { try { report(await apiJson(`/api/rounds/${gateId()}/metrics`)); } catch (error) { fail(error); } });
  document.getElementById("round-public-export").addEventListener("click", async () => {
    try {
      report(await postJson(`/api/rounds/${gateId()}/public-export`, {
        run_id: document.getElementById("public-export-run-id").value,
        claim_limitations: document.getElementById("public-export-limitations").value.split("\n").map(item => item.trim()).filter(Boolean),
      }));
    } catch (error) { fail(error); }
  });
  document.getElementById("round-finalize").addEventListener("click", async () => { try { report(await postJson(`/api/rounds/${gateId()}/finalize`, {terminal_shortfall: false})); } catch (error) { fail(error); } });
  document.getElementById("round-shortfall").addEventListener("click", async () => { try { report(await postJson(`/api/rounds/${gateId()}/finalize`, {terminal_shortfall: true})); } catch (error) { fail(error); } });
}

async function renderReviewSample() {
  const params = new URLSearchParams(location.search);
  const roundId = params.get("round");
  const list = document.getElementById("assignment-list");
  const message = document.getElementById("sample-message");
  if (!roundId) {
    apiMessage(message, "검토 라운드가 지정되지 않았습니다.", true);
    return;
  }
  try {
    const data = await apiJson(`/api/rounds/${encodeURIComponent(roundId)}/assignments`);
    if (!data.assignments.length) {
      apiMessage(message, "이 라운드에 배정된 샘플이 없습니다.");
      return;
    }
    let showAssignment = () => {};
    data.assignments.forEach((assignment, assignmentIndex) => {
      const form = node("form", "card review-submit");
      form.append(node("h2", "", assignment.sample_id), node("p", "metric-note", assignment.assignment_id));
      const sample = assignment.sample || {};
      const sourceSummary = node("details", "");
      sourceSummary.append(node("summary", "", "배정된 source binding 보기"));
      const sourceList = node("ul", "compact-list");
      Object.entries(sample.required_sources || {}).forEach(([field, source]) => {
        sourceList.append(node("li", "", `${field}: ${source.source_id} · SHA-256 ${source.sha256}`));
      });
      if (!sourceList.children.length) sourceList.append(node("li", "", "등록된 source binding 없음"));
      sourceSummary.append(
        node("p", "metric-note", `${sample.slice || "미기록"} · ${sample.outcome || "미기록"} · ${sample.source_closure || "미기록"}`),
        sourceList,
      );
      if ((sample.reason_codes || []).length) sourceSummary.append(node("p", "metric-note", `reason: ${sample.reason_codes.join(", ")}`));
      form.append(sourceSummary);
      const select = node("select");
      ["SOURCE_COMPLETE", "REVIEW_REQUIRED", "UNSUPPORTED", "CONFLICT"].forEach(value => {
        const option = node("option", "", value);
        option.value = value;
        select.append(option);
      });
      const rationale = node("textarea");
      rationale.placeholder = "판정 근거 또는 source reference";
      const expertPayload = node("textarea");
      expertPayload.placeholder = "M16 expert 구조화 payload JSON";
      expertPayload.value = JSON.stringify({applicability: "APPLICABLE", field_values: {}, source_ids: [], corrections: [], confidence: 1, calibration: false}, null, 2);
      if (assignment.review_type === "M16_EXPERT_PILOT") form.append(expertPayload);
      const submit = node("button", "button", assignment.has_finalized ? "Revision 제출" : "판정 확정");
      submit.type = "submit";
      form.append(select, rationale, submit);
      let activityStarted = false;
      let heartbeat = null;
      const touch = async action => postJson(`/api/assignments/${encodeURIComponent(assignment.assignment_id)}/activity/${action}`, {});
      form.addEventListener("focusin", async () => {
        if (activityStarted) return;
        activityStarted = true;
        try {
          await touch("start");
          heartbeat = window.setInterval(() => {
            if (!document.hidden && form.contains(document.activeElement)) touch("heartbeat").catch(() => {});
          }, 60000);
        } catch (error) { apiMessage(message, error.message, true); }
      });
      form.addEventListener("submit", async event => {
        event.preventDefault();
        try {
          const revision = assignment.latest_revision === null ? 0 : assignment.latest_revision + 1;
          if (activityStarted) await touch("heartbeat");
          const reviewPayload = assignment.review_type === "M16_EXPERT_PILOT" ? JSON.parse(expertPayload.value) : undefined;
          await apiJson(`/api/assignments/${assignment.assignment_id}/reviews`, {
            method: "POST",
            headers: csrfHeaders(),
            body: JSON.stringify({verdict: select.value, rationale: rationale.value, revision, finalize: true, payload: reviewPayload}),
          });
          if (heartbeat !== null) window.clearInterval(heartbeat);
          submit.disabled = true;
          submit.textContent = "제출 완료";
          if (assignmentIndex + 1 < data.assignments.length) showAssignment(assignmentIndex + 1);
        } catch (error) {
          apiMessage(message, error.message, true);
        }
      });
      list.append(form);
    });
    const cards = Array.from(list.children);
    const navigation = document.getElementById("sample-navigation");
    const previous = document.getElementById("sample-previous");
    const next = document.getElementById("sample-next");
    const position = document.getElementById("sample-position");
    let current = 0;
    showAssignment = index => {
      current = Math.max(0, Math.min(index, cards.length - 1));
      cards.forEach((card, cardIndex) => { card.hidden = cardIndex !== current; });
      previous.disabled = current === 0;
      next.disabled = current === cards.length - 1;
      position.textContent = `${current + 1} / ${cards.length}`;
      cards[current].querySelector("select").focus();
    };
    navigation.hidden = false;
    previous.addEventListener("click", () => showAssignment(current - 1));
    next.addEventListener("click", () => showAssignment(current + 1));
    showAssignment(0);
  } catch (error) {
    apiMessage(message, `${error.message} 로그인 후 다시 시도하십시오.`, true);
  }
}

async function renderAdjudication() {
  const roundId = new URLSearchParams(location.search).get("round");
  const list = document.getElementById("adjudication-list");
  const message = document.getElementById("adjudication-message");
  if (!roundId) {
    apiMessage(message, "판정 라운드가 지정되지 않았습니다.", true);
    return;
  }
  try {
    const data = await apiJson(`/api/rounds/${encodeURIComponent(roundId)}/adjudications`);
    if (!data.queue.length) {
      apiMessage(message, "판정 가능한 disagreement가 없습니다.");
      return;
    }
    data.queue.forEach(sample => {
      const form = node("form", "card review-submit");
      form.append(node("h2", "", sample.sample_id));
      const originals = node("ul", "compact-list");
      sample.original_verdicts.forEach(item => originals.append(node("li", "", `${item.reviewer_id}: ${item.verdict}`)));
      const select = node("select");
      ["SOURCE_COMPLETE", "REVIEW_REQUIRED", "UNSUPPORTED", "CONFLICT"].forEach(value => {
        const option = node("option", "", value); option.value = value; select.append(option);
      });
      const rationale = node("textarea"); rationale.placeholder = "판정 rationale과 source reference";
      const finalFields = node("textarea");
      finalFields.placeholder = "최종 field record JSON (선택)";
      finalFields.value = "{}";
      const submit = node("button", "button", "최종 판정 제출"); submit.type = "submit";
      form.append(originals, select, rationale, finalFields, submit);
      form.addEventListener("submit", async event => {
        event.preventDefault();
        try {
          await apiJson(`/api/rounds/${encodeURIComponent(roundId)}/samples/${sample.sample_id}/adjudication`, {
            method: "POST",
            headers: {"Content-Type": "application/json", "X-CSRF-Token": sessionStorage.getItem("gs_csrf_token") || ""},
            body: JSON.stringify({verdict: select.value, rationale: rationale.value, payload: {final_fields: JSON.parse(finalFields.value)}}),
          });
          submit.disabled = true; submit.textContent = "판정 완료";
        } catch (error) { apiMessage(message, error.message, true); }
      });
      list.append(form);
    });
  } catch (error) { apiMessage(message, `${error.message} 로그인 후 다시 시도하십시오.`, true); }
}

function renderPortfolioMilestones() {
  const list = document.getElementById("portfolio-milestones");
  DATA.research_projects.forEach(project => {
    const card = node("article", "card portfolio-status-card");
    const head = node("div", "section-head");
    head.append(node("span", "structure-order", String(project.order).padStart(2, "0")), statusPill(project.state));
    card.append(
      head,
      node("h2", "", project.title),
      node("p", "metric-note", `${project.milestones.length}개 마일스톤`),
      node("h3", "", `${project.active_milestone_id} · ${project.active_milestone.title}`),
      node("p", "", project.current_task),
    );
    const link = node("a", "button", "독립 마일스톤 보기");
    link.href = project.page;
    card.append(link);
    list.append(card);
  });
}

function renderProject() {
  const project = projectByOrder();
  document.title = `${project.title} · GuardSynth-CC`;
  setText("project-number", `Research area ${String(project.order).padStart(2, "0")}`);
  setText("project-title", project.title);
  setText("project-overview", project.overview);
  setText("project-goal", project.goal);
  setText("project-plan-focus", project.plan_focus);
  setText("project-evidence", project.evidence);
  setText("project-boundary", project.boundary);
  setText("project-blocker", project.blocker);
  setText("project-next", project.next);
  setText("current-task", project.current_task);
  setText("active-milestone-title", `${project.active_milestone_id} · ${project.active_milestone.title}`);
  setText("active-milestone-summary", project.active_milestone.summary);
  setText("project-milestone-count", `${project.milestones.length}개`);
  setText("project-review-summary", project.review_pages.length ? `${project.review_pages.length}개 검토 패키지가 이 연구영역에 등록되어 있습니다.` : "현재 등록된 검토 패키지가 없습니다.");
  setText("project-sync-mode", project.tracking_sync.mode === "LIVE_ON_PAGE_LOAD" ? "페이지를 열 때 권위 문서에서 자동 갱신" : "빌드 스냅샷");
  const state = document.getElementById("project-state");
  state.className = `status ${statusClass(project.state)}`;
  state.textContent = project.state;
  const active = document.getElementById("active-milestone-status");
  active.className = `status ${statusClass(project.active_milestone.status)}`;
  active.textContent = project.active_milestone.status;
  const reviewLink = document.getElementById("project-review-link");
  reviewLink.href = project.review_page;
  const switcher = document.getElementById("project-switcher");
  DATA.research_projects.forEach(item => {
    const link = node("a", `project-switch${item.id === project.id ? " active" : ""}`, String(item.order).padStart(2, "0"));
    link.href = item.page;
    link.title = item.title;
    switcher.append(link);
  });
  const milestones = document.getElementById("project-milestones");
  project.milestones.forEach(item => milestones.append(milestoneDetails(item, item.id === project.active_milestone_id)));
}

function renderReviewSelector() {
  const list = document.getElementById("review-project-list");
  if (list.dataset.rendered === "true") return;
  DATA.research_projects.forEach(project => list.append(projectCard(project, true)));
}

function renderProjectReview() {
  const project = projectByOrder();
  document.title = `${project.title} 검토 · GuardSynth-CC`;
  setText("review-project-title", `${project.title} 검토`);
  setText("review-count", `${project.review_pages.length}개`);
  setText("review-boundary", project.boundary);
  document.getElementById("review-project-link").href = project.page;
  const empty = document.getElementById("empty-review");
  const workspace = document.getElementById("review-workspace");
  if (!project.review_pages.length) {
    empty.hidden = false;
    workspace.hidden = true;
    return;
  }
  const menu = document.getElementById("review-menu");
  const menuPanel = document.getElementById("review-menu-panel");
  menuPanel.hidden = project.review_pages.length <= 1;
  const frame = document.getElementById("review-frame");
  const title = document.getElementById("review-title");
  const open = document.getElementById("review-open");
  function select(page, button) {
    menu.querySelectorAll("button").forEach(item => item.classList.remove("active"));
    button.classList.add("active");
    title.textContent = page.title;
    frame.src = page.href;
    open.href = page.href;
  }
  project.review_pages.forEach((page, index) => {
    const button = node("button", "review-option");
    button.type = "button";
    button.append(
      node("strong", "", page.title),
      node("small", "", `${page.review_time} · ${page.description}`),
    );
    button.addEventListener("click", () => select(page, button));
    menu.append(button);
    if (index === 0) select(page, button);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  if (!DATA) throw new Error("portal data is missing");
  renderCommon();
  const page = document.body.dataset.page;
  if (page === "overview") renderOverview();
  if (page === "projects") renderProjects();
  if (page === "platform") renderPlatform();
  if (page === "meetings") renderMeetings();
  if (page === "evidence") renderEvidence();
  if (page === "artifact") renderArtifacts();
  if (page === "login") renderLogin();
  if (page === "review-round") renderReviewRounds();
  if (page === "review-sample") renderReviewSample();
  if (page === "adjudication") renderAdjudication();
  if (page === "milestones") renderPortfolioMilestones();
  if (page === "project") renderProject();
  if (page === "review" || page === "reviews") renderReviewSelector();
  if (page === "project-review") renderProjectReview();
});
