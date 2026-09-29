# Builder Center submission draft — Signal Lens

Status: **draft; do not publish until the evidence and final live check are complete.**

## Project title

Signal Lens — topic signals from real YouTube videos

## Short description

Find a useful next video angle. Enter a topic and a recent time window; Signal Lens groups real short-duration YouTube videos into specific, explainable themes, with source links, publication times, view counts, and a fetch timestamp.

## Category and lane

- Category: `#commercial-potential`
- Lane: `#startups`

This is an early creator research product. The first release validates a narrow workflow before adding more sources or historical trend measurement.

## Project story

Creators need to see what people are making around a subject now, but a list of popular videos alone does not explain which concrete ideas recur. Signal Lens turns a live YouTube search into a small set of evidence-backed topic signals. A creator can enter a subject such as “AI video editing,” choose a recent window, inspect the recurring phrases, and open every supporting video.

The application retrieves up to 25 relevant, recently published short-duration videos through the official YouTube Data API. A deterministic grouping method favors specific repeated phrases and support from different channels. Each result shows the source videos and why the group was formed. Unmatched videos remain visible under “Other relevant signals.”

The app deliberately calls these **signals from the search**. It has no historical snapshots and does not claim measured growth or a platform-wide trend ranking. YouTube's short-duration filter is also not an exact classification of YouTube Shorts. This release supports YouTube only; TikTok and Instagram remain possible future sources.

## How the coding agent helped ship

Codex was connected to AWS through the AWS MCP Server. An authenticated STS GetCallerIdentity call verified access to the intended AWS environment in Frankfurt (`eu-central-1`). Codex implemented the UI, YouTube integration, grouping logic, tests, and AWS CDK infrastructure. It synthesized and reviewed the stack, deployed it, verified the public URL with live API results, then refined the grouping after a live test showed generic labels such as “Trending” and “Edit.” The revised live result produced specific labels such as “Hotel Lobby Song,” “Pata Chalega Song,” “Car Driving,” and “Car Jump.”

Attach a screenshot of the Codex AWS MCP tool invocation and response. Add a second screenshot showing the live application results. Redact credentials; the YouTube API key must not appear in the entry.

## Technical implementation

- AWS CDK (TypeScript) deploys one Python Lambda and a public Lambda Function URL in `eu-central-1`.
- The Lambda serves the static UI and `POST /api/search`, validates input, and calls YouTube Data API `search.list` and `videos.list`.
- The YouTube API key is held in AWS Secrets Manager. The Lambda role can read only the named secret.
- The grouping is deterministic and testable; no Bedrock model, database, queue, scheduled crawler, or account system is required for this MVP.
- Source code and deployment instructions: https://github.com/dobeerman/aws-hackathon-2026-w
- Live application: https://tzaf24aswwdzm2blkpfyajsw240faavh.lambda-url.eu-central-1.on.aws/

## Demo steps

1. Open the live application without signing in.
2. Search for `AI video editing` with the default seven-day window.
3. Inspect the specific themes, the number of supporting videos and channels, and the methodology.
4. Open a supporting YouTube link and compare its title, publication date, and views with the displayed source card.
5. Try a different subject or time window to see a fresh result and fetch timestamp.

## Verification already reported

- Stack `YoutubeTopicSignalsStack`: `UPDATE_COMPLETE`.
- Live search on September 29, 2026: 25 real videos; all returned links were unique YouTube watch URLs.
- 3 infrastructure tests, 17 backend tests, formatting, lint, TypeScript checking, and CDK synth passed.
- The public UI was independently opened in a browser without AWS authentication, and a live search returned source cards.

## Before publishing

- [ ] Attach a readable screenshot of the authenticated AWS MCP call in Codex, with credentials hidden.
- [ ] Attach a live result screenshot (specific themes and source videos visible).
- [ ] Confirm the public URL still works in a fresh browser session.
- [ ] Ensure category and lane tags are present on the Builder Center project.
- [ ] Check the Builder Center preview and submit before October 2, 2026, 11:59 PM PDT.
