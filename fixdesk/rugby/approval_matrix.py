def approval_matrix(type, role, department):
    APPROVAL_MATRIX = {
        "procurementrequest": {
            "Non-Academic - Procurement": {
                "team_lead": ["Non-Academic - Accounting"],
                "staff": ["Team Lead", "Non-Academic - Accounting"],
            },
            "*": {
                "team_lead": ["Non-Academic - Procurement", "Non-Academic - Accounting"],
                "staff": ["Team Lead", "Non-Academic - Procurement", "Non-Academic - Accounting"],
            },
        },
        "leaverequest": {
            "Non-Academic - HR": {
                "team_lead": ["Senior Leadership Team"],
                "staff": ["Team Lead", "Senior Leadership Team"],
            },
            "Senior Leadership Team": {
                "team_lead": ["Non-Academic - HR"],
                "staff": ["Team Lead", "Non-Academic - HR"],
            },
            "*": {
                "team_lead": ["Non-Academic - HR", "Senior Leadership Team"],
                "staff": ["Team Lead", "Non-Academic - HR", "Senior Leadership Team"],
            },
        },
    }

    type_rules = APPROVAL_MATRIX.get(type)
    if not type_rules:
        return {}, 0

    dept_rules = type_rules.get(department) or type_rules.get("*")
    if not dept_rules:
        return {}, 0

    level_titles = dept_rules.get(role)
    if not level_titles:
        return {}, 0

    approval_info = build_approval_structure(level_titles)
    number_of_levels = len(level_titles)

    return approval_info, number_of_levels


def build_approval_structure(level_titles):
    approval_info = {}

    for index, title in enumerate(level_titles, start=1):
        approval_info[f"l{index}"] = {
            "title": title,
            "name": "",
            "date": "",
            "comment": "",
            "approver_id": "",
            "status": ""
        }

    return approval_info

def resolve_approvers(title: str, requester, User_model) -> list[dict]:
    """
    Returns a list of approvers for this level as:
    [{"id": <uuid>, "email": "<email>"}]
    """

    def dept_team_leads(dept_name: str) -> list[dict]:
        return list(
            User_model.objects
            .filter(department=dept_name, role="team_lead")
            .values("id", "email")
        )

    title = title.strip().lower()

    if title == "team lead":
        return dept_team_leads(requester.department)

    if title == "Non-Academic - HR":
        return dept_team_leads("Non-Academic - HR")

    if title == "Non-Academic - Procurement":
        return dept_team_leads("Non-Academic - Procurement")

    if title == "Non-Academic - Accounting":
        return dept_team_leads("Non-Academic - Accounting")

    if title == "Senior Leadership Team":
        return dept_team_leads("Senior Leadership Team")

    return []

def attach_approvers_to_approval_info(approval_info: dict, requester, User_model) -> dict:
    for _, level_data in approval_info.items():
        title = level_data.get("title", "")
        approvers = resolve_approvers(title, requester, User_model)

        # store full list
        level_data["approvers"] = approvers  # [{"id":..., "email":...}, ...]

        # convenience fields
        level_data["approver_ids"] = [a["id"] for a in approvers]
        level_data["approver_emails"] = [a["email"] for a in approvers]

        # optional "primary"
        level_data["approver_id"] = approvers[0]["id"] if approvers else ""
        level_data["approver_email"] = approvers[0]["email"] if approvers else ""

    return approval_info

def extract_approval_emails(approval_info: dict) -> list[str]:
    emails = set()

    for level in approval_info.values():
        level_emails = level.get("approver_emails", [])
        emails.update(level_emails)

    return list(emails)