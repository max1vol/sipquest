from agents.gcc_public_funding_agent import FundingApplication, allocate_funding, score_application


def test_gcc_scoring_rewards_counterfactual_and_verification():
    strong = FundingApplication(
        project_id="strong",
        title="Strong public good",
        requested_gbp=1000,
        target_people=1000,
        underserved_weight=0.9,
        evidence_strength=0.8,
        counterfactual_need=0.9,
        milestone_clarity=0.9,
        verification_strength=0.9,
        open_source_reuse=0.9,
        delivery_risk=0.1,
        summary="High public value.",
    )
    weak = FundingApplication(
        project_id="weak",
        title="Weak public good",
        requested_gbp=1000,
        target_people=1000,
        underserved_weight=0.2,
        evidence_strength=0.4,
        counterfactual_need=0.2,
        milestone_clarity=0.4,
        verification_strength=0.3,
        open_source_reuse=0.2,
        delivery_risk=0.4,
        summary="Mostly commercial.",
    )

    assert score_application(strong)["score"] > score_application(weak)["score"]


def test_gcc_allocator_respects_budget():
    applications = [
        FundingApplication(
            project_id="a",
            title="A",
            requested_gbp=4000,
            target_people=2000,
            underserved_weight=0.9,
            evidence_strength=0.8,
            counterfactual_need=0.9,
            milestone_clarity=0.9,
            verification_strength=0.9,
            open_source_reuse=0.8,
            delivery_risk=0.1,
            summary="A",
        ),
        FundingApplication(
            project_id="b",
            title="B",
            requested_gbp=4000,
            target_people=1900,
            underserved_weight=0.8,
            evidence_strength=0.7,
            counterfactual_need=0.8,
            milestone_clarity=0.8,
            verification_strength=0.8,
            open_source_reuse=0.7,
            delivery_risk=0.2,
            summary="B",
        ),
    ]

    result = allocate_funding(applications, budget_gbp=5000)

    assert result["allocatedGbp"] <= 5000
    assert any(item["decision"] == "partial" for item in result["allocations"])
