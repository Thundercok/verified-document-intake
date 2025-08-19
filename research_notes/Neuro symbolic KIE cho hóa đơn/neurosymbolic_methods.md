# Neuro-symbolic approaches to document understanding and rule-based correction of OCR/extraction errors (2022–2026)

Scope note: about 35 searches and fetches, run 2026-11-21. A paper counts as "verified" when its title, authors, venue and ID were read from its arXiv, ACL Anthology, publisher or proceedings page, or from the PDF's first page. Numbers come from the paper's own HTML or PDF text unless marked "snippet-level". Work before 2022 is marked **[background]**.

## Q1. Which papers formulate document extraction or table reconstruction as constrained decoding, CSP, ILP, MaxSAT, SMT or PSL, and what is optimised and gained?

### Takeaway
Very little 2022–2026 work treats invoice or receipt extraction as a true joint optimisation problem (CSP, ILP, MaxSAT, SMT or PSL over field values). The main pattern is **generate-then-verify**: a neural model or LLM proposes candidates, and symbolic arithmetic or grounding checks filter them or pick among samples. The clearest example is Hemmer et al. (IJDAR 2025). It reports large F1 gains on the documents that pass the checks, but coverage drops sharply. The other options are hard logic constraints compiled into a neural layer (LogicMP, a Markov logic network solved by mean-field inference, on FUNSD) and grammar-constrained decoding, which restricts output format, not arithmetic.

