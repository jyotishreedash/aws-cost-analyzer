import boto3
from datetime import datetime, timedelta
from typing import List, Dict


def get_ec2_instances(session: boto3.Session) -> List[Dict]:
    """Fetch all EC2 instances and analyze utilization."""
    ec2 = session.client("ec2")
    cloudwatch = session.client("cloudwatch")

    instances = []
    paginator = ec2.get_paginator("describe_instances")

    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for inst in reservation["Instances"]:
                if inst["State"]["Name"] == "terminated":
                    continue

                name = next(
                    (t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"),
                    inst["InstanceId"],
                )

                avg_cpu = _get_avg_cpu(cloudwatch, inst["InstanceId"])

                status = "idle" if avg_cpu < 5 else "underutilized" if avg_cpu < 20 else "active"

                instances.append({
                    "id": inst["InstanceId"],
                    "name": name,
                    "type": inst["InstanceType"],
                    "state": inst["State"]["Name"],
                    "avg_cpu_7d": round(avg_cpu, 2),
                    "status": status,
                    "launch_time": str(inst["LaunchTime"]),
                    "region": session.region_name,
                })

    return instances


def _get_avg_cpu(cloudwatch, instance_id: str) -> float:
    """Get 7-day average CPU utilization for an EC2 instance."""
    end = datetime.utcnow()
    start = end - timedelta(days=7)

    response = cloudwatch.get_metric_statistics(
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
        StartTime=start,
        EndTime=end,
        Period=86400,
        Statistics=["Average"],
    )

    datapoints = response.get("Datapoints", [])
    if not datapoints:
        return 0.0
    return sum(d["Average"] for d in datapoints) / len(datapoints)
