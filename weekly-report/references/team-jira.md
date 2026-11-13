# Team Jira: how to pull the week's tickets

The script cannot call MCP tools, so the model runs the search with the Atlassian connector
and hands the saved pages to `collect.py --jira`. Every rule below comes from a live run on
2026-11-13 (215 issues).

## The query

```text
project = <jira_project> AND (resolved >= "<mon-1>" AND resolved < "<fri+2>"
  OR created >= "<mon-1>" AND created < "<fri+2>") ORDER BY updated DESC
```

`fields`: summary, status, issuetype, created, resolutiondate, assignee.

The span is one day wider on each side on purpose. JQL runs in the Jira profile's time
zone, and the collector trims to Chicago Mon-Fri. A date-only `<= <fri>` would drop Friday.

## Paging: even pages, so each page is saved to a file

1. Run the query once with `searchResultMode` `count`. Only this call, or the first page,
   carries `totalCount`.
2. `pages = ceil(total / 100)`, then `maxResults = max(50, ceil(total / pages))`.
3. Page with `nextPageToken` until `hasNextPage` is false.
4. Pass every saved file to `--jira`, one flag per file.

Why even: each row is about 2 KB, mostly URLs. A page of 71 or more rows is too big to
return inline, so the host saves it to a file and names the path. A short page comes back
inline (15 rows, seen live), and the script cannot read it. With 100-row pages, 215 issues
gave 100 + 100 + 15 and lost the last page. With even pages, 72 + 72 + 71, all were saved.

A small week can still come back inline as one page. The cut-off between 15 and 71 rows is
not measured. Save an inline page verbatim with Write, then pass that file. Never retype or
trim it. A page you skip shows as `jira: N issues missing` in the facts, and then the bulk
flags are not reliable.
