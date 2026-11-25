function route(s) {
  const out={state:"blocked",reason:"invalid_snapshot",mandatoryReads:[],detailRequests:[],ci:{success:0,required:0},mayExecute:false,mayMerge:false,maySkipCI:false};
  const sha=x=>typeof x==="string"&&/^[0-9a-f]{40}$/.test(x);
  if(!s||!sha(s.devHead)||!sha(s.finalReadHead)||s.devHead!==s.finalReadHead){out.reason="head_missing_or_changed";return out}
  if(!/^R[1-9][0-9]*$/.test(s.officialRound||"")||s.officialAssignment!==`docs/${s.officialRound}_ABCD_START.md`||!["A","B","C","D"].includes(s.team)){out.reason="official_scope_unknown";return out}
  out.mandatoryReads=["AGENTS.md","docs/PARALLEL_DEVELOPMENT.md",s.officialAssignment,"docs/PROJECT_HANDOFF.md (or docs/project/STATE.json if absent)","docs/PROJECT_SPEC.md","pyproject.toml","assigned code and tests"];
  const d=s.dispatch;
  if(!d||d.schema!=="cbdk-role-dispatch-v1"||d.state!=="active"||d.round!==s.officialRound||d.official_assignment!==s.officialAssignment||!Number.isInteger(d.revision)||d.revision<0||!Number.isInteger(s.minimumRevision)||d.revision<s.minimumRevision||d.development_branch!=="feature/v0.18-shape-diagnostics"){out.reason="dispatch_unverified";return out}
  const map=d.phase==="normal"?{B:"B",C:"C",D:"D"}:d.phase==="integration_support"?{B:"E",C:"G",D:"F"}:null;
  if(!map||!d.team_roles||Object.keys(d.team_roles).length!==3||Object.keys(map).some(k=>map[k]!==d.team_roles[k])){out.reason="dispatch_conflict";return out}
  if(!Array.isArray(s.requiredFamilies)||s.requiredFamilies.length===0||new Set(s.requiredFamilies).size!==s.requiredFamilies.length||s.requiredFamilies.some(x=>typeof x!=="string"||!x)||!Array.isArray(s.runs)||!["push","pull_request"].includes(s.expectedEvent)||!sha(s.expectedCIHead)){out.reason="ci_contract_unknown";return out}
  out.ci.required=s.requiredFamilies.length;
  const unresolved=[];
  for(const name of s.requiredFamilies){
    const matches=s.runs.filter(x=>x&&x.name===name&&x.head_sha===s.expectedCIHead&&x.event===s.expectedEvent);
    if(matches.length!==1){unresolved.push({name,why:matches.length?"ambiguous_attempt":"missing_exact_head"});continue}
    const row=matches[0];
    if(row.status==="completed"&&row.conclusion==="success"){out.ci.success++;continue}
    unresolved.push({name,why:row.status==="completed"?row.conclusion||"unknown_conclusion":row.status||"unknown_status"});
    if(row.status==="completed"&&["failure","timed_out"].includes(row.conclusion)&&Number.isSafeInteger(row.id)&&row.id>0)out.detailRequests.push({runId:row.id,request:"failed_job_summary_then_failed_step_log_if_needed"});
  }
  out.unresolved=unresolved;
  if(unresolved.length){out.reason="ci_not_all_verified";return out}
  out.state="summary_ready";out.reason="family_summaries_green_not_execution_authority";
  out.roleHint=s.team==="A"?"A":map[s.team];
  out.next=["independently validate formal assignment and required jobs via existing A rules/preflight","confirm owned PR and exact head before any edit","fetch relevant source and tests; optional tags only for technical references"];
  return out;
}

function batchPlan(items) {
  if(!Array.isArray(items)||!items.length||items.length>8)return {eligible:false,reason:"empty_or_budget"};
  const keys=["owner","invariant","fixture","acceptance","baseHead","scope"];
  const a=items[0];
  if(items.some(x=>!x||typeof x.id!=="string"||!x.id||keys.some(k=>typeof x[k]!=="string"||!x[k]||x[k]!==a?.[k]))||new Set(items.map(x=>x.id)).size!==items.length||!["B","C","D"].includes(a.owner)||!/^[0-9a-f]{40}$/.test(a.baseHead))return {eligible:false,reason:"different_scope_or_invalid"};
  return {eligible:true,ids:items.map(x=>x.id),stages:["scope","freeze","implement_minimum","compare_each_case","close_with_exact_head_ci"],permission:false};
}

export { route, batchPlan };
