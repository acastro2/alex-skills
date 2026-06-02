# Microsoft 365 Copilot Prompt

Copy and paste this prompt into Microsoft 365 Copilot Chat to gather collaboration data for the performance report.

---

I need a comprehensive 6-month activity summary for {{PERSON_NAME}} ({{EMAIL}}) from {{PERIOD_START_LABEL}} through {{PERIOD_END_LABEL}}. Show me:

1. **Documents**: All documents they created or modified in SharePoint and OneDrive (include document name, type, co-authors, and date)
2. **Meetings**: Meetings they organized vs meetings they attended as an invitee. List any recurring meeting series they run.
3. **Teams channels**: Which Teams channels they are most active in, with approximate activity level (high/medium/low)
4. **Email**: Any notable email threads they initiated or were a key participant in
5. **Collaborators**: Who they collaborate with most frequently across email, Teams, and shared documents

Focus on evidence of cross-team leadership, technical decision-making artifacts (design docs, RFCs, architecture proposals), and meeting facilitation.

---

**Note:** Results from M365 Copilot are scoped to the requester's permissions. Data may not include private channels, restricted SharePoint sites, or conversations outside your visibility. Include this caveat when adding M365 data to the report.
