#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { TopicSignalsStack } from "../lib/app-stack.js";

const app = new cdk.App();

new TopicSignalsStack(app, "YoutubeTopicSignalsStack", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? "eu-central-1",
  },
  youtubeSecretName:
    app.node.tryGetContext("youtubeSecretName") ??
    "youtube-trend-signals/youtube-api-key",
  description:
    "YouTube emerging topic signals MVP for the AWS Builder Center Zero to Shipped hackathon",
});
