from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class FundingApplication:
    project_id: str
    title: str
    requested_gbp: float
    target_people: int
    underserved_weight: float
    evidence_strength: float
    counterfactual_need: float
    milestone_clarity: float
    verification_strength: float
    open_source_reuse: float
    delivery_risk: float
    summary: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FundingApplication":
        return cls(
            project_id=str(data["project_id"]),
            title=str(data["title"]),
            requested_gbp=float(data["requested_gbp"]),
            target_people=int(data["target_people"]),
            underserved_weight=float(data["underserved_weight"]),
            evidence_strength=float(data["evidence_strength"]),
            counterfactual_need=float(data["counterfactual_need"]),
            milestone_clarity=float(data["milestone_clarity"]),
            verification_strength=float(data["verification_strength"]),
            open_source_reuse=float(data["open_source_reuse"]),
            delivery_risk=float(data["delivery_risk"]),
            summary=str(data["summary"]),
        )


def score_application(app: FundingApplication) -> dict[str, Any]:
    reach = min(app.target_people / 5000.0, 1.0)
    equity_adjusted_reach = reach * (0.55 + 0.45 * clamp(app.underserved_weight))
    cost_efficiency = min((app.target_people / max(app.requested_gbp, 1.0)) / 4.0, 1.0)

    impact = 0.45 * equity_adjusted_reach + 0.3 * app.evidence_strength + 0.25 * cost_efficiency
    accountability = 0.5 * app.milestone_clarity + 0.35 * app.verification_strength + 0.15 * app.open_source_reuse
    counterfactual = app.counterfactual_need
    risk_adjustment = 1.0 - 0.45 * clamp(app.delivery_risk)

    raw_score = (0.42 * impact + 0.22 * counterfactual + 0.24 * accountability + 0.12 * app.open_source_reuse)
    final_score = raw_score * risk_adjustment

    return {
        "projectId": app.project_id,
        "title": app.title,
        "requestedGbp": app.requested_gbp,
        "score": round(final_score, 4),
        "metrics": {
            "impact": round(impact, 4),
            "counterfactualNeed": round(counterfactual, 4),
            "milestoneQuality": round(app.milestone_clarity, 4),
            "verificationStrength": round(app.verification_strength, 4),
            "openSourceReuse": round(app.open_source_reuse, 4),
            "deliveryRisk": round(app.delivery_risk, 4),
            "costEfficiency": round(cost_efficiency, 4),
        },
        "reasoning": [
            f"Estimated reach: {app.target_people} people with underserved weight {app.underserved_weight:.2f}.",
            f"Counterfactual need is {app.counterfactual_need:.2f}; lower scores mean the work likely happens without GCC.",
            f"Milestone and verification quality are {app.milestone_clarity:.2f} and {app.verification_strength:.2f}.",
            f"Risk adjustment applied from delivery risk {app.delivery_risk:.2f}.",
        ],
    }


def allocate_funding(applications: list[FundingApplication], budget_gbp: float) -> dict[str, Any]:
    ranked = sorted((score_application(app) for app in applications), key=lambda item: item["score"], reverse=True)
    remaining = budget_gbp
    allocations: list[dict[str, Any]] = []

    for item in ranked:
        requested = float(item["requestedGbp"])
        if item["score"] < 0.35:
            allocations.append({**item, "recommendedGbp": 0, "decision": "decline", "decisionReason": "Score below funding threshold."})
            continue
        if remaining <= 0:
            allocations.append({**item, "recommendedGbp": 0, "decision": "waitlist", "decisionReason": "Budget exhausted."})
            continue
        recommended = min(requested, remaining)
        remaining -= recommended
        decision = "fund" if recommended == requested else "partial"
        allocations.append({
            **item,
            "recommendedGbp": round(recommended, 2),
            "decision": decision,
            "decisionReason": "High transparent-impact score within available budget.",
        })

    return {
        "program": "GCC public funding allocation",
        "budgetGbp": budget_gbp,
        "allocatedGbp": round(budget_gbp - remaining, 2),
        "remainingGbp": round(remaining, 2),
        "rubric": {
            "impact": "Reach, evidence, equity-adjusted need, and cost efficiency.",
            "counterfactual": "Whether funding changes what happens versus the likely baseline.",
            "milestones": "Whether outputs can be verified without trusting a chat response.",
            "reuse": "Whether components are portable for other public-good grant programs.",
            "risk": "Delivery risk reduces, but does not fully dominate, the score.",
        },
        "allocations": allocations,
    }


def load_applications(path: Path) -> list[FundingApplication]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("funding applications file must be a JSON array")
    return [FundingApplication.from_dict(item) for item in raw]


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def main() -> None:
    parser = argparse.ArgumentParser(description="GCC public funding allocation agent")
    parser.add_argument("--applications", default="data/gcc/applications.json")
    parser.add_argument("--budget-gbp", type=float, default=12000)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    result = allocate_funding(load_applications(Path(args.applications)), args.budget_gbp)
    text = json.dumps(result, indent=2)
    if args.out:
      Path(args.out).parent.mkdir(parents=True, exist_ok=True)
      Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
