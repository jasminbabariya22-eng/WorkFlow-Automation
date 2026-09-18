import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import ClientDatabaseAdapter

ctx = {
    "parameter": {
        "Name": "Ram",
        "Address": "Delhi",
        "pocket_no": "22",
        "Incident_Id": "INC-9999"
    },
    "status": "APPROVED",
    "id": 42
}

subj_template = 'Notification for {Name} - Ticket #{id}'
body_template = 'New Incident created = {Incident_Id} at {Address}, Pocket: {pocket_no}. Status={status}'

res_subj = ClientDatabaseAdapter._resolve_template_value(subj_template, ctx)
res_body = ClientDatabaseAdapter._resolve_template_value(body_template, ctx)

print("Resolved Subject:", res_subj)
print("Resolved Body:", res_body)

assert "Ram" in res_subj
assert "42" in res_subj
assert "INC-9999" in res_body
assert "Delhi" in res_body
assert "22" in res_body
assert "APPROVED" in res_body

print(">>> ALL PARAMETER REPLACEMENT ASSERTIONS PASSED SUCCESSFULLY! <<<")
