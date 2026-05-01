from datetime import datetime
from typing import Dict
import json


def generate_html_report(data: Dict, output_path: str = "reports/cost_report.html"):
    """Generate a beautiful HTML cost optimization report."""

    ec2 = data.get("ec2", [])
    s3 = data.get("s3", [])
    rds = data.get("rds", [])
    costs = data.get("costs", {})

    idle_ec2 = [i for i in ec2 if i["status"] == "idle"]
    underutilized_ec2 = [i for i in ec2 if i["status"] == "underutilized"]
    s3_issues = [b for b in s3 if b["status"] == "needs_attention"]
    rds_issues = [r for r in rds if r["health"] == "needs_attention"]

    total_issues = len(idle_ec2) + len(underutilized_ec2) + len(s3_issues) + len(rds_issues)
    health_score = max(0, 100 - (total_issues * 10))

    change_color = "#ef4444" if costs.get("change_pct", 0) > 0 else "#22c55e"
    change_arrow = "↑" if costs.get("change_pct", 0) > 0 else "↓"

    ec2_rows = ""
    for inst in ec2:
        status_class = {"idle": "badge-red", "underutilized": "badge-yellow", "active": "badge-green"}.get(inst["status"], "badge-gray")
        ec2_rows += f"""
        <tr>
            <td><code>{inst['id']}</code></td>
            <td>{inst['name']}</td>
            <td>{inst['type']}</td>
            <td>{inst['state']}</td>
            <td>{inst['avg_cpu_7d']}%</td>
            <td><span class="badge {status_class}">{inst['status']}</span></td>
        </tr>"""

    s3_rows = ""
    for bucket in s3:
        issues_html = "".join(f'<li>{i}</li>' for i in bucket["issues"]) if bucket["issues"] else "<li>None</li>"
        status_class = "badge-red" if bucket["status"] == "needs_attention" else "badge-green"
        s3_rows += f"""
        <tr>
            <td>{bucket['name']}</td>
            <td>{bucket['size_gb']} GB</td>
            <td>{bucket['versioning']}</td>
            <td>{'Yes' if bucket['has_lifecycle'] else 'No'}</td>
            <td><span class="badge {status_class}">{bucket['status']}</span></td>
            <td><ul class="issues-list">{issues_html}</ul></td>
        </tr>"""

    rds_rows = ""
    for db in rds:
        issues_html = "".join(f'<li>{i}</li>' for i in db["issues"]) if db["issues"] else "<li>None</li>"
        health_class = "badge-red" if db["health"] == "needs_attention" else "badge-green"
        rds_rows += f"""
        <tr>
            <td>{db['id']}</td>
            <td>{db['engine']}</td>
            <td>{db['class']}</td>
            <td>{db['avg_cpu_7d']}%</td>
            <td>{db['avg_connections_7d']}</td>
            <td><span class="badge {health_class}">{db['health']}</span></td>
            <td><ul class="issues-list">{issues_html}</ul></td>
        </tr>"""

    service_bars = ""
    services = costs.get("by_service", [])
    max_cost = max((s["cost_usd"] for s in services), default=1)
    for svc in services:
        width = int((svc["cost_usd"] / max_cost) * 100)
        service_bars += f"""
        <div class="service-row">
            <span class="service-name">{svc['service']}</span>
            <div class="bar-wrap"><div class="bar" style="width:{width}%"></div></div>
            <span class="service-cost">${svc['cost_usd']}</span>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AWS Cost Analyzer Report</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

  :root {{
    --bg: #0a0e1a;
    --surface: #111827;
    --surface2: #1a2235;
    --border: #1e2d45;
    --accent: #00d4ff;
    --accent2: #7c3aed;
    --green: #22c55e;
    --yellow: #f59e0b;
    --red: #ef4444;
    --text: #e2e8f0;
    --muted: #64748b;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'IBM Plex Sans', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 2rem;
  }}

  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 2.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
  }}

  .header h1 {{
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--accent);
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: -0.5px;
  }}

  .header p {{ color: var(--muted); font-size: 0.85rem; margin-top: 0.3rem; }}

  .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem; }}

  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.4rem;
  }}

  .stat-card {{ position: relative; overflow: hidden; }}
  .stat-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
  }}

  .stat-label {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem; }}
  .stat-value {{ font-size: 2rem; font-weight: 700; font-family: 'IBM Plex Mono', monospace; color: var(--accent); }}
  .stat-sub {{ font-size: 0.8rem; color: var(--muted); margin-top: 0.3rem; }}

  .section-title {{
    font-size: 1rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-family: 'IBM Plex Mono', monospace;
  }}

  .section-title .dot {{
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--accent);
  }}

  table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  th {{ text-align: left; color: var(--muted); font-weight: 600; padding: 0.6rem 0.8rem; border-bottom: 1px solid var(--border); text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.5px; }}
  td {{ padding: 0.7rem 0.8rem; border-bottom: 1px solid var(--border); color: var(--text); }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: var(--surface2); }}

  code {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; color: var(--accent); }}

  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
  .badge-green {{ background: rgba(34,197,94,0.15); color: var(--green); }}
  .badge-yellow {{ background: rgba(245,158,11,0.15); color: var(--yellow); }}
  .badge-red {{ background: rgba(239,68,68,0.15); color: var(--red); }}
  .badge-gray {{ background: rgba(100,116,139,0.15); color: var(--muted); }}

  .issues-list {{ list-style: none; padding: 0; }}
  .issues-list li {{ font-size: 0.75rem; color: var(--yellow); margin-bottom: 2px; }}
  .issues-list li::before {{ content: '⚠ '; }}

  .health-ring {{
    width: 90px; height: 90px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem; font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
    background: conic-gradient(var(--green) {health_score}%, var(--border) 0);
    position: relative;
  }}

  .health-ring-inner {{
    width: 68px; height: 68px;
    border-radius: 50%;
    background: var(--surface);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem;
    color: var(--green);
  }}

  .service-row {{ display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.7rem; }}
  .service-name {{ width: 180px; font-size: 0.78rem; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; }}
  .bar-wrap {{ flex: 1; background: var(--border); border-radius: 4px; height: 8px; }}
  .bar {{ height: 8px; border-radius: 4px; background: linear-gradient(90deg, var(--accent), var(--accent2)); }}
  .service-cost {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; color: var(--text); width: 70px; text-align: right; }}

  .summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }}
  .summary-item {{ text-align: center; padding: 1rem; background: var(--surface2); border-radius: 8px; border: 1px solid var(--border); }}
  .summary-num {{ font-size: 1.8rem; font-weight: 700; font-family: 'IBM Plex Mono', monospace; }}
  .summary-label {{ font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }}
  .num-red {{ color: var(--red); }}
  .num-yellow {{ color: var(--yellow); }}
  .num-green {{ color: var(--green); }}

  .footer {{ text-align: center; color: var(--muted); font-size: 0.75rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border); }}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>⚡ AWS Cost Analyzer</h1>
    <p>Generated on {datetime.now().strftime("%B %d, %Y at %H:%M UTC")} · Period: {costs.get('period', 'N/A')}</p>
  </div>
  <div style="display:flex; align-items:center; gap:1.2rem;">
    <div>
      <div class="stat-label">Health Score</div>
      <div class="health-ring"><div class="health-ring-inner">{health_score}</div></div>
    </div>
  </div>
</div>

<!-- Top Stats -->
<div class="grid-4">
  <div class="card stat-card">
    <div class="stat-label">Total Spend (30d)</div>
    <div class="stat-value">${costs.get('total_cost_usd', 0)}</div>
    <div class="stat-sub" style="color:{change_color}">{change_arrow} {abs(costs.get('change_pct', 0))}% vs last month</div>
  </div>
  <div class="card stat-card">
    <div class="stat-label">EC2 Instances</div>
    <div class="stat-value">{len(ec2)}</div>
    <div class="stat-sub">{len(idle_ec2)} idle · {len(underutilized_ec2)} underutilized</div>
  </div>
  <div class="card stat-card">
    <div class="stat-label">S3 Buckets</div>
    <div class="stat-value">{len(s3)}</div>
    <div class="stat-sub">{len(s3_issues)} need attention</div>
  </div>
  <div class="card stat-card">
    <div class="stat-label">RDS Instances</div>
    <div class="stat-value">{len(rds)}</div>
    <div class="stat-sub">{len(rds_issues)} need attention</div>
  </div>
</div>

<!-- Issue Summary -->
<div class="card" style="margin-bottom:2rem;">
  <div class="section-title"><span class="dot"></span>Issue Summary</div>
  <div class="summary-grid">
    <div class="summary-item">
      <div class="summary-num num-red">{len(idle_ec2)}</div>
      <div class="summary-label">Idle EC2 Instances</div>
    </div>
    <div class="summary-item">
      <div class="summary-num num-yellow">{len(underutilized_ec2)}</div>
      <div class="summary-label">Underutilized EC2</div>
    </div>
    <div class="summary-item">
      <div class="summary-num num-yellow">{len(s3_issues) + len(rds_issues)}</div>
      <div class="summary-label">S3 + RDS Issues</div>
    </div>
  </div>
</div>

<!-- Cost by Service + EC2 -->
<div class="grid-2">
  <div class="card">
    <div class="section-title"><span class="dot"></span>Cost by Service (Top 10)</div>
    {service_bars if service_bars else '<p style="color:var(--muted);font-size:0.85rem;">No cost data available</p>'}
  </div>
  <div class="card">
    <div class="section-title"><span class="dot"></span>EC2 Instances</div>
    <div style="overflow-x:auto;">
      <table>
        <thead><tr><th>ID</th><th>Name</th><th>Type</th><th>State</th><th>Avg CPU</th><th>Status</th></tr></thead>
        <tbody>{ec2_rows if ec2_rows else '<tr><td colspan="6" style="color:var(--muted);text-align:center;">No instances found</td></tr>'}</tbody>
      </table>
    </div>
  </div>
</div>

<!-- S3 -->
<div class="card" style="margin-bottom:2rem;">
  <div class="section-title"><span class="dot"></span>S3 Buckets</div>
  <div style="overflow-x:auto;">
    <table>
      <thead><tr><th>Bucket</th><th>Size</th><th>Versioning</th><th>Lifecycle</th><th>Status</th><th>Issues</th></tr></thead>
      <tbody>{s3_rows if s3_rows else '<tr><td colspan="6" style="color:var(--muted);text-align:center;">No buckets found</td></tr>'}</tbody>
    </table>
  </div>
</div>

<!-- RDS -->
<div class="card" style="margin-bottom:2rem;">
  <div class="section-title"><span class="dot"></span>RDS Instances</div>
  <div style="overflow-x:auto;">
    <table>
      <thead><tr><th>ID</th><th>Engine</th><th>Class</th><th>Avg CPU</th><th>Avg Connections</th><th>Health</th><th>Issues</th></tr></thead>
      <tbody>{rds_rows if rds_rows else '<tr><td colspan="7" style="color:var(--muted);text-align:center;">No RDS instances found</td></tr>'}</tbody>
    </table>
  </div>
</div>

<div class="footer">Generated by aws-cost-analyzer · github.com/jyotishreedash/aws-cost-analyzer</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
