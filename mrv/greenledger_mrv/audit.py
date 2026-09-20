from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone

def canonical_hash(payload):
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'),default=str).encode()
    return hashlib.sha256(raw).hexdigest()

def make_audit_event(event_type, payload, methodology_id, methodology_version):
    return {'event_type':event_type,'methodology_id':methodology_id,'methodology_version':methodology_version,'timestamp':datetime.now(timezone.utc).isoformat(),'payload_hash':canonical_hash(payload)}
