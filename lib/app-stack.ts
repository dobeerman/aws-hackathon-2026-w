import * as path from "node:path";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";

export interface TopicSignalsStackProps extends cdk.StackProps {
  readonly youtubeSecretName: string;
}

export class TopicSignalsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: TopicSignalsStackProps) {
    super(scope, id, props);

    const youtubeApiKey = secretsmanager.Secret.fromSecretNameV2(
      this,
      "YoutubeApiKey",
      props.youtubeSecretName,
    );

    const logGroup = new logs.LogGroup(this, "ApplicationLogs", {
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const handler = new lambda.Function(this, "Application", {
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      handler: "app.handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "../runtime"), {
        exclude: ["tests", "tests/**", "__pycache__", "*.pyc"],
      }),
      memorySize: 256,
      timeout: cdk.Duration.seconds(20),
      logGroup,
      environment: {
        YOUTUBE_API_KEY_SECRET_ARN: youtubeApiKey.secretArn,
      },
      description: "Serves the topic-signals UI and YouTube search API",
    });

    youtubeApiKey.grantRead(handler);

    const functionUrl = handler.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
      cors: {
        allowedOrigins: ["*"],
        allowedMethods: [lambda.HttpMethod.GET, lambda.HttpMethod.POST],
        allowedHeaders: ["content-type"],
        maxAge: cdk.Duration.hours(1),
      },
    });

    new cdk.CfnOutput(this, "ApplicationUrl", {
      value: functionUrl.url,
      description: "Public URL for the YouTube topic-signals MVP",
    });
  }
}
