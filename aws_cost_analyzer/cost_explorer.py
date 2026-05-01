import boto3
from datetime import datetime, timedelta
from typing import Dict, List


def get_cost_summary(session: boto3.Session) -> Dict:
    """Fetch cost data for the last 30 days broken down by service."""
    ce = session.client("ce", region_name="us-east-1")

    end = datetime.utcnow().date()
    start = end - timedelta(days=30)

    response = ce.get_cost_and_usage(
        TimePeriod={"Start": str(start), "End": str(end)},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    service_costs = []
    total = 0.0

    for result in response.get("ResultsByTime", []):
        for group in result.get("Groups", []):
            service = group["Keys"][0]
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            if amount > 0.01:
                service_costs.append({"service": service, "cost_usd": round(amount, 2)})
                total += amount

    service_costs.sort(key=lambda x: x["cost_usd"], reverse=True)

    # Get previous month for comparison
    prev_end = start
    prev_start = prev_end - timedelta(days=30)

    prev_response = ce.get_cost_and_usage(
        TimePeriod={"Start": str(prev_start), "End": str(prev_end)},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
    )

    prev_total = 0.0
    for result in prev_response.get("ResultsByTime", []):
        for metric in result.get("Total", {}).values():
            prev_total += float(metric.get("Amount", 0))

    change_pct = 0.0
    if prev_total > 0:
        change_pct = round(((total - prev_total) / prev_total) * 100, 1)

    return {
        "total_cost_usd": round(total, 2),
        "prev_month_cost_usd": round(prev_total, 2),
        "change_pct": change_pct,
        "period": f"{start} to {end}",
        "by_service": service_costs[:10],  # Top 10 services
    }


def get_savings_recommendations(session: boto3.Session) -> List[Dict]:
    """Fetch AWS Cost Explorer savings recommendations."""
    ce = session.client("ce", region_name="us-east-1")
    recommendations = []

    try:
        response = ce.get_recommendations(
            Service="EC2",
            RecommendationTarget="CROSS_INSTANCE_FAMILY",
            BenefitsConsidered={
                "IncludeUpfrontCost": False,
            },
        )
        for r in response.get("Recommendations", []):
            recommendations.append({
                "type": "Reserved Instance",
                "description": r.get("InstanceDetails", {}).get("EC2InstanceDetails", {}).get("Family", ""),
                "estimated_savings": r.get("EstimatedMonthlySavings", {}).get("Value", "N/A"),
            })
    except Exception:
        pass  # Recommendations may not be available in all accounts

    return recommendations
