TechNews Publisher implementation notes

Storage model
- DB stores issue metadata for listing, future editing, publish flags, and eventual auth/audit history.
- Markdown files store the rendered body source in backend/content/YYYY/MM/*.md.
- This split keeps future editing/versioning flexible without forcing rich-text into DB.

Recommended future cron flow
1. Existing GeekNews cron still sends Telegram summary.
2. After composing the final summary, call a local ingestion endpoint on this app.
3. Ingestion endpoint writes markdown file + upserts issue row.
4. Public web page at /technews renders the stored issue.

Suggested future additions
- Admin-only ingestion/auth later
- search by keyword
- tags (AI, infra, devtools, security)
- original source domain badges
- RSS/Atom feed
- shareable permalink per issue
- draft/published states
- manual pinning or editor note section