### Cited Findings
**Hemmer, Coustaty, Bartolo, Ogier: "Neurosymbolic Information Extraction from Transactional Documents"**
- Published in IJDAR 28, 475–485 (2025), ICDAR 2025 journal track, arXiv 2512.09666. The DOI 10.1007/s10032-025-00530-0 comes from a citing paper's reference list. — [arXiv](https://arxiv.org/abs/2512.09666); DOI confirmed in [Giovannini et al. 2026 refs](https://ceur-ws.org/Vol-4332/paper8.pdf)
- Method: an LLM generates schema-based JSON candidates, which then pass three levels of symbolic checks — [arXiv HTML](https://arxiv.org/html/2512.09666v1):
  - Syntactic: the output must be valid JSON with all keys present.
  - Task: every value must appear verbatim in the OCR text.
  - Domain: arithmetic checks.
- The domain constraints include — [arXiv HTML](https://arxiv.org/html/2512.09666v1):
  - subtotal = sum of line items
  - gross total = net total + taxes
  - base taxable amount = sum of line-item net totals
  - total tax derivable from net total × tax rate
  - at least one line item, and a gross or net total present
  - tax rate between 0 and 1
- A constraint is checked only when all of its fields are filled, and equality allows a **0.5% relative tolerance**. — [arXiv HTML](https://arxiv.org/html/2512.09666v1)
- Nothing is "optimised" in the solver sense. Selection works by sampling N candidates at temperature 1.0, keeping only those that pass the checks, and taking the one with the highest mean token probability. — [arXiv HTML](https://arxiv.org/html/2512.09666v1)
- Data: CORD and SROIE were relabelled into a 53-field schema (CORD_TD, SROIE_TD). The models were Ministral-8B and Pixtral-12B zero-shot, and Ministral-8B, Llama-3.1-8B and Qwen2.5-14B fine-tuned with LoRA for distillation. OCR came from DocTR. — [arXiv HTML](https://arxiv.org/html/2512.09666v1)
- Zero-shot results, Pixtral-12B — [arXiv HTML](https://arxiv.org/html/2512.09666v1):
  - CORD_TD: F1 rises from 69.0 to 74.0 after the domain filter, but only **44.0%** of documents remain.
  - SROIE_TD: F1 rises from 40.5 to 45.4, with only **19.9%** remaining.
  - Ministral-8B on SROIE_TD keeps just 11.7% after the domain filter.
- Fine-tuned upper bound, Ministral-8B — [arXiv HTML](https://arxiv.org/html/2512.09666v1):
  - CORD_TD: F1 95.7 → 98.1 with 85.0% remaining; document accuracy 74.0 → 83.5.
  - SROIE_TD: F1 80.6 → 90.6 with 46.4% remaining.
- Distillation: training on domain-validated pseudo-labels raised F1 on CORD_TD from 69.7 to 77.4 (Ministral-8B), and gave +2 to +3 F1 on SROIE_TD across the three models. — [arXiv HTML](https://arxiv.org/html/2512.09666v1)
- Sampling 16 candidates raised the share of documents passing the domain filter (SROIE_TD: 19.9% → 51.2%) but lowered base F1. — [arXiv HTML](https://arxiv.org/html/2512.09666v1)
- Limitations the authors state — [arXiv HTML](https://arxiv.org/html/2512.09666v1):
  - The schema allows a single tax rate only.
  - The checks cannot correct OCR errors, because values must match the OCR text verbatim.
  - Decimal separators are ambiguous.
  - Some source documents have incorrect arithmetic themselves.

**Palm, Laws, Winther: "Attend, Copy, Parse" (ICDAR 2019) [background]**
- The authors tried to build total = subtotal + tax and tax = subtotal × rate into the loss as a marginal-probability term. They report it "did not improve on the results" and give no numbers. — [arXiv 1812.07248](https://arxiv.org/abs/1812.07248); [ar5iv full text](https://ar5iv.labs.arxiv.org/html/1812.07248)

**Xu et al.: "LogicMP: A Neuro-symbolic Approach for Encoding First-order Logic Constraints" (ICLR 2024)**
- arXiv 2309.15458. LogicMP is a plug-in neural layer that runs mean-field inference over a Markov logic network. The authors report it as about 10× faster than competing MLN inference methods. — [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/12143893d9d37c3569dda800b95cabd9-Abstract-Conference.html); [arXiv](https://arxiv.org/abs/2309.15458)
- Document task: FUNSD, framed as predicting a binary token "coexistence" matrix. The constraint is transitivity: C(a,b) ∧ C(b,c) ⇒ C(a,c). — [arXiv HTML](https://arxiv.org/html/2309.15458)
- Results with a LayoutLM-Pair backbone — [arXiv HTML](https://arxiv.org/html/2309.15458):
  - Full set: F1 82.0 → 83.3.
  - "Long" subset: F1 46.7 → 50.1.
  - The SL and SPL baselines failed to run on this task.

**Geng, Josifoski, Peyrard, West: "Grammar-Constrained Decoding for Structured NLP Tasks without Finetuning" (EMNLP 2023)**
- arXiv 2305.13971, DOI 10.18653/v1/2023.emnlp-main.674.
- Formal grammars, including input-dependent grammars, constrain the output space for closed IE (Wikidata-restricted triplets) and entity disambiguation. The authors report that constrained LMs beat unconstrained ones and sometimes beat fine-tuned models.
- This enforces structure and vocabulary, not arithmetic.
- [ACL Anthology](https://aclanthology.org/2023.emnlp-main.674); [arXiv](https://arxiv.org/abs/2305.13971)

**Probabilistic soft logic and SMT**
- PSL for document IE turned up only in a 2020 LWDA workshop paper on court sentences, which models extraction pipeline stages jointly with logic rules **[background, snippet-level]**. — [CEUR Vol-2738](https://ceur-ws.org/Vol-2738/LWDA2020_paper_29.pdf)
- A 2026 preprint pairs LLM extraction with Z3, treating extracted facts as soft constraints in a weighted MaxSAT/MaxSMT setup. Its domain is financial-legal compliance, not document tables **[snippet-level]**. — [arXiv 2601.06181](https://arxiv.org/html/2601.06181v1)

### Inferences
- Hemmer et al.'s "% remaining" is in effect the **coverage** of a selective extractor, and their F1 is F1 at that coverage. The arithmetic checks act as a precision gate, not a corrector. A zero-shot LLM pipeline may keep only 12–44% of receipts, so a correction step is needed to recover coverage. Options include a repair search over OCR digit confusions, or an ILP/MaxSAT step that finds the fewest field edits that satisfy the sums. The literature leaves that step mostly unexplored.
- A 0.5% tolerance plus "check only when all fields are present" is a practical, citable default for sum constraints. It also shows why exact-equality CSP formulations fail on real invoices: rounding, and source documents with wrong arithmetic.

### Gaps
- I found **no 2022–2026 paper** that formulates invoice or receipt field extraction as an ILP, CSP, MaxSAT or SMT problem with an explicit objective, such as minimum edits or maximum likelihood subject to sum constraints, with reported gains. This thin literature is itself a finding.
- I found no ILP- or CSP-based table structure recognition paper in 2022–2026. Table structure recognition is now dominated by neural graph and regression models such as LORE (arXiv 2303.03730); the search surfaced these but I did not examine them.
- I did not verify a peer-reviewed venue for LMDX (see Q6). The arXiv page lists none.

## Q2. Which works use knowledge graphs or entity linking (vendor, tax-ID or product registries) to validate or correct extracted fields?

### Takeaway
Academic evidence is thin. The one verified peer-reviewed KG-validation paper covers **structured EDIFACT e-invoices**, not OCR output. Registry lookup and vendor entity resolution for scanned invoices appear mainly in patents and vendor documentation, with no benchmarks.

### Cited Findings
- **Mäkelburg & Acosta, "Automating Invoice Validation with Knowledge Graphs: Optimizations and Practical Lessons"**, *Transactions on Graph Data and Knowledge* (TGDK) 3(3), 2:1–2:24, 2025, DOI 10.4230/TGDK.3.3.2. — [Dagstuhl DROPS](https://drops.dagstuhl.de/entities/document/10.4230/TGDK.3.3.2)
  - EDIFACT invoices are converted to RDF and validated with SHACL shapes written with domain experts.
  - SHACL severity is used to prioritise errors.
  - The abstract claims the approach is "correct, efficient, and practical". I did not read the metrics.
- Patents describe a validator that drops an extracted value it cannot find at its claimed location in the source. They also describe matching invoice totals against purchase orders. — [USPTO 12536376](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12536376); [USPTO 8526739](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8526739)
- Vendor and industry sources only, not peer-reviewed: they describe vendor-name resolution against ERP master data ("Acme Inc." vs "ACME INCORPORATED") and PO cross-document checks. — [Docsumo blog](https://docsumo.com/blog/cross-document-linking); [Atlan](https://atlan.com/know/ai-agent/data-for-ai/document-intelligence-for-enterprise/)

### Inferences
- For Vietnamese invoices, the closest analogue with a citation is SHACL-style constraint validation of structured e-invoices (Vietnam's e-invoice XML would fit). Registry lookup of the MST tax code against a business registry is an engineering choice without a research benchmark.

### Gaps
- I found no peer-reviewed 2022–2026 study that measures accuracy gains from linking OCR-extracted vendors or tax IDs to an external registry or product catalogue.
- I did not open the TGDK full text, so its constraint types (arithmetic vs mandatory fields) and its numbers are unverified.

## Q3. Program-of-thought, tool use and code execution for numeric reasoning over documents and tables: how much do they reduce arithmetic errors?

### Takeaway
Moving arithmetic into an executor brings large, well-documented gains on financial QA. PoT beats CoT by +24.1 points on FinQA, +19.0 on ConvFinQA and +7.6 on TAT-QA (Codex, greedy). Once arithmetic is offloaded, the main remaining error is **value grounding**, i.e. picking the wrong numbers. That is the same failure that field-level verification targets.

### Cited Findings
**Chen, Ma, Wang, Cohen: "Program of Thoughts Prompting" (TMLR 2023, arXiv 2211.12588)**
- Abstract: an average gain of about 12% over CoT across all evaluated datasets. — [arXiv](https://arxiv.org/abs/2211.12588)
- Table 2 (Codex, few-shot), CoT vs PoT — [ar5iv](https://ar5iv.labs.arxiv.org/html/2211.12588):

  | Dataset | CoT greedy | PoT greedy | CoT-SC | PoT-SC |
  |---|---|---|---|---|
  | FinQA | 40.4 | 64.5 | 44.4 | 68.1 |
  | ConvFinQA | 45.6 | 64.6 | 47.9 | 67.3 |
  | TAT-QA | 61.4 | 69.0 | 63.2 | 70.2 |

- The authors attribute the FinQA gains to CoT's "miscalculation errors" on large numbers. — [ar5iv](https://ar5iv.labs.arxiv.org/html/2211.12588)
- Error analysis of 198 PoT failures on TAT-QA — [ar5iv](https://ar5iv.labs.arxiv.org/html/2211.12588):
  - 47% value-grounding errors
  - 33% logic errors
  - 15% both
  - 5% actually correct

**Cheng et al.: "Binding Language Models in Symbolic Languages" (Binder, ICLR 2023 oral, arXiv 2210.02875)**
- Codex generates SQL or Python extended with LM-API calls, with no training.
- WikiTQ test: 65.2 vs 61.1 for Codex SQL and 48.7 for end-to-end Codex QA.
- TabFact small test set: 85.1 (86.0 with a retriever), against TAPEX's 85.9.
- [arXiv](https://arxiv.org/pdf/2210.02875); [ICLR](https://iclr.cc/virtual/2023/oral/12617)

**Zhu et al.: "TAT-LLM: A Specialized Language Model for Discrete Reasoning over Tabular and Textual Data" (ICAIF '24, arXiv 2401.13223)**
- A step-wise Extractor → Reasoner → **Executor** pipeline, fine-tuned from LLaMA-2.
- TAT-DQA: TAT-LLM (7B) reaches EM 69.45 / F1 77.75, against GPT-4's 64.46 / 72.20.
- [arXiv](https://arxiv.org/abs/2401.13223)

**Zhu et al.: "Towards Complex Document Understanding By Discrete Reasoning" (ACM MM 2022, arXiv 2207.11871)**
- Introduces TAT-DQA: 3,067 pages and 16,558 QA pairs from financial reports.
- Introduces MHST, a model that switches between extraction and reasoning. The authors say it still "lags far behind" expert humans.
- [arXiv](https://arxiv.org/abs/2207.11871)

**Zhao et al.: "DocMath-Eval: Evaluating Math Reasoning Capabilities of LLMs in Understanding Long and Specialized Documents" (ACL 2024)**
- DOI 10.18653/v1/2024.acl-long.852. It compares CoT and PoT across many LLMs; the best model, GPT-4o, still lags human experts (76%). — [ACL Anthology](https://aclanthology.org/2024.acl-long.852)
- Sources disagree on model count: 48 LLMs in the ACL version vs 27 in an earlier listing. — [ACL Anthology](https://aclanthology.org/2024.acl-long.852); [PSU Pure](https://pure.psu.edu/en/publications/docmath-eval-evaluating-math-reasoning-capabilities-of-llms-in-un/)

**Wang et al.: "Chain-of-Table: Evolving Tables in the Reasoning Chain for Table Understanding" (ICLR 2024, arXiv 2401.04398)**
- The LLM picks table operations that are executed programmatically, step by step. It is compared with CoT, Text-to-SQL, Binder and Dater on WikiTQ, TabFact and FeTaQA.
- [arXiv](https://arxiv.org/abs/2401.04398); [Google Research blog](https://research.google/blog/chain-of-table-evolving-tables-in-the-reasoning-chain-for-table-understanding/)

**Zhang et al.: "TableLLM: Enabling Tabular Data Manipulation by LLMs in Real Office Usage Scenarios" (arXiv 2403.19318; no venue on the arXiv page)**
- An 8B model trained on distantly supervised data with a "cross-way validation" check on the generated data. It covers tables in documents and in spreadsheets.
- [arXiv](https://arxiv.org/abs/2403.19318)

**FinQA (Chen et al., EMNLP 2021) and TAT-QA (Zhu et al., ACL 2021)** are the benchmarks the works above use **[background]**. I did not re-fetch them in this pass.

### Inferences
- In an invoice verifier, the PoT result means arithmetic should be recomputed deterministically, never trusted from an LLM. The PoT error split, with value grounding as the largest share, says the hard part is binding the right OCR tokens to variables. This supports pairing an executor with verbatim or segment grounding checks (Hemmer, LMDX).

### Gaps
- I did not extract per-model PoT vs CoT numbers from DocMath-Eval, so no claim that PoT beats CoT there is made from the paper itself.
- I found no system called "DocReasoner" and cannot verify that name.
- I did not retrieve TableLLM's or Chain-of-Table's numbers.

## Q4. Post-OCR correction with language or domain constraints (checksums, lexicons, gazetteers, number-word agreement), including LLM-based correction and its risks

### Takeaway
Recent LLM post-OCR work is mixed to negative. Boros et al. 2024 found that 14 LLMs **mostly degrade** historical transcriptions and often hallucinate. Kanerva et al. 2025 found gains in English but not Finnish. Bourne 2024 reports positive results when socio-cultural context is supplied. I found no peer-reviewed 2022–2026 paper on checksum- or registry-driven OCR correction of identifiers (VAT/MST, IBAN), or on amount-in-words vs amount-in-digits agreement. That evidence sits in patents and vendor documentation.

### Cited Findings
**Boros, Ehrmann, Romanello, Najem-Meyer, Kaplan: "Post-Correction of Historical Text Transcripts with Large Language Models: An Exploratory Study" (LaTeCH-CLfL 2024, pp. 133–159)**
- Evaluates 14 LLMs, zero- and few-shot. — [ACL Anthology](https://aclanthology.org/2024.latechclfl-1.14)
- Main finding: "LLMs mostly degrade the input text, occasionally leave it unchanged, and rarely improve it". Few-shot examples degraded results further for every model except GPT-3.5 and GPT-4. — [PDF](https://aclanthology.org/2024.latechclfl-1.14.pdf)
- The noisiest inputs degraded least and were sometimes improved. LLMs correct where needed but do not "leave almost error-free texts intact". — [PDF](https://aclanthology.org/2024.latechclfl-1.14.pdf)
- A manual analysis of about 2,500 pairs found mostly strong deviations from the ground truth, with "a majority of pure hallucination" for LLaMA-2-7B and BLOOMZ-7.1B. GPT models tended to paraphrase, and GPT-4 "embellish[ed]" text. — [PDF](https://aclanthology.org/2024.latechclfl-1.14.pdf)

**Kanerva, Ledins, Käpyaho, Ginter: "OCR Error Post-Correction with LLMs in Historical Documents: No Free Lunches" (arXiv 2502.01205, "to be published in RESOURCEFUL 2025")**
- Open-weight LLMs reduce CER in English, but "a practically useful performance for Finnish was not reached".
- [arXiv](https://arxiv.org/abs/2502.01205)

**Bourne: "CLOCR-C: Context Leveraging OCR Correction with Pre-trained Language Models" (arXiv 2408.17428)**
- Seven LMs on three 19th-century datasets. Supplying socio-cultural context helped and misleading prompts hurt. The top models worked well, but large closed models are likely too costly at archive scale.
- [arXiv](https://arxiv.org/abs/2408.17428)

**Other**
- Thomas, Gaizauskas, Lu (LT4HALA 2024) apply LLMs to post-OCR correction of historical newspapers **[snippet-level]**. — [ACL Anthology](https://aclanthology.org/2024.lt4hala-1.14)
- The ICDAR 2026 HIPE-OCRepair competition frames the open problem as reducing OCR errors "while avoiding overcorrection and hallucination" **[snippet-level]**. — [arXiv 2607.08143](https://arxiv.org/pdf/2607.08143)
- Checksum and format validators appear in industry sources and patents, not peer-reviewed research — [Nutrient](https://www.nutrient.io/guides/ai-document-processing/preconfigured-validators/); [matil.ai](https://matil.ai/en/blog/tax-id-validation); [USPTO 8526739](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8526739):
  - Nutrient ships prebuilt VAT, IBAN and date validators that set a field to "verification needed".
  - A practitioner blog says a passing checksum does not prove the ID is active or belongs to the named entity.
  - A patent notes that validation results could feed back to narrow OCR character hypotheses.

### Inferences
- The evidence argues against free-form LLM rewriting of numeric or identifier fields. It favours **constrained correction**: candidate edits limited to known OCR confusions (O/0, B/8, l/1) and accepted only when a checksum, sum or lexicon constraint becomes satisfied. Boros et al.'s finding that LLMs damage near-clean text suggests correction should trigger only when a verifier fails.

### Gaps
- I found no peer-reviewed 2022–2026 study of OCR correction driven by checksums (tax ID, IBAN, ISBN), gazetteers for addresses, or agreement between amounts in words and in digits. This gap is a finding.
- I did not extract numeric CER tables from Bourne or Kanerva.

## Q5. GNNs plus symbolic rules for form understanding; logic-based KIE; Logic Tensor Networks or DeepProbLog on documents

### Takeaway
Two verified logic-based document works: LogicMP (an MLN constraint layer on FUNSD, +1.3 / +3.4 F1) and a 2026 workshop paper that learns interpretable first-order layout rules with Logical Neural Networks on XFUND. I found **no** application of Logic Tensor Networks or DeepProbLog to documents.

### Cited Findings
- **LogicMP** on FUNSD: a transitivity constraint over token grouping; F1 82.0 → 83.3 on the full set and 46.7 → 50.1 on long documents. See Q1. — [arXiv HTML](https://arxiv.org/html/2309.15458)
- **Giovannini, Coppini, Marinai, "Language agnostic document key value extraction using Logical Neural Networks"**, BEWARE-26 workshop (co-located with AIxIA 2026), CEUR Workshop Proceedings Vol-4332, published 2026-11-17. — [CEUR PDF](https://ceur-ws.org/Vol-4332/paper8.pdf)
  - Logical Neural Networks learn first-order rules over predicates derived **only from layout and geometry**, with no text.
  - Key-value pairs: the best rules, such as verticalAligned ∧ isOnSameLine, reach test F1 of 0.812 and 0.754 for the two strongest source languages, with Portuguese the weakest at 0.684.
  - Cross-lingual transfer stays in roughly the 0.75–0.82 F1 range.
  - Key-field classification is weaker: F1 from 0.343 (ja) to 0.714 (fr).
- DeepProbLog (Manhaeve et al., NeurIPS 2018) and Logic Tensor Networks (Badreddine et al., arXiv 2012.13635) exist as frameworks **[background]**, but the search found no document or form application. — [DeepProbLog NeurIPS](https://neurips.cc/virtual/2018/spotlight/12755); [LTN arXiv](https://arxiv.org/pdf/2012.13635)

### Inferences
- Logic-based KIE is still at the workshop stage, and its rules are about layout, not arithmetic. LogicMP's gains are largest on long documents, where local neural predictions break global consistency most. That is a hint that structural constraints pay off most on multi-page or dense documents.

### Gaps
- I found no paper combining GNN form models (e.g. Doc2Graph, FormNet) with explicit symbolic rule layers. I did not investigate this deeply.
- I found no LTN or DeepProbLog application to documents; this negative result is a finding.

## Q6. Human-in-the-loop verification and selective or certified extraction (abstention, conformal risk control) with rules as verifiers

### Takeaway
One peer-reviewed KIE paper applies split conformal prediction: Rombach & Mehdiyev (IJDAR 2026) get 98.3% marginal coverage at α = 0.02 on WildReceipt, with 70% singleton sets that can be auto-processed. Rule verifiers used as abstention gates appear implicitly in LMDX (grounding check) and Hemmer et al. (arithmetic filter). I found no paper that combines conformal guarantees with symbolic rule verifiers for documents.

### Cited Findings
**Rombach & Mehdiyev: "Beyond Accuracy: Understanding Model Confidence in Key Information Extraction with Conformal Prediction"**
- IJDAR 2026, DOI 10.1007/s10032-026-00572-y; received 28 May 2025, accepted 19 Feb 2026. — [PDF (DFKI copy)](https://www-live.dfki.de/fileadmin/user_upload/import/17320_s10032-026-00572-y.pdf)
- Method: post hoc split conformal prediction on fine-tuned LayoutLM, LayoutLMv2, LayoutLMv3 and ERNIE-Layout. — [PDF](https://www-live.dfki.de/fileadmin/user_upload/import/17320_s10032-026-00572-y.pdf)
- Data: WildReceipt, with 1,739 receipt photos, 25 fields and 1,192 templates. — [PDF](https://www-live.dfki.de/fileadmin/user_upload/import/17320_s10032-026-00572-y.pdf)
- Results — [PDF](https://www-live.dfki.de/fileadmin/user_upload/import/17320_s10032-026-00572-y.pdf):
  - 98.3% marginal coverage at α = 0.02.
  - 70% singleton sets, plus 24% sets of size 2.
  - Mean set size 1.38.
  - Dates and prices give near-perfect singletons; tips and generic keywords give larger sets and lower coverage.
  - Singletons are routed to automatic processing and larger sets to human review.

**LMDX (Perot et al., "LMDX: Language Model-based Document Information Extraction and Localization", arXiv 2309.10952; no venue on the arXiv page)** — [arXiv HTML v2](https://arxiv.org/html/2309.10952v2)
- Grounding works through line-level coordinate tokens. The LLM must cite a segment ID for each entity, and the parser discards an entity if the ID does not exist or the text is not in that line, which removes hallucinations.
- Decoding takes K = 16 samples with JSON-parse filtering and per-entity majority voting.
- CORD: zero-shot F1 66.95 (PaLM 2-S); 90.02 with 10 training documents, against LayoutLMv3's 74.04.
- VRDU Registration Form (10 training documents): 87.72 vs LayoutLMv2's 69.44.

**Hemmer et al.** (Q1): domain-filter coverage of 11.7–44% zero-shot and 46–85% fine-tuned is an explicit coverage–accuracy trade-off set by rules. — [arXiv HTML](https://arxiv.org/html/2512.09666v1)

**Adjacent conformal abstention work outside documents [snippet-level; full texts not read]**
- Conformal selective abstention in a fact-checking pipeline (CEUR Vol-4307). — [CEUR](https://ceur-ws.org/Vol-4307/paper33.pdf)
- PASC: joint coverage across multi-stage pipelines, including IE (arXiv 2605.18812). — [arXiv](https://arxiv.org/html/2605.18812)
- Conformal abstention for Text-to-SQL (arXiv 2501.10858). — [arXiv](https://arxiv.org/pdf/2501.10858)

### Inferences
- A natural and apparently **unpublished** combination: use rule-verifier outcomes as part of the nonconformity score, or as a hard pre-filter before conformal calibration, so the guarantee holds on the auto-accepted subset. Rombach & Mehdiyev's per-field finding fits Hemmer's arithmetic checks: structured fields such as dates and prices are where both calibration and rules work best.
- Note that marginal coverage, as reported by Rombach & Mehdiyev, is not per-field or per-document coverage. Rare fields had lower coverage.

### Gaps
- I did not fetch or verify Conformal Risk Control (Angelopoulos et al.) or conformal language modelling in this pass. The report writer should not cite them from these notes without checking.
- I found no paper with conformal or certified guarantees for document extraction that uses symbolic rule verifiers.
- I found no Amazon or Microsoft industry paper on invoice processing with symbolic verification; Google LMDX is the only big-lab system covered.
