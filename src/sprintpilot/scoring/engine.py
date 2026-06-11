"""Deterministic Engineering Confidence Score engine."""

from __future__ import annotations

from sprintpilot.domain import (
    ArchitecturePlan,
    ConfidenceFactorScore,
    EngineeringConfidenceAssessment,
    MissingInformation,
    ProductDefinition,
    Reasoning,
    Recommendation,
    Risk,
    ScoreCap,
    SprintPlan,
)
from sprintpilot.scoring.factors import CONFIDENCE_FACTORS, ConfidenceFactor
from sprintpilot.validation.artifacts import (
    validate_architecture_completeness,
    validate_sprint_plan_completeness,
)
from sprintpilot.validation.scope import detect_forbidden_scope


def assess_engineering_confidence(
    *,
    product_definition: ProductDefinition | None,
    architecture_plan: ArchitecturePlan | None,
    sprint_plan: SprintPlan | None,
) -> EngineeringConfidenceAssessment:
    """Assess implementation readiness from validated Core v1 artifacts."""

    factors = [
        _score_requirement_clarity(product_definition),
        _score_architecture_completeness(architecture_plan),
        _score_dependency_readiness(product_definition, architecture_plan, sprint_plan),
        _score_acceptance_criteria_quality(product_definition, sprint_plan),
        _score_technical_ambiguity(product_definition, architecture_plan, sprint_plan),
        _score_delivery_risk(product_definition, architecture_plan, sprint_plan),
    ]

    weighted = round(sum(score.score * score.weight for score in factors) / 100)
    caps = _score_caps(product_definition, architecture_plan, sprint_plan)
    overall = min([weighted, *[cap.cap for cap in caps]]) if caps else weighted

    missing_information = _collect_missing_information(product_definition, architecture_plan)
    risks = _collect_risks(product_definition, architecture_plan, sprint_plan)
    recommendations = _recommendations(overall, factors, caps, missing_information)

    return EngineeringConfidenceAssessment(
        overall_score=overall,
        factor_scores=factors,
        score_caps=caps,
        reasoning=Reasoning(
            summary=(
                "Engineering confidence is calculated from requirement clarity, architecture "
                "completeness, dependency readiness, acceptance criteria quality, technical "
                "ambiguity and delivery risk."
            )
        ),
        risks=risks,
        missing_information=missing_information,
        recommendations=recommendations,
    )


def _factor(key: str) -> ConfidenceFactor:
    return next(factor for factor in CONFIDENCE_FACTORS if factor.key == key)


def _factor_score(
    key: str,
    score: int,
    *,
    reason_code: str,
    reasoning: str,
    evidence: list[str] | None = None,
) -> ConfidenceFactorScore:
    factor = _factor(key)
    return ConfidenceFactorScore(
        key=factor.key,
        label=factor.label,
        score=max(0, min(100, score)),
        weight=factor.weight,
        reason_code=reason_code,
        reasoning=reasoning,
        evidence=evidence or [],
    )


def _score_requirement_clarity(product_definition: ProductDefinition | None) -> ConfidenceFactorScore:
    if product_definition is None:
        return _factor_score(
            "requirement_clarity",
            0,
            reason_code="missing_product_definition",
            reasoning="Product definition is missing.",
        )

    score = 100
    evidence = [
        f"{len(product_definition.functional_requirements)} functional requirements",
        f"{len(product_definition.user_stories)} user stories",
    ]
    if not product_definition.functional_requirements:
        score -= 40
    if not product_definition.user_stories:
        score -= 35
    if not product_definition.assumptions:
        score -= 10
    if not product_definition.reasoning.summary:
        score -= 20
    return _factor_score(
        "requirement_clarity",
        score,
        reason_code="requirements_reviewed",
        reasoning="Requirement clarity reflects requirements, stories, assumptions and reasoning.",
        evidence=evidence,
    )


