"""Phase212-A: backend-neutral bounded mechanical-design evaluation.

No bpy dependency. A design backend supplies measured observations, explicit
limits, and a frozen set of candidate IDs. Missing or invalid evidence never
passes; a short screen cannot promote itself to a full physical result.
"""
from dataclasses import dataclass
import math
from typing import Optional

@dataclass(frozen=True)
class Limit:
    name: str
    lower: Optional[float] = None
    upper: Optional[float] = None
    def __post_init__(self):
        if not self.name or (self.lower is None and self.upper is None):
            raise ValueError("named bounded metric required")
        if any(v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)) for v in (self.lower,self.upper)):
            raise ValueError("finite numeric limit required")
        if self.lower is not None and self.upper is not None and self.lower>self.upper:
            raise ValueError("inverted limit")
    def accepts(self,value):
        return ((self.lower is None or value>=self.lower) and
                (self.upper is None or value<=self.upper))

def finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)

def evaluate(limits,observations):
    """Observations maps metric -> [(frame, part, value), ...] in time order."""
    limits=tuple(limits)
    if not limits or len({l.name for l in limits})!=len(limits):
        raise ValueError("nonempty unique metric limits required")
    details={}
    for limit in limits:
        series=observations.get(limit.name)
        if not series:
            details[limit.name]={"status":"unverified","reason":"missing"}
            continue
        rows=list(series)
        if not rows or any(not isinstance(r,(tuple,list)) or len(r)!=3 or
                type(r[0]) is not int or r[0]<1 or not isinstance(r[1],str) or
                not r[1] or not finite(r[2]) for r in rows):
            details[limit.name]={"status":"unverified","reason":"invalid"}
            continue
        if any(a[0]>b[0] for a,b in zip(rows,rows[1:])):
            details[limit.name]={"status":"unverified","reason":"out_of_order"}
            continue
        bad=next((r for r in rows if not limit.accepts(r[2])),None)
        details[limit.name]={"status":"fail" if bad else "pass","count":len(rows),
            "min":min(r[2] for r in rows),"max":max(r[2] for r in rows),
            "first":dict(frame=bad[0],part=bad[1],value=bad[2]) if bad else None}
    states=[d["status"] for d in details.values()]
    status="fail" if "fail" in states else "unverified" if "unverified" in states else "pass"
    firsts=[(d["first"]["frame"],name,d["first"]) for name,d in details.items() if d.get("first")]
    first=None
    if firsts:
        _,metric,record=min(firsts,key=lambda r:(r[0],r[1]))
        first=dict(metric=metric,**record)
    return dict(status=status,metrics=details,first=first)

def select_candidate(candidate_ids,results,budget):
    """Only declared candidates may be measured; ranks are fixed before screening."""
    ids=tuple(candidate_ids)
    if type(budget) is not int or budget<1 or not ids or len(ids)>budget or len(set(ids))!=len(ids):
        raise ValueError("invalid finite candidate plan")
    if any(not isinstance(x,str) or not x for x in ids) or set(results)-set(ids):
        raise ValueError("unknown candidate")
    states={x:results.get(x,"unverified") for x in ids}
    if any(s not in ("pass","fail","unverified") for s in states.values()):
        raise ValueError("invalid candidate state")
    if "unverified" in states.values():
        return dict(selected=None,action="collect_missing_evidence",states=states)
    selected=next((x for x in ids if states[x]=="pass"),None)
    return dict(selected=selected,action="full_validation" if selected else "stop_and_redesign",states=states)

def qualification(stages,required=("geometry","screen","full_motion","negative_controls")):
    """No missing stage, user demonstration, or CI success can imply certification."""
    required=tuple(required)
    if not required or len(set(required))!=len(required):
        raise ValueError("unique required stages")
    states={s:stages.get(s,"unverified") for s in required}
    if any(s not in ("pass","fail","unverified") for s in states.values()):
        raise ValueError("invalid stage state")
    status="fail" if "fail" in states.values() else "unverified" if "unverified" in states.values() else "pass"
    return dict(status=status,stages=states,certified=status=="pass")
