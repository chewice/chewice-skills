// Public academic talks supplement the research module, not paper evidence.
const list = value => Array.isArray(value) ? value : [];
const get = (row, key) => row?.[key] ?? row?.[key.replace(/[A-Z]/g, char => `_${char.toLowerCase()}`)] ?? null;
const refs = row => [...new Set(list(get(row, "sourceIds")).map(String))];
const roles = {keynote:"大会报告", invited:"邀请报告", oral:"分会场报告", speaker:"演讲报告", panelist:"讨论嘉宾", chair:"主持", attendee:"参会", unknown:"角色待核实"};
const speakers = new Set(["keynote", "invited", "oral", "speaker"]);
const searchStates = new Set(["found", "not_found", "partial", "inaccessible", "not_checked"]);
const unique = rows => [...new Map(rows.map(row => [JSON.stringify(row),row])).values()];

export function academicEvents(source = {}) {
  return {
    academicTalks: list(get(source, "academicTalks")).filter(row => row && typeof row === "object").map(row => ({
      eventName:get(row,"eventName"), date:row.date || null, role:Object.hasOwn(roles,row.role) ? row.role : "unknown",
      talkTitle:get(row,"talkTitle"), talkTitleZh:get(row,"talkTitleZh"), url:row.url || null,
      participationStatus:get(row,"participationStatus") || "unknown", identityStatus:get(row,"identityStatus") || "not_checked",
      checkedAt:get(row,"checkedAt"), sourceIds:refs(row), limitations:row.limitations || null,
    })),
    talkSearches: list(get(source, "talkSearches")).filter(row => row && typeof row === "object").map(row => ({
      database:row.database || null, query:row.query || null, checkedAt:get(row,"checkedAt"),
      windowStart:get(row,"windowStart"), windowEnd:get(row,"windowEnd"),
      status:searchStates.has(row.status) ? row.status : "not_checked", sourceIds:refs(row), limitations:row.limitations || null,
    })),
  };
}

export function mergeAcademicEvents(current, incoming) {
  const left = academicEvents(current), right = academicEvents(incoming);
  return {academicTalks:unique([...left.academicTalks,...right.academicTalks]), talkSearches:unique([...left.talkSearches,...right.talkSearches])};
}

const dateValid = value => typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)
  && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0,10) === value;

export function talkWindow(searches) {
  const search = searches.filter(row => dateValid(row.checkedAt)).sort((a,b) => b.checkedAt.localeCompare(a.checkedAt))[0];
  if (!search) return null;
  const start = new Date(`${search.checkedAt}T00:00:00Z`);
  const month = start.getUTCMonth();
  start.setUTCFullYear(start.getUTCFullYear()-2);
  if (start.getUTCMonth() !== month) start.setUTCDate(0);
  const window = {start:start.toISOString().slice(0,10), end:search.checkedAt};
  return search.windowStart === window.start && search.windowEnd === window.end ? window : null;
}

function supportingRows(ids, evidence, advisorId, status = "verified") {
  return list(evidence).filter(row => ids.includes(row.evidence_id || row.evidenceId)
    && (row.entity_id || row.entity) === advisorId && row.status === status
    && /^https?:\/\/[^\s]+$/i.test(row.final_url || row.source_url || row.url || ""));
}

export function talkSearchComplete(mainline, evidence, advisorId) {
  return mainline.talkSearches.length > 0 && mainline.talkSearches.every(row =>
    row.database && row.query && talkWindow([row]) && ["found","not_found"].includes(row.status)
    && supportingRows(row.sourceIds,evidence,advisorId,row.status === "found" ? "verified" : "not_found").length > 0)
    && (!mainline.talkSearches.some(row => row.status === "found") || mainline.academicTalks.length > 0)
    && academicTalkRows(mainline,evidence,advisorId).every(row => row.timing === "范围外记录" ||
      (row.timing !== "日期或检索范围待核实" && row.role !== "unknown" &&
        ["已确认报告","预告安排（实际报告待核实）","非演讲角色／角色待核实"].includes(row.status)));
}

export function academicTalkRows(mainline, evidence, advisorId) {
  const window = talkWindow(mainline.talkSearches);
  const seen = new Set();
  return mainline.academicTalks.filter(row => {
    const key = JSON.stringify(row);
    if (seen.has(key)) return false;
    seen.add(key); return true;
  }).map(row => {
    const timing = window && dateValid(row.date)
      ? row.date > window.end ? "即将举行" : row.date < window.start ? "范围外记录" : "近两年活动"
      : "日期或检索范围待核实";
    const sources = supportingRows(row.sourceIds,evidence,advisorId);
    const matched = row.identityStatus === "verified" && sources.some(source =>
      ["conference_programme","event_announcement","event_report","recording"].includes(source.source_type));
    const deliveryEvidence = sources.some(source => ["event_report","recording"].includes(source.source_type));
    const programmeEvidence = sources.some(source => ["conference_programme","event_announcement"].includes(source.source_type));
    const isSpeaker = speakers.has(row.role);
    let status = "参与情况待核实";
    if (!matched) status = "导师身份或活动证据待核实";
    else if (!isSpeaker) status = "非演讲角色／角色待核实";
    else if (row.participationStatus === "delivered" && deliveryEvidence && timing === "近两年活动") status = "已确认报告";
    else if (programmeEvidence) status = "预告安排（实际报告待核实）";
    else if (timing === "即将举行" && deliveryEvidence) status = "活动日期与报告证据冲突，待核实";
    return {...row, timing, status, roleLabel:roles[row.role],
      title:isSpeaker ? row.talkTitle || "演讲标题未公开／未查到" : "未确认个人演讲，不以分会场主题代替标题",
      titleZh:isSpeaker && row.talkTitle ? row.talkTitleZh : null};
  });
}

export function academicTalkSummary(mainline, evidence, advisorId) {
  const window = talkWindow(mainline.talkSearches);
  const searches = mainline.talkSearches.map(row => `${row.database || "来源未记录"} | ${row.query || "查询未记录"} | ${row.status} | ${row.checkedAt || "日期未记录"} | ${row.limitations || ""} | ${row.sourceIds.join(", ")}`);
  return [window ? `检索范围：${window.start} 至 ${window.end}；未来活动单列` : "未记录有效的近两年检索范围",
    searches.length ? searches.join("\n") : "未记录会议与演讲检索，不代表没有活动",
    ...academicTalkRows(mainline,evidence,advisorId).map(row => [row.timing,row.eventName || "活动名称未记录",row.date || "日期待核实",row.roleLabel,row.title,row.titleZh,row.status,row.url,row.limitations,row.sourceIds.join(", ")].filter(Boolean).join(" | "))].join("\n");
}