def _score_architecture_completeness(architecture_plan: ArchitecturePlan | None) -> ConfidenceFactorScore:
    if architecture_plan is None:
        return _factor_score(
            "architecture_completeness",
            0,
            reason_code="missing_architecture_plan",
            reasoning="Architecture plan is missing.",
        )

    errors = validate_architecture_completeness(architecture_plan)
    score = 100 - (15 * len(errors))
    if not architecture_plan.system_components:
        score -= 30
    if not architecture_plan.technology_stack_categories:
        score -= 20
    return _factor_score(
        "architecture_completeness",
        score,
        reason_code="architecture_reviewed" if not errors else "architecture_gaps",
        reasoning="Architecture completeness reflects components, stack categories, tradeoffs, assumptions, open questions and reasoning.",
        evidence=errors or [f"{len(architecture_plan.system_components)} system components"],
    )


def _score_dependency_readiness(
    product_definition: ProductDefinition | None,
    architecture_plan: ArchitecturePlan | None,
    sprint_plan: SprintPlan | None,
) -> ConfidenceFactorScore:
    score = 100
    evidence: list[str] = []
    if architecture_plan is None or sprint_plan is None:
        return _factor_score(
            "dependency_readiness",
            20 if product_definition else 0,
            reason_code="missing_dependency_artifacts",
            reasoning="Dependency readiness cannot be fully assessed without architecture and sprint artifacts.",
        )
    if not sprint_plan.dependencies:
        score -= 25
        evidence.append("No sprint dependencies were identified.")
    if architecture_plan.open_questions:
        score -= min(30, 10 * len(architecture_plan.open_questions))
        evidence.append(f"{len(architecture_plan.open_questions)} architecture open questions")
    if product_definition and product_definition.missing_information:
        score -= min(20, 10 * len(product_definition.missing_information))
        evidence.append(f"{len(product_definition.missing_information)} product missing-information items")
    return _factor_score(
        "dependency_readiness",
        score,
        reason_code="dependencies_reviewed",
        reasoning="Dependency readiness reflects open questions, missing information and sprint dependencies.",
        evidence=evidence,
    )


def _score_acceptance_criteria_quality(
    product_definition: ProductDefinition | None,
    sprint_plan: SprintPlan | None,
) -> ConfidenceFactorScore:
    if product_definition is None or sprint_plan is None:
        return _factor_score(
            "acceptance_criteria_quality",
            0,
            reason_code="missing_story_artifacts",
            reasoning="Acceptance criteria cannot be assessed without product and sprint stories.",
        )

    product_story_count = len(product_definition.user_stories)
    sprint_story_count = len(sprint_plan.stories)
    stories_with_criteria = sum(1 for story in sprint_plan.stories if story.acceptance_criteria)
    score = 100
    if product_story_count == 0 or sprint_story_count == 0:
        score = 0
    elif stories_with_criteria < sprint_story_count:
        score -= 40
    return _factor_score(
        "acceptance_criteria_quality",
        score,
        reason_code="acceptance_criteria_reviewed",
        reasoning="Acceptance criteria quality reflects product and sprint stories with testable criteria.",
        evidence=[f"{stories_with_criteria}/{sprint_story_count} sprint stories include acceptance criteria"],
    )


def _score_technical_ambiguity(
    product_definition: ProductDefinition | None,
    architecture_plan: ArchitecturePlan | None,
    sprint_plan: SprintPlan | None,
) -> ConfidenceFactorScore:
    ambiguity_count = 0
    if product_definition:
        ambiguity_count += len(product_definition.missing_information)
    if architecture_plan:
        ambiguity_count += len(architecture_plan.open_questions)
    if sprint_plan:
        ambiguity_count += len(sprint_plan.risks)
    score = 100 - min(70, ambiguity_count * 10)
    return _factor_score(
        "technical_ambiguity",
        score,
        reason_code="ambiguity_reviewed",
        reasoning="Technical ambiguity reflects missing information, open questions and planning risks.",
        evidence=[f"{ambiguity_count} ambiguity signals"],
    )


