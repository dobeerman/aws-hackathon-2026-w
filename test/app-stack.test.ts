import assert from "node:assert/strict";
import test from "node:test";
import * as cdk from "aws-cdk-lib";
import { Match, Template } from "aws-cdk-lib/assertions";
import { TopicSignalsStack } from "../lib/app-stack.js";

function template(): Template {
  const app = new cdk.App();
  const stack = new TopicSignalsStack(app, "TestStack", {
    youtubeSecretName: "test/youtube-key",
  });
  return Template.fromStack(stack);
}

test("creates exactly one public Lambda with bounded runtime settings", () => {
  const output = template();

  output.resourceCountIs("AWS::Lambda::Function", 1);
  output.hasResourceProperties("AWS::Lambda::Function", {
    Architectures: ["arm64"],
    Runtime: "python3.12",
    Handler: "app.handler",
    MemorySize: 256,
    Timeout: 20,
    Environment: {
      Variables: {
        YOUTUBE_API_KEY_SECRET_ARN: Match.anyValue(),
      },
    },
  });
  output.hasResourceProperties("AWS::Lambda::Url", {
    AuthType: "NONE",
    Cors: Match.objectLike({ AllowOrigins: ["*"] }),
  });
});

test("grants only secret read and basic log permissions", () => {
  const rendered = template().toJSON();
  const policies = Object.values(rendered.Resources).filter(
    (resource: any) => resource.Type === "AWS::IAM::Policy",
  ) as any[];

  assert.equal(policies.length, 1);
  const statements = policies[0].Properties.PolicyDocument.Statement;
  assert.ok(
    statements.some(
      (statement: any) =>
        statement.Effect === "Allow" &&
        JSON.stringify(statement.Action).includes(
          "secretsmanager:GetSecretValue",
        ),
    ),
  );
  assert.equal(
    JSON.stringify(rendered).includes("YOUR_KEY"),
    false,
    "template must not contain a YouTube API key",
  );
});

test("sets an explicit one-week log retention policy", () => {
  template().hasResourceProperties("AWS::Logs::LogGroup", {
    RetentionInDays: 7,
  });
});
