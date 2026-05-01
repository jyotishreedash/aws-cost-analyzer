import boto3
from typing import List, Dict


def get_s3_buckets(session: boto3.Session) -> List[Dict]:
    """Fetch all S3 buckets and flag empty or unversioned ones."""
    s3 = session.client("s3")
    cloudwatch = session.client("cloudwatch")

    response = s3.list_buckets()
    buckets = []

    for bucket in response.get("Buckets", []):
        name = bucket["Name"]
        size_bytes = _get_bucket_size(cloudwatch, name)

        try:
            versioning = s3.get_bucket_versioning(Bucket=name)
            versioning_status = versioning.get("Status", "Disabled")
        except Exception:
            versioning_status = "Unknown"

        try:
            lifecycle = s3.get_bucket_lifecycle_configuration(Bucket=name)
            has_lifecycle = bool(lifecycle.get("Rules"))
        except s3.exceptions.ClientError:
            has_lifecycle = False
        except Exception:
            has_lifecycle = False

        issues = []
        if size_bytes == 0:
            issues.append("Empty bucket — consider deleting")
        if versioning_status != "Enabled":
            issues.append("Versioning disabled — risk of data loss")
        if not has_lifecycle:
            issues.append("No lifecycle policy — storage costs accumulating")

        buckets.append({
            "name": name,
            "size_gb": round(size_bytes / (1024 ** 3), 3),
            "versioning": versioning_status,
            "has_lifecycle": has_lifecycle,
            "issues": issues,
            "status": "needs_attention" if issues else "healthy",
        })

    return buckets


def _get_bucket_size(cloudwatch, bucket_name: str) -> float:
    """Get the latest bucket size in bytes from CloudWatch."""
    from datetime import datetime, timedelta

    end = datetime.utcnow()
    start = end - timedelta(days=2)

    response = cloudwatch.get_metric_statistics(
        Namespace="AWS/S3",
        MetricName="BucketSizeBytes",
        Dimensions=[
            {"Name": "BucketName", "Value": bucket_name},
            {"Name": "StorageType", "Value": "StandardStorage"},
        ],
        StartTime=start,
        EndTime=end,
        Period=86400,
        Statistics=["Average"],
    )

    datapoints = response.get("Datapoints", [])
    if not datapoints:
        return 0.0
    return max(d["Average"] for d in datapoints)
