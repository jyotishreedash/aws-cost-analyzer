import boto3
from datetime import datetime, timedelta
from typing import List, Dict


def get_rds_instances(session: boto3.Session) -> List[Dict]:
    """Fetch RDS instances and check for idle or oversized ones."""
    rds = session.client("rds")
    cloudwatch = session.client("cloudwatch")

    response = rds.describe_db_instances()
    instances = []

    for db in response.get("DBInstances", []):
        identifier = db["DBInstanceIdentifier"]
        avg_connections = _get_avg_connections(cloudwatch, identifier)
        avg_cpu = _get_avg_cpu(cloudwatch, identifier)

        issues = []
        if avg_connections < 1:
            issues.append("Zero connections in 7 days — possible zombie instance")
        if avg_cpu < 5 and avg_connections < 5:
            issues.append("Very low CPU & connections — consider downsizing")
        if db.get("MultiAZ") and avg_connections < 5:
            issues.append("Multi-AZ enabled with minimal usage — costly for idle DB")

        instances.append({
            "id": identifier,
            "engine": f"{db['Engine']} {db['EngineVersion']}",
            "class": db["DBInstanceClass"],
            "status": db["DBInstanceStatus"],
            "multi_az": db.get("MultiAZ", False),
            "avg_cpu_7d": round(avg_cpu, 2),
            "avg_connections_7d": round(avg_connections, 2),
            "issues": issues,
            "health": "needs_attention" if issues else "healthy",
        })

    return instances


def _get_avg_connections(cloudwatch, db_id: str) -> float:
    end = datetime.utcnow()
    start = end - timedelta(days=7)
    response = cloudwatch.get_metric_statistics(
        Namespace="AWS/RDS",
        MetricName="DatabaseConnections",
        Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_id}],
        StartTime=start, EndTime=end, Period=86400, Statistics=["Average"],
    )
    dp = response.get("Datapoints", [])
    return sum(d["Average"] for d in dp) / len(dp) if dp else 0.0


def _get_avg_cpu(cloudwatch, db_id: str) -> float:
    end = datetime.utcnow()
    start = end - timedelta(days=7)
    response = cloudwatch.get_metric_statistics(
        Namespace="AWS/RDS",
        MetricName="CPUUtilization",
        Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_id}],
        StartTime=start, EndTime=end, Period=86400, Statistics=["Average"],
    )
    dp = response.get("Datapoints", [])
    return sum(d["Average"] for d in dp) / len(dp) if dp else 0.0
