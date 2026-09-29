# YouTube Emerging Topic Signals

Small, public MVP for the AWS Builder Center **Zero to Shipped** hackathon.

A creator enters a topic and a recent time window. The app searches the official
YouTube Data API for relevant, recently published short-duration videos, fetches
their real metadata and available statistics, and groups those videos into a few
explainable themes.

This release supports **YouTube only**. TikTok and Instagram are possible future
sources and are not supported or represented as supported in the UI.

## Live deployment

- URL: <https://tzaf24aswwdzm2blkpfyajsw240faavh.lambda-url.eu-central-1.on.aws/>
- CloudFormation stack: `YoutubeTopicSignalsStack`
- AWS Region: `eu-central-1`

## Product contract

- The default search window is seven days; supported windows are 1, 3, 7, 14,
  and 30 days.
- Every displayed video comes from the live YouTube API response. Fixture data is
  used only in automated tests and is never shown as live data.
- Each result includes its YouTube URL, publication time, available view count,
  and the UTC time at which the API data was fetched.
- Results are described as signals from the submitted search, not a definitive
  ranking of YouTube-wide trends.
- YouTube's `videoDuration=short` search filter means a short-duration video; it
  is not an exact classification of the YouTube Shorts product.
- Queries are limited to 100 characters and one search returns at most 25 videos.
  A request uses two YouTube Data API calls: `search.list` and `videos.list`.

## Architecture

```text
Browser
  |  GET / and POST /api/search
  v
Public Lambda Function URL
  |-- embedded static HTML/CSS/JS UI
  |-- Python request validation and deterministic theme grouping
  |-- YouTube Data API v3 (search.list, videos.list)
  `-- existing Secrets Manager secret (YouTube API key)
```

AWS CDK in TypeScript defines one Python Lambda and its public Function URL. The
stack references an **existing** Secrets Manager secret and grants the function
permission to read only that secret. The API key is never passed as a CDK context
value, Lambda environment value, or CloudFormation plaintext value.

No database, queue, user account, scheduler, crawler, API Gateway, Bedrock model,
or multi-agent system is used. Deterministic grouping is intentional: specific
words and 2–3 word phrases repeated in at least two retrieved titles form candidate
themes. Generic promotional/editing vocabulary is excluded, multiword phrases and
cross-channel support are preferred, and unmatched videos stay in an honestly
labeled remainder group. This makes the result reproducible and lets the UI explain
exactly why a theme appeared.

## Repository layout

```text
bin/app.ts                 CDK application entry point
lib/app-stack.ts           Lambda, Function URL, secret access, and logs
runtime/app.py             Lambda handler and routing
runtime/youtube.py         YouTube API client and error mapping
runtime/grouping.py        Deterministic theme grouping
runtime/index.html         Single-page web UI
runtime/dev_server.py      Local HTTP server using the same handler
runtime/tests/             Python unit tests
test/                      CDK assertions
```

## Prerequisites

- Node.js 22 or later and npm
- Python 3.12 or later
- AWS CDK v2 (provided as a local npm dependency)
- An AWS identity able to synthesize/deploy CDK and read/create the configured
  secret
- A YouTube Data API v3 key with the YouTube Data API enabled in its Google Cloud
  project

## Secure YouTube API key configuration

For local development, provide the key only in the process environment:

```bash
read -s YOUTUBE_API_KEY
export YOUTUBE_API_KEY
```

Do not put the key in `.env`, CDK context, source files, or shell history.

Before a future deployment, create an AWS Secrets Manager secret named
`youtube-trend-signals/youtube-api-key` in `eu-central-1`. Store either the raw
key as the secret string or JSON in this form:

```json
{ "apiKey": "YOUR_KEY" }
```

The safest setup path is the AWS Console's Secrets Manager secret-value field,
which avoids placing the value in a command or CloudFormation template. A
different existing secret name can be selected with the CDK context option shown
below.

## Local development

Run these commands from the repository root:

```bash
npm install
npm run format:check
npm run lint
npm run typecheck
npm test
YOUTUBE_API_KEY="$YOUTUBE_API_KEY" python3 runtime/dev_server.py
```

Open <http://127.0.0.1:8080>. Live searches require the local environment key;
the UI itself loads without one and returns a useful configuration error when a
search is attempted.

## Validate and synthesize

These commands do not deploy resources:

```bash
npm run format:check
npm run lint
npm run typecheck
npm test
npm run synth
```

The synthesized template is written to `cdk.out/`, which is ignored by Git.

## Deployment commands

For a reviewed update, run these only after the existing secret is present:

```bash
export CDK_DEFAULT_ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
export CDK_DEFAULT_REGION=eu-central-1
npx cdk bootstrap "aws://${CDK_DEFAULT_ACCOUNT}/${CDK_DEFAULT_REGION}"
npx cdk diff --context youtubeSecretName=youtube-trend-signals/youtube-api-key
npx cdk deploy --context youtubeSecretName=youtube-trend-signals/youtube-api-key
```

Bootstrap is required only if the target account/Region has not already been
bootstrapped. `cdk diff` must be reviewed before deployment.

## API

`POST /api/search`

```json
{ "topic": "serverless video editing", "days": 7 }
```

Successful responses include `query`, `windowDays`, `fetchedAt`, `resultCount`,
`themes`, and a plain-language `methodology`. Errors use an appropriate HTTP
status and an `error` object with a stable `code` and useful `message`.

## Failure handling

- Missing local key or unreadable deployment secret: `503 configuration_error`
- No matching videos: successful empty result with suggestions to broaden the
  topic or time window
- YouTube quota exhaustion: `429 quota_exceeded`
- Other YouTube authorization/API failures: `502 youtube_api_error`
- YouTube timeout or network failure: `502 youtube_unavailable`
- Invalid topic/window/body: `400 validation_error`

## Limitations

- Signals cover only the returned videos for one YouTube search, not all YouTube
  activity and not platform-wide trend rankings.
- View counts are cumulative snapshots when available. The app has no historical
  store and therefore does not calculate growth or velocity.
- Theme labels are lexical title clusters. They are transparent and inexpensive,
  but exact wording differences can prevent semantically related titles from
  clustering together.
- YouTube may omit or hide statistics, and the UI labels unavailable values.
- Search relevance, availability, regional behavior, and quota enforcement are
  controlled by YouTube.
- The public Function URL has no user accounts. Input limits and two-call search
  design constrain accidental usage, but production abuse protection would need
  an additional edge or authentication layer outside this MVP's scope.
