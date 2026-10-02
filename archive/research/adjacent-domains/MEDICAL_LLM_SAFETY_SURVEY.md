# Preventing Unsafe Consequences from Medical LLMs: A Recent Research Survey and Taxonomy

The central conclusion is:

> The unit of medical LLM safety should shift from answer correctness to the downstream actions and clinical outcomes caused by the answer.

A response may correctly identify possible myocardial infarction but remain unsafe if it recommends scheduling an outpatient appointment the next day. Conversely, sending every user to the emergency department creates overtriage, resource burden, and user disengagement.

The goal is therefore not a uniformly conservative model, but one that guides action appropriately in proportion to risk.

This is a structured narrative survey covering research available through August 3, 2026. It prioritizes peer-reviewed work from 2024–2026; preprints are explicitly identified.

## 1. Why accuracy alone is not a sufficient safety measure

A JAMA systematic review of 519 studies found that 95.4% evaluated accuracy, but only 5% used real patient-care data, 1.2% evaluated calibration or uncertainty, and 4.6% examined deployment. Most research therefore asks whether an LLM can answer medical questions—not whether patients remain safe after using its answers. [JAMA systematic review](https://jamanetwork.com/journals/jama/fullarticle/2825147)

A Nature Medicine study using 2,400 cases derived from real electronic health records found that LLMs underperformed physicians in diagnosis, treatment-guideline adherence, laboratory interpretation, and robustness to changes in information order and presentation. High medical-knowledge scores did not reliably translate into sound clinical decision-making. [Hager et al., Nature Medicine 2024](https://www.nature.com/articles/s41591-024-03097-1)

More direct evidence has since emerged:

- HealthAdvice evaluated 888 responses to 222 patient questions. Between 21.6% and 43.2% of responses contained problematic content, and 5–13% were judged unsafe. Failures included not only incorrect information, but also omitted warnings and missing follow-up questions in situations involving infant fever, alcohol withdrawal, and medication use during pregnancy. [HealthAdvice, npj Digital Medicine 2026](https://www.nature.com/articles/s41746-026-02428-5)

- In 960 structured triage interactions, ChatGPT Health undertriaged 51.6% of emergency cases and overtriaged 64.8% of nonurgent cases. When a family member or friend minimized the patient’s symptoms, the model shifted substantially toward less urgent dispositions. [Nature Medicine 2026](https://www.nature.com/articles/s41591-026-04297-7)

- In a randomized study involving 1,298 UK adults, participants using an LLM did not achieve better triage decisions and performed worse at identifying relevant conditions. Human–LLM performance was substantially worse than model-only evaluations, partly because users omitted important information or misinterpreted model outputs. Simulated patients did not reliably predict this effect. [Nature Medicine 2026 RCT](https://www.nature.com/articles/s41591-025-04074-y)

A useful definition is therefore:

> **Consequence safety** is the property that an LLM-mediated interaction does not increase expected patient harm relative to an appropriate clinical comparator.

---

## 2. Proposed research taxonomy

The literature can be organized along three largely independent axes:

1. What kind of harm occurs: a **hazard taxonomy**
2. Where the harm is prevented: an **intervention taxonomy**
3. How realistically safety is validated: an **evidence-maturity taxonomy**

### A. Hazard taxonomy: What unsafe consequence occurs?

| Hazard | Definition | Example | Key evaluation target |
|---|---|---|---|
| Commission harm | Recommending an action that should not be taken | Contraindicated medication, unsafe dose, hazardous self-treatment | Harmful recommendation rate |
| Omission harm | Failing to provide necessary information or action | Missing red flags, emergency escalation, contraindications, or safety-netting | Critical omission rate |
| Timing or disposition harm | Recommending the wrong time or location of care | Routine appointment instead of emergency care, or unnecessary ED referral | Undertriage and overtriage |
| Epistemic harm | Mishandling knowledge or uncertainty | Hallucination, outdated evidence, overconfidence, failure to abstain | Calibration and selective risk |
| Interaction harm | The conversation itself leads to unsafe behavior | Incomplete history-taking, following user anchoring, burying urgent advice | Multi-turn harm and action latency |
| Distributional harm | Harm is concentrated in particular populations | Different testing or triage by race, sex, income, or language | Subgroup worst-case risk |
| Systemic harm | Harm emerges from the larger technical system | Privacy leakage, data poisoning, tool errors, scalable misinformation | Incident and attack-success rates |

Omission harm is particularly undermeasured. Detecting an incorrect statement is easier than detecting something the model should have said but did not.

Similarly, counting disclaimers or referrals is insufficient. A 2026 study found that 97% of chatbot responses recommended professional consultation, but referral frequency alone does not establish that the recommended urgency, timing, or location was appropriate. [JMIR 2026](https://www.jmir.org/2026/1/e84668/)

### B. Intervention taxonomy: Where is safety introduced?

#### 1. Data and knowledge layer

Relevant interventions include:

- Provenance- and date-verified clinical guidelines
- Version-controlled drug, dose, and contraindication databases
- Detection of poisoned training data
- Localization to regional referral pathways and healthcare access
- Retrieval-augmented generation and knowledge-graph verification

A very small amount of poisoned medical training data can increase harmful medical errors without materially reducing conventional benchmark scores. In one study, knowledge-graph-based output verification detected 91.9% of harmful content. [Nature Medicine 2025](https://www.nature.com/articles/s41591-024-03445-1)

#### 2. Training and alignment layer

Potential interventions include:

- Clinician-authored safe-completion examples
- Risk-sensitive SFT, DPO, or RLHF
- Alignment with medical ethics and contraindication policies
- Training models to provide safe alternatives instead of merely refusing

MedSafetyBench showed that medical safety fine-tuning could reduce compliance with harmful requests without substantially degrading general medical QA performance. Its main limitation is that it emphasizes malicious requests and refusal behavior, rather than omissions and undertriage in benign patient questions. [NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/3ac952d0264ef7a505393868a70a46b6-Abstract-Datasets_and_Benchmarks_Track.html)

#### 3. Inference-time clinical safety policy

The system can apply structured policies before or during generation:

- Classify red flags before generating a full response
- Escalate immediately when risk is high
- Collect required history in a structured manner
- Present emergency actions before explanations
- For low-risk cases, provide self-care guidance together with explicit deterioration criteria

This should ideally be implemented as a structured policy or separate module rather than relying on a single prompt.

#### 4. Uncertainty, abstention, and human handoff

Important capabilities include:

- Declining to answer when evidence is insufficient
- Transferring a case to a clinician when estimated risk crosses a threshold
- Distinguishing uncertainty-driven abstention from safety-driven abstention
- Calibrating error risk rather than relying on verbal confidence

In medical QA, models’ self-reported confidence was almost universally overconfident. Consistency across repeated samples was generally a more useful uncertainty signal, although most uncertainty measures remained weak for treatment-selection tasks. [JAMIA 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11648734/)

MedQAbstain similarly found that models systematically overcommitted and generated answers even when the available information could not support a correct conclusion. [ACL 2026](https://aclanthology.org/2026.acl-long.1365/)

#### 5. Independent guardrails and verification

A separate safety layer can check:

- Emergency red flags
- Medication contraindications and interactions
- Required and prohibited actions
- Consistency with retrieved guidelines
- The implied triage or disposition level
- Whether to accept, caution, refuse, or escalate

Asking the same model to review its own answer is limited because generation and verification may share the same failure modes. Independent rules, databases, classifiers, or differently trained models provide stronger separation.

#### 6. Deployment and governance

Deployment-level protections include:

- Separating patient-facing and clinician-support privileges
- Preventing autonomous execution of high-risk actions
- Pinning model, prompt, and knowledge-base versions
- Safety regression testing before updates
- Monitoring subgroup errors and near misses
- Incident reporting, rollback mechanisms, and kill switches
- Measuring automation bias in real users and clinicians

A cluster-randomized trial involving 16 Kenyan primary-care facilities, 103 clinical officers, and 9,691 patients found no new safety signal under clinician supervision. However, it also did not demonstrate a statistically significant reduction in treatment failure. This supports the feasibility of prospective evaluation in a bounded, supervised role—not the safety of autonomous patient-facing decision-making. [Nature Medicine 2026](https://www.nature.com/articles/s41591-026-04503-6)

---

## 3. Evidence-maturity taxonomy

| Level | Evaluation setting | What it can establish | What it cannot establish |
|---|---|---|---|
| L0 | Multiple-choice medical QA | Medical knowledge and test performance | Real-world behavioral safety |
| L1 | Open-ended clinical vignettes | Omissions and harmful recommendations | Actual user response |
| L2 | Adversarial, paraphrased, and multi-turn cases | Vulnerability, consistency, and tail risk | Real workflow effects |
| L3 | Multisite retrospective EHR replay | Realistic distributions and subgroup performance | Effects on patient behavior |
| L4 | Real-user or clinician simulation/RCT | Information transfer, overtrust, automation bias | Long-term patient outcomes |
| L5 | Prospective silent or live clinical trial | Clinical outcomes and actual harm | Long-term postdeployment drift |
| L6 | Postdeployment surveillance | Near misses, rare harms, update regressions | Some forms of controlled causal inference |

Most medical LLM studies remain at L0–L2. L4 and L5 evidence only began to emerge meaningfully in 2025–2026.

An evidence map of 55 clinical outcome studies conducted between 2022 and mid-2025 found that 65.5% examined human–AI collaboration. Randomized studies produced lower and more variable diagnostic performance than nonrandomized studies, and the evidence for clinical benefit remained insufficient. [npj Digital Medicine 2026](https://www.nature.com/articles/s41746-026-02837-6)

---

## 4. Evolution of the research landscape

### 2024: From knowledge evaluation to multidimensional safety

Major developments included:

- MedSafetyBench for harmful-request compliance and safety fine-tuning
- EquityMedQA for biases not visible in conventional medical QA
- Evaluation on realistic clinical cases showing sensitivity to prompt order and information presentation

EquityMedQA contains 4,619 examples across seven adversarial datasets and uses input from physicians, equity experts, and consumers. It found more pronounced bias in adversarial settings than in ordinary medical QA. [Nature Medicine 2024](https://www.nature.com/articles/s41591-024-03258-2)

### 2025: Harm weighting, attack robustness, and real-user concerns

Research expanded toward:

- Training-data poisoning and adversarial fine-tuning
- Harm-weighted evaluation
- Sociodemographic counterfactual testing
- Retrieval and independent verification
- Human–AI interaction

One study generated more than 1.7 million outputs by varying sociodemographic characteristics across 1,000 emergency-department cases. Recommendations differed by factors such as income level without a corresponding clinical justification. [Nature Medicine 2025](https://www.nature.com/articles/s41591-025-03626-6)

HealthBench introduced 5,000 multi-turn health conversations and 48,562 physician-written evaluation criteria covering emergency referral, uncertainty, context gathering, and communication. It represents a significant methodological advance, but remains a rubric-based benchmark rather than a patient-outcome study. As of the survey cutoff, it should be treated as a preprint. [HealthBench 2025 preprint](https://arxiv.org/abs/2505.08775)

CSEDB introduced 2,069 open-ended cases, 17 safety metrics, and a harm-weighted safety gate. Average model performance decreased substantially in high-risk cases, demonstrating why overall averages can conceal dangerous weaknesses. [npj Digital Medicine 2026](https://www.nature.com/articles/s41746-025-02277-8)

### 2026: Triage, abstention, and human–LLM systems

The most important developments include:

- Direct measurement of unsafe omissions in HealthAdvice
- Triage failures at both emergency and nonurgent extremes
- Systematic study of inappropriate answer generation under uncertainty
- Randomized studies with real public users
- Prospective clinical outcome studies under clinician supervision

The overall progression can be summarized as:

```text
Medical accuracy
    → Content safety
    → Risk-sensitive action evaluation
    → Human–LLM interaction
    → Actual patient outcomes
```

---

## 5. Designing a benchmark for unsafe consequences

To evaluate the specific problem—“the answer may be medically correct, but the patient should have been told to seek urgent care”—a benchmark cannot rely on a single reference answer.

Each case should instead be annotated with:

- `M`: mandatory critical actions
- `P`: prohibited actions
- `Q`: information that must be collected
- `D`: appropriate disposition, location, and time window
- `S`: required safety-net instructions
- `H`: severity and reversibility of potential harm

Evaluation should use a safety gate before computing an average quality score:

1. Was a life-critical action omitted?
2. Was a prohibited action recommended?
3. Was the user directed to the appropriate level of care within the correct time?
4. Did the model abstain or escalate appropriately under uncertainty?
5. Only then should diagnosis, explanation, empathy, and writing quality be scored.

A critical emergency omission should not be offset by excellent reasoning, diagnostic accuracy, or communication.

### Recommended metrics

- Catastrophic omission rate
- Severity-weighted harmful commission rate
- Undertriage and overtriage by acuity
- Number of sentences before the first urgent action instruction
- Appropriate abstention and handoff rate
- Risk–coverage curve
- Worst-of-N performance across paraphrases and dialogue orderings
- Maximum subgroup harm and undertriage disparity
- The action ultimately selected by the user
- Actual adverse events and near misses

Results should be reported separately for high-risk slices such as emergencies, pregnancy, infants, older adults, polypharmacy, and mental-health crises. The worst-group result may be more informative than the global average.

---

## 6. Recommended system architecture

```text
User input
    ↓
Emergency red-flag and risk gate
    ├── High risk → Immediate action instruction + clinician handoff
    └── Otherwise → Collect required context
                          ↓
               Retrieve current guidelines
                          ↓
                 Generate draft response
                          ↓
       Independent contraindication, omission,
              and triage verification
                          ↓
     Self-care / outpatient / same-day / emergency route
                          ↓
       Near-miss, subgroup, and incident monitoring
```

Important design principles include:

- For high-risk situations, put the required action before the explanation.
- Do not delay emergency escalation while collecting additional history.
- Specify when, where, and how urgently care should be obtained; generic “consult a professional” language is insufficient.
- Avoid unnecessary emergency referrals in genuinely low-risk cases.
- Do not use the model’s verbal confidence as the primary safety mechanism.
- Do not treat prompting, RAG, or fine-tuning alone as a safety guarantee.
- Use independent safety gates and human handoff for high-risk decisions and actions.

---

## 7. Highest-priority research gaps

1. **Omission-centered benchmarks**  
   Benchmarks should explicitly evaluate missing questions, warnings, safety-netting, and escalation—not only incorrect statements.

2. **Measurement of actual user behavior**  
   The important outcome is not whether an emergency recommendation appeared somewhere in the response, but whether the user understood the urgency and chose an appropriate action.

3. **Tail-risk evaluation**  
   A rare catastrophic error may matter more than high average accuracy. Repeated sampling, paraphrases, adversarial dialogue, and worst-case evaluation are necessary.

4. **Longitudinal and multi-turn safety**  
   A model may initially recommend urgent care but later withdraw that recommendation when the user resists or minimizes symptoms.

5. **Asymmetric costs of undertriage and overtriage**  
   Undertriage should generally receive a greater harm weight, while overtriage must still be measured because of cost, access, and trust consequences.

6. **Localized consequence benchmarks**  
   Benchmarks should reflect local emergency numbers, referral pathways, medication names, language patterns, and healthcare-system constraints.

7. **Continuous postdeployment monitoring**  
   Model behavior can change after updates even when the product name remains the same. Version-specific regression testing and near-miss surveillance are essential.

## Conclusion

The most promising direction is not simply to build a more knowledgeable medical LLM. It is to build a safety-oriented system combining:

> **risk-sensitive triage gates + safe completion + calibrated abstention + independent verification + human handoff + real-world outcome monitoring**

Current evidence supports prospective evaluation of such systems in constrained roles under clinician supervision. It does not yet support the conclusion that autonomous, patient-facing medical decision systems are sufficiently safe.