def _score_delivery_risk(
    product_definition: ProductDefinition | None,
    architecture_plan: ArchitecturePlan | None,
    sprint_plan: SprintPlan | None,
) -> ConfidenceFactorScore:
    if sprint_plan is None:
        return _factor_score(
            "delivery_risk",
            0,
            reason_code="missing_sprint_plan",
            reasoning="Delivery risk cannot be assessed without a sprint plan.",
        )

    errors = validate_sprint_plan_completeness(sprint_plan)
    risk_count = len(sprint_plan.risks)
    if product_definition:
        risk_count += len(product_definition.risks)
    if architecture_plan:
        risk_count += len(architecture_plan.risks)
    score = 100 - min(80, risk_count * 10 + len(errors) * 15)
    return _factor_score(
        "delivery_risk",
        score,
        reason_code="delivery_risks_reviewed",
        reasoning="Delivery risk reflects sprint completeness, explicit risks and estimate quality.",
        evidence=errors or [f"{risk_count} explicit risks"],
    )


def _score_caps(
    product_definition: ProductDefinition | None,
    architecture_plan: ArchitecturePlan | None,
    sprint_plan: SprintPlan | None,
) -> list[ScoreCap]:
    caps: list[ScoreCap] = []
    if product_definition is None or architecture_plan is None or sprint_plan is None:
        caps.append(
            ScoreCap(
                reason="missing_critical_artifacts",
                cap=60,
                explanation="Confidence cannot exceed 60 without product, architecture and sprint artifacts.",
            )
        )

    combined = " ".join(
        artifact.model_dump_json()
        for artifact in (product_definition, architecture_plan, sprint_plan)
        if artifact is not None
    )
    if detect_forbidden_scope(combined):
        caps.append(
            ScoreCap(
                reason="out_of_scope_content",
                cap=70,
                explanation="Confidence cannot exceed 70 while Core v1 artifacts include out-of-scope content.",
            )
        )
    return caps


def _collect_missing_information(
    product_definition: ProductDefinition | None,
    architecture_plan: ArchitecturePlan | None,
) -> list[MissingInformation]:
    items: list[MissingInformation] = []
    if product_definition is None:
        items.append(MissingInformation(question="Where is the product definition?", impact="Required for scoring."))
    else:
        items.extend(product_definition.missing_information)
    if architecture_plan is None:
        items.append(MissingInformation(question="Where is the architecture plan?", impact="Required for scoring."))
    else:
        items.extend(architecture_plan.open_questions)
    return items


def _collect_risks(
    product_definition: ProductDefinition | None,
    architecture_plan: ArchitecturePlan | None,
    sprint_plan: SprintPlan | None,
) -> list[Risk]:
    risks: list[Risk] = []
    for artifact in (product_definition, architecture_plan, sprint_plan):
        if artifact is not None:
            risks.extend(artifact.risks)
    return risks


def _recommendations(
    overall_score: int,
    factors: list[ConfidenceFactorScore],
    caps: list[ScoreCap],
    missing_information: list[MissingInformation],
) -> list[Recommendation]:
    recommendations: list[Recommendation] = []
    if overall_score >= 90:
        return recommendations

    weakest = min(factors, key=lambda factor: factor.score)
    recommendations.append(
        Recommendation(
            action=f"Improve {weakest.label.lower()}",
            rationale=weakest.reasoning,
        )
    )
    if missing_information:
        recommendations.append(
            Recommendation(
                action="Resolve missing planning information",
                rationale="Open questions and missing information reduce engineering readiness.",
            )
        )
    if any(cap.reason == "out_of_scope_content" for cap in caps):
        recommendations.append(
            Recommendation(
                action="Remove or defer out-of-scope Core v1 content",
                rationale="Future-module content lowers confidence in the current implementation scope.",
            )
        )
    return recommendations
