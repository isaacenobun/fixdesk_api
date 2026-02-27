from .models import Issues, Tasks, FacilityRequest, ProcurementRequest, LeaveRequest


def users_inclusion_matrix(
    email,
    User_model,
    role,
    department,
    subject,
    action,
    id=None
):
    # -----------------------------
    # Normalize inputs
    # -----------------------------
    role = role.lower()
    department = department.lower()
    subject = subject.lower()
    action = action.lower()

    # -----------------------------
    # Helper functions
    # -----------------------------
    def dept_users(dept):
        return set(
            User_model.objects.filter(department__iexact=dept)
            .values_list("email", flat=True)
        )

    def team_leads(dept):
        return set(
            User_model.objects.filter(
                department__iexact=dept,
                role="team_lead"
            ).values_list("email", flat=True)
        )

    def assigned_issue_users():
        if not id:
            return set()
        return set(
            Issues.objects.filter(id=id)
            .values_list("assigned_to__email", flat=True)
        )

    def issue_reporter():
        if not id:
            return set()
        return set(
            Issues.objects.filter(id=id)
            .values_list("reported_by__email", flat=True)
        )

    def assigned_task_users():
        if not id:
            return set()
        return set(
            Tasks.objects.filter(id=id)
            .values_list("assigned_to__email", flat=True)
        )

    def assigned_facility_users():
        if not id:
            return set()
        return set(
            FacilityRequest.objects.filter(id=id)
            .values_list("assigned_to__email", flat=True)
        )

    def assigned_procurement_users():
        if not id:
            return set()
        return set(
            ProcurementRequest.objects.filter(id=id)
            .values_list("assigned_to__email", flat=True)
        )
    
    def assigned_leave_users():
        if not id:
            return set()
        return set(
            LeaveRequest.objects.filter(id=id)
            .values_list("assigned_to__email", flat=True)
        )

    recipients = set()

    # ==========================================================
    # SUBJECT DISPATCH
    # ==========================================================

    # ==========================================================
    # ISSUE
    # ==========================================================
    if subject == "issue":

        if action == "creation":
            if department == "Non-Academic - IT":
                recipients |= dept_users("Non-Academic - IT")
                if role == "staff":
                    recipients -= {email}
                else:
                    recipients |= {email}

            elif department == "Non-Academic - HR":
                recipients |= dept_users("Non-Academic - IT")
                recipients |= team_leads("Non-Academic - HR")
                recipients |= {email}

            elif department == "facilities":
                recipients |= dept_users("Non-Academic - IT")
                recipients |= team_leads("facilities")

            else:
                recipients |= dept_users("Non-Academic - IT")
                recipients |= {email}

        elif action == "status_change":
            recipients |= dept_users("Non-Academic - IT")
            recipients |= {email}

        elif action == "comment":
            recipients |= dept_users("Non-Academic - IT")

            if role == "team_lead" and department == "Non-Academic - IT":
                recipients |= issue_reporter()

            recipients -= {email}

        elif action == "assigned":
            recipients |= assigned_issue_users()

        return recipients

    # ==========================================================
    # TASK
    # ==========================================================
    if subject == "task":

        if action == "creation":
            if role == "team_lead":
                recipients |= assigned_task_users()

        elif action == "status_change":
            recipients |= assigned_task_users()
            recipients |= {email}

        elif action == "comment":
            recipients |= assigned_task_users()
            recipients -= {email}

        elif action == "assigned":
            recipients |= assigned_task_users()

        return recipients

    # ==========================================================
    # LEAVE REQUEST
    # ==========================================================
    if subject == "leaverequest":

        if action in ["creation", "status_change"]:
            recipients |= team_leads(department)
            recipients |= dept_users("Non-Academic - HR")
            recipients |= team_leads("Senior Leadership Team")
            recipients |= {email}

        elif action == "comment":
            recipients |= team_leads(department)
            recipients |= dept_users("Non-Academic - HR")
            recipients |= team_leads("Senior Leadership Team")
            recipients -= {email}

        elif action == "assigned":
            recipients |= assigned_leave_users()

        return recipients

    # ==========================================================
    # FACILITY REQUEST
    # ==========================================================
    if subject == "facilityrequest":

        if action in ["creation", "status_change"]:
            recipients |= team_leads(department)
            recipients |= dept_users("facilities")
            recipients |= dept_users("Non-Academic - Accounting")
            recipients |= team_leads("Senior Leadership Team")
            recipients |= {email}

        elif action == "comment":
            recipients |= team_leads(department)
            recipients |= dept_users("facilities")
            recipients |= dept_users("Non-Academic - Accounting")
            recipients |= team_leads("Senior Leadership Team")
            recipients -= {email}

        elif action == "assigned":
            recipients |= assigned_facility_users()

        return recipients

    # ==========================================================
    # PROCUREMENT REQUEST
    # ==========================================================
    if subject == "procurementrequest":

        if action in ["creation", "status_change"]:
            recipients |= team_leads(department)
            recipients |= dept_users("Non-Academic - Procurement")
            recipients |= dept_users("Non-Academic - Accounting")
            recipients |= team_leads("Senior Leadership Team")
            recipients |= {email}

        elif action == "comment":
            recipients |= team_leads(department)
            recipients |= dept_users("Non-Academic - Procurement")
            recipients |= dept_users("Non-Academic - Accounting")
            recipients |= team_leads("Senior Leadership Team")
            recipients -= {email}

        elif action == "assigned":
            recipients |= assigned_procurement_users()

        return recipients

    # ==========================================================
    # DEFAULT FALLBACK
    # ==========================================================
    return set()