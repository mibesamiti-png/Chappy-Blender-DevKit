function scenarios(required,dev) {
  const dispatch={schema:"cbdk-role-dispatch-v1",state:"active",round:"R16",official_assignment:"docs/R16_ABCD_START.md",revision:1,development_branch:"feature/v0.18-shape-diagnostics",phase:"normal",team_roles:{B:"B",C:"C",D:"D"}};
  const s={devHead:dev,finalReadHead:dev,officialRound:"R16",officialAssignment:"docs/R16_ABCD_START.md",team:"B",dispatch,minimumRevision:1,requiredFamilies:required,expectedCIHead:dev,expectedEvent:"push",runs:required.map((name,i)=>({name,head_sha:dev,event:"push",status:"completed",conclusion:"success",id:i+1}))};
  const clone=()=>JSON.parse(JSON.stringify(s));
  const cases=[];
  const add=(id,change,state,reason,details,role)=>{const x=clone();change(x);cases.push({id,input:x,expect:{state,reason,details,role}})};
  add("green",()=>{},"summary_ready","family_summaries_green_not_execution_authority",0,"B");
  add("red",x=>x.runs[0].conclusion="failure","blocked","ci_not_all_verified",1);
  add("running",x=>{x.runs[0].status="in_progress";x.runs[0].conclusion=null},"blocked","ci_not_all_verified",0);
  add("cancelled",x=>x.runs[0].conclusion="cancelled","blocked","ci_not_all_verified",0);
  add("missing",x=>x.runs.pop(),"blocked","ci_not_all_verified",0);
  add("stale",x=>x.runs[0].head_sha="a".repeat(40),"blocked","ci_not_all_verified",0);
  add("wrong_event",x=>x.runs[0].event="pull_request","blocked","ci_not_all_verified",0);
  add("duplicate",x=>x.runs.push({...x.runs[0],id:99}),"blocked","ci_not_all_verified",0);
  add("head_moved",x=>x.finalReadHead="a".repeat(40),"blocked","head_missing_or_changed",0);
  add("wrong_round",x=>x.dispatch.round="R15","blocked","dispatch_unverified",0);
  add("revision_rollback",x=>x.minimumRevision=2,"blocked","dispatch_unverified",0);
  add("role_conflict",x=>x.dispatch.team_roles.B="E","blocked","dispatch_conflict",0);
  add("unknown_ci_contract",x=>x.requiredFamilies=[],"blocked","ci_contract_unknown",0);
  add("dynamic_round",x=>{x.officialRound="R17";x.officialAssignment="docs/R17_ABCD_START.md";x.dispatch.round="R17";x.dispatch.official_assignment=x.officialAssignment},"summary_ready","family_summaries_green_not_execution_authority",0,"B");
  add("support_hint",x=>{x.dispatch.phase="integration_support";x.dispatch.team_roles={B:"E",C:"G",D:"F"}},"summary_ready","family_summaries_green_not_execution_authority",0,"E");
  return cases;
}

function assess(cases,route,batchPlan,dev){
  const rows=cases.map(c=>{const r=route(c.input),e=c.expect;return {id:c.id,pass:r.state===e.state&&r.reason===e.reason&&r.detailRequests.length===e.details&&(e.role===undefined||r.roleHint===e.role)&&!r.mayExecute&&!r.mayMerge&&!r.maySkipCI,result:r}});
  const item={id:"a",owner:"B",invariant:"same",fixture:"f",acceptance:"g",scope:"owned",baseHead:dev};
  const batches=[["same_family",[item,{...item,id:"b"}],true],["mixed_owner",[item,{...item,id:"b",owner:"C"}],false],["mixed_fixture",[item,{...item,id:"b",fixture:"other"}],false],["duplicate",[item,item],false],["over_budget",Array.from({length:9},(_,i)=>({...item,id:String(i)})),false]];
  const b=batches.map(([id,items,expect])=>{const r=batchPlan(items);return {id,pass:r.eligible===expect&&r.permission!==true,result:r}});
  return {routing:rows,batching:b,passed:[...rows,...b].filter(x=>x.pass).length,total:rows.length+b.length};
}

export { scenarios, assess };
