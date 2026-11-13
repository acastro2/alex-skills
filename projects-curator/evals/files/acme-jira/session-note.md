Earlier in this session, after Alex approved them, the curator made these Jira writes and each
call returned success:
- created ACME-81, ACME-82 and ACME-83 with parent ACME-80
- moved ACME-77 under parent ACME-80

Right after the writes, it ran the JQL `parent = ACME-80`. The result is in search.json.
