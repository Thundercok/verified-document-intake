# Error rates, hallucination and numeric-consistency checking in neural / MLLM extraction of financial documents (2022–2026)

Scope note: research done 2026-11-21. "Verified" below means the abstract page or full HTML of the paper was opened and the number was read from it. Items seen only in search snippets are flagged **[snippet only]**. Pre-2022 material is flagged **[background]**. Several 2026 arXiv items are recent preprints without peer review; that is stated per item.

## Q1. Reported error rates of MLLMs and OCR-free models on numeric fields, line items and tables

### Takeaway
On realistic invoice/receipt benchmarks, even frontier MLLMs leave large error mass: on ReceiptBench (10k receipts, 2026) Gemini-3-Pro reaches only 0.7373 overall F1 and 0.5781 F1 on nested line-item structure parsing (GPT-5: 0.4893), and GPT-4o on DocILE invoice fields is wrong on roughly 26% of fields. Line items / hierarchical fields are consistently the weakest category across VRDU, DocILE and ReceiptBench, and pre-LLM supervised baselines on DocILE only reach ~0.66–0.70 F1.

### Cited Findings

**ReceiptBench (MLLMs, 2026)**
- Paper: "From Recognition to Reasoning: Benchmarking and Enhancing MLLMs on Real-World Receipt Document Understanding", Yandi Wang et al., arXiv:2605.22413 (v1, 21 May 2026). arXiv page lists no venue; a search result shows an ACL Anthology PDF at `2026.acl-long.2135` (ACL 2026 long), which I did not open. Benchmark: 10k human-annotated receipts, four task levels (Basic Perception, Format Normalization, Semantic Reasoning, Structure Parsing of nested line items). — [arXiv abs](https://arxiv.org/abs/2605.22413); [ACL Anthology PDF (not opened)](https://aclanthology.org/2026.acl-long.2135.pdf)
- F1 (Table 3), Overall / Perception / Normalization / Reasoning / Structure: Gemini-3-Pro 0.7373 / 0.7360 / 0.9086 / 0.8714 / 0.5781; GPT-5 0.7076 / 0.7304 / 0.8743 / 0.8706 / 0.4893; Qwen3-VL-Plus 0.7210 / 0.7306 / 0.9000 / 0.8787 / 0.5484; Qwen3-VL-32B (open, no fine-tuning) 0.6751 / 0.6645 / 0.8310 / 0.8690 / 0.4852; authors' Qwen3-VL-8B SFT+GRPO 0.7950 / 0.8488 / 0.9416 / 0.8547 / 0.6373. Model versions are given only as family names/sizes; Claude was not evaluated. — [arXiv HTML](https://arxiv.org/html/2605.22413v1)
- Paper states structure parsing (nested line items) is the bottleneck for all baselines. — [arXiv HTML](https://arxiv.org/html/2605.22413v1)

**DocILE (invoices; supervised baselines, background for LLM numbers)**
- Paper: "DocILE Benchmark for Document Information Localization and Extraction", Štěpán Šimsa et al., ICDAR 2023, arXiv:2302.05658. 6.7k annotated business documents, 100k synthetic, ~1M unlabeled; 55 field classes; tasks KILE and LIR (line item recognition). — [arXiv abs](https://arxiv.org/abs/2302.05658)
- Test set, best permitted baseline RoBERTa_BASE+SYNTH: KILE AP 0.539, F1 0.664; LIR micro-F1 0.698, AP 0.583. LayoutLMv3_BASE (IIT-CDIP pre-trained, excluded from ranking) KILE F1 0.698 / AP 0.553; LIR F1 0.721. DETR-table + DETR-LineItem + RoBERTa_BASE LIR F1 only 0.594. "NER upper bound" KILE F1 0.946, LIR F1 0.961. Matching requires correct localization (pseudo-character-centre criterion) and for LIR assignment to the correct line item. No per-field breakdown reported. — [arXiv HTML](https://arxiv.org/html/2302.05658)

**GPT-4o on DocILE fields (from a calibration paper)**
- "Beyond Logprobs: A Multi-Signal Confidence Engine for LLM-Based Document Field Extraction", Nitesh Kumar (Perfios), arXiv:2606.24420 (v1, 23 Jun 2026); extended version of an oral at RobustifAI Workshop, IJCAI-ECAI 2026. GPT-4o (temp 0, AWS Textract OCR) on a DocILE subset of 1,339 fields (1,072 train / 267 test): positive (correct) rate 73.4%, i.e. ~26.6% of extracted fields wrong (paper also says 73.3% elsewhere). Zero-shot on CORD (828 field samples, 30 fields): 88.6% correct. No per-field-type error rates (amounts/dates/totals) reported. — [arXiv HTML](https://arxiv.org/html/2606.24420)

**VRDU (Google, KDD 2023)**
- "VRDU: A Benchmark for Visually-rich Document Understanding", Zilong Wang, Yichao Zhou, Wei Wei, Chen-Yu Lee, Sandeep Tata; KDD 2023; arXiv:2211.15421. Abstract findings: generalizing to new templates is still very challenging, few-shot performance has substantial room for improvement, and models struggle with hierarchical fields "such as line-items in an invoice". (F1 numbers are in the full paper, not retrieved.) — [arXiv abs](https://arxiv.org/abs/2211.15421)

**GPT-4V OCR/KIE evaluation (2023)**
- "Exploring OCR Capabilities of GPT-4V(ision): A Quantitative and In-depth Evaluation", Yongxin Shi et al. (Lianwen Jin group), arXiv:2310.16809 (Oct 2023; no venue on arXiv page). — [arXiv abs](https://arxiv.org/abs/2310.16809)
- GPT-4V semantic entity recognition: FUNSD F1 34.51% (P 41.85, R 29.36, 1-NED 0.2697 vs supervised SOTA StrucTexTv2 1-NED 0.5500); XFUND-zh F1 19.11%. Pair extraction: FUNSD F1 13.71%; XFUND-zh F1 0.03%. Table structure recognition (TEDS-S, structure only): SciTSR 87.47% vs SOTA 99.19%; WTW 25.60% vs SOTA 91.91%. SROIE/CORD were not evaluated in the paper. — [arXiv HTML](https://arxiv.org/html/2310.16809)

**OCR-free models (Donut)**
- "OCR-free Document Understanding Transformer" (Donut), Geewook Kim et al., ECCV 2022, arXiv:2111.15664. Official repo lists CORD TED-based accuracy 91.3 / 91.1 / 90.9 across released checkpoints; secondary summaries give Donut CORD field-level F1 84.1 and tree accuracy 90.9 vs LayoutLMv2 78.9 F1 / 82.4 **[snippet only; numbers vary across arXiv vs ECCV versions — the ECCV PDF is reported in a snippet to give 93.6 accuracy at 1280×960 while arXiv gives 91.1]**. — [GitHub clovaai/donut](https://github.com/clovaai/donut); [ECCV PDF](https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136880493.pdf); [arXiv](https://arxiv.org/pdf/2111.15664)
- Donut pre-training used 11M scans pseudo-labelled by a commercial OCR engine, so "OCR-free" inference still depends on OCR-derived supervision **[snippet only]**. — [arXiv](https://arxiv.org/pdf/2111.15664)
- Interpretation caveat: on CORD, a gap between field-level exact-match F1 (~84) and TED accuracy (~91) means roughly 1 in 6 fields is not exactly right even when the tree is mostly correct **[derived from snippet numbers]**.

**Long financial documents / financial QA**
- MMLongBench-Doc: "MMLongBench-Doc: Benchmarking Long-context Document Understanding with Visualizations", Yubo Ma et al., NeurIPS 2024 Datasets & Benchmarks (Spotlight), arXiv:2407.01523. arXiv abstract (v3): 130 PDFs, 1,062 questions, 22.8% unanswerable; best model GPT-4o F1 42.7%, GPT-4V 31.4%; 12 of 14 LVLMs did worse than their LLM counterparts given lossy OCR-parsed text. — [arXiv abs](https://arxiv.org/abs/2407.01523). **Conflict:** the NeurIPS proceedings version reportedly gives GPT-4o F1 44.9% and GPT-4V 30.5%, with 223 unanswerable questions (20.6%) **[snippet only]** — [NeurIPS PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/ae0e43289bffea0c1fa34633fc608e92-Paper-Datasets_and_Benchmarks_Track.pdf). A later "MMLongBench-Doc-V2" (arXiv:2608.03397) claims annotation corrections and that the metric measures string identity rather than correctness **[snippet only]** — [arXiv](https://arxiv.org/pdf/2608.03397)
- FinanceBench: "FinanceBench: A New Benchmark for Financial Question Answering", Pranab Islam et al., arXiv:2311.11944 (Nov 2023). GPT-4-Turbo with a shared vector store "incorrectly answered or refused to answer 81% of questions" (16 configurations, 150-case sample, 2,400 answers manually reviewed); all models showed hallucinations. — [arXiv abs](https://arxiv.org/abs/2311.11944)
- TAT-DQA: "Towards Complex Document Understanding By Discrete Reasoning", Fengbin Zhu et al., ACM MM 2022, arXiv:2207.11871; answer types include arithmetic, counting, span, multi-span. — [arXiv](https://arxiv.org/pdf/2207.11871)
- TAT-LLM (Zhu et al., "TAT-LLM: A Specialized Language Model for Discrete Reasoning over Tabular and Textual Data", ICAIF 2024, arXiv:2401.13223) claims to beat GPT-4 on FinQA, TAT-QA and TAT-DQA (verified from abstract). Reported EM for TAT-LLM: FinQA 64.60, TAT-QA 74.56, TAT-DQA 69.45; GPT-4 on TAT-DQA 64.46 EM / 72.20 F1; GPT-3.5-Turbo 52.74 EM / 61.40 F1 **[numbers snippet only; text-only LLMs on OCR text, not MLLMs]**. — [arXiv abs](https://arxiv.org/abs/2401.13223); [ACM](https://dl.acm.org/doi/fullHtml/10.1145/3677052.3698685)

**Industry / non-peer-reviewed invoice tests (anecdotal)**
- A HackerNoon test reports GPT-4o ~86.5% on invoices with line items and 38.5% on tables, Gemini 1.5 Pro 94.2% on tables **[snippet only; blog, methodology unknown]**. — [HackerNoon](https://hackernoon.com/can-your-llm-handle-an-invoice-i-tested-5heres-the-truth)
- Businessware Technologies blog found Gemini strongest on line-item detail and GPT-4o occasionally inaccurate on numbers **[snippet only; vendor blog]**. — [Businessware](https://www.businesswaretech.com/blog/research-ai-models-invoice-processing-benchmark)

### Inferences
- Header fields (vendor, date, total) are relatively easy (ReceiptBench normalization/reasoning ≥0.87 F1 for frontier models), while the share of errors concentrates in nested line items (0.49–0.58 F1) — i.e., the exact place where sum checks (Σ line items = subtotal) can catch errors.
- The ~26% GPT-4o field error rate on DocILE and 11.4% on CORD fields suggests error rates on real invoices are 2–3× those on clean receipt benchmarks; numbers on CORD/SROIE overstate production accuracy.
- MMLongBench-Doc's finding that most LVLMs do worse than LLMs fed OCR text supports a pipeline in which OCR text plus symbolic checks is not obviously inferior to end-to-end MLLMs.

### Gaps
- No verified per-field (e.g. CORD `total.total_price`, `sub_total.tax_price`) MLLM error breakdown was found; SROIE/CORD per-field results for GPT-4o/Gemini/Claude/Qwen-VL/InternVL were not located in a primary source.
- Pix2Struct, InternVL, Qwen2/2.5-VL KIE numbers on CORD/SROIE not retrieved (time budget).
- Kleister-Charity / Kleister-NDA (Stanisławek et al., ICDAR 2021) **[background]** not researched; no 2022–2026 LLM results on them were retrieved.
- VRDU per-field F1 (Registration Forms / Ad-buy Forms) not retrieved from the full paper.
- MLLM-specific (image-input) TAT-DQA numbers were not found.

## Q2. Documented hallucination behaviour in document understanding

### Takeaway
Primary sources document a consistent taxonomy: (1) schema-pressure fabrication (inventing an invoice number or fields that are not on the page), (2) "arithmetic-motivated" hallucination where models alter a line-item price or invent a Tax line to make items reconcile with the total, (3) self-computing a missing total with calculation errors, (4) digit confusions (1/7) and date-component swaps (day/month, wrong day), (5) currency/location over-inference ("$" → USD, "£" → London), (6) omission of rows in long tables, and (7) in long documents, "hallucinated evidence" is the single largest error class (33% of GPT-4o errors on MMLongBench-Doc). Dedicated hallucination benchmarks for invoice values are scarce; most MLLM hallucination benchmarks target natural-image objects.

### Cited Findings
- ReceiptBench error analysis (fine-tuned Qwen3-VL-4B vs Gemini-3-Pro): when no unique ID is present Gemini "fabricates a plausible string for invoice_number to satisfy the schema"; Gemini 516 hallucination errors vs 248 for Qwen. — [arXiv HTML](https://arxiv.org/html/2605.22413v1)
- ReceiptBench: models "occasionally alter the price of a line item" so line items match `std_total`, and hallucinate a non-existent "Tax" item (attributed particularly to Gemini). — [arXiv HTML](https://arxiv.org/html/2605.22413v1)
- ReceiptBench: when the total is not visible, models sum the line items themselves, leading to calculation errors. — [arXiv HTML](https://arxiv.org/html/2605.22413v1)
- ReceiptBench: Qwen misidentifies confusable digits (e.g. "1"/"7") in `invoice_number`, one of the most error-prone fields for both models; ambiguous dates such as "02/03/24" cause day/month swaps. — [arXiv HTML](https://arxiv.org/html/2605.22413v1)
- ReceiptBench: Gemini infers a city from a currency symbol ("London" from "£"), defaults ambiguous "$" to USD; 241 `std_curr` errors for Gemini vs 58 for Qwen. — [arXiv HTML](https://arxiv.org/html/2605.22413v1)
- GPT-4V (Shi et al. 2023): FUNSD example where a header "09 / 17 / 97 10:55" was returned as date 09/18/97 and non-existent fields (Fax Number, Company, Page Number) were invented; GPT-4V "tends to generate new keys for non-kv-pair contents"; reconstructed only three rows of a large table despite being told not to omit; "significant hallucinations in Chinese text recognition" (fluent but unrelated output). — [arXiv HTML](https://arxiv.org/html/2310.16809)
- MMLongBench-Doc error analysis (GPT-4o): Hallucinated Evidence 33%, Perceptual Error 28%, Irrelevant Answer 11%, Incomplete Evidence 10%; GPT-4o and Claude-3 Opus described as "aggressive" on unanswerable questions (often answering incorrectly) while Gemini-1.5-Pro and DeepSeek-VL-Chat were "cautious" **[snippet only, from NeurIPS version]**. — [NeurIPS PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/ae0e43289bffea0c1fa34633fc608e92-Paper-Datasets_and_Benchmarks_Track.pdf); [arXiv abs](https://arxiv.org/abs/2407.01523)
- FinanceBench: all evaluated models "exhibit weaknesses, such as hallucinations". — [arXiv abs](https://arxiv.org/abs/2311.11944)
- GPT4o-Receipt ("GPT4o-Receipt: A Dataset and Human Study for AI-Generated Document Forensics", Yan Zhang et al., arXiv:2603.11442, v1 12 Mar 2026, v3 24 Oct 2026; preprint): the dominant forensic signal in GPT-4o-*generated* receipts is arithmetic errors (subtotals not reconciling), invisible to visual inspection but systematically checkable by LLMs; human detection F1 falls well below Claude Sonnet 4 and Gemini 2.5 Flash. Snippet-level numbers: Claude Sonnet 4 F1 0.975, Gemini 2.5 Flash 0.890, Gemini flags sum errors 85.9% and tax errors 78.2% **[those numbers snippet only]**. Relevance: shows image-generating MLLMs do not maintain arithmetic consistency, and that arithmetic checks are a strong signal. — [arXiv abs](https://arxiv.org/abs/2603.11442)
- Neurosymbolic IE (Hemmer et al., see Q3) lists four causes of constraint failure: parsing, schema limits, readability, incorrect arithmetic (no counts per cause). — [arXiv HTML](https://arxiv.org/html/2512.09666)
- General MLLM hallucination benchmarks (POPE, HallusionBench, MMHal-Bench, Bingo, VHTest) mostly target object hallucination rather than document/table value fabrication. — [Survey, arXiv:2404.18930](https://arxiv.org/pdf/2404.18930); [Benchmark survey, arXiv:2408.08632](https://arxiv.org/pdf/2408.08632)
- Candidate table/chart grounding benchmarks found but not opened: ViTaB-A (visual table attribution, arXiv:2602.15769), MMTabReal (arXiv:2505.21771), ChartCap (chart caption hallucination) **[titles only]**. — [ViTaB-A](https://arxiv.org/pdf/2602.15769); [MMTabReal](https://arxiv.org/pdf/2505.21771)

### Inferences
- The "alter a line-item price / invent a Tax line to reconcile" failure is important for verifier design: an MLLM can produce output that *passes* a naive sum check while being wrong. A sum check must therefore be paired with grounding (value must be present in OCR tokens / located on the page), not used alone.
- Schema-pressure fabrication (invoice_number invented when absent) argues for explicit "absent/null" handling and abstention in the schema rather than required fields.
- Digit confusions (1/7) and day/month swaps are exactly the error classes that checksum-style and format validators (ID check digits, date plausibility, cross-field date ordering) can catch.

### Gaps
- No primary source quantified unit/currency errors in financial statements, or misaligned table rows (row-shift) rates, for MLLMs.
- No dedicated document-value hallucination benchmark (fabricated numbers on DocVQA/ChartQA/TAT-DQA) was confirmed; ChartQA/DocVQA hallucination-specific studies were not retrieved.
- OCR-error propagation in OCR→LLM pipelines: only indirect evidence (ExtractConf finds OCR-quality features are strong error predictors, see Q5); no controlled propagation study retrieved.

## Q3. How papers enforce or measure numerical consistency

### Takeaway
Three families: (a) **post-hoc symbolic validation** of extracted fields against arithmetic constraints (subtotal = Σ line items, gross = net + tax, tax-rate range), used as a filter, a confidence channel, or to select distillation labels (Hemmer et al., IJDAR 2025); (b) **training-time consistency rewards** (ReceiptBench's metric-aware GRPO with an arithmetic consistency reward); (c) **offloading arithmetic to an executor** (Program-of-Thoughts, TAT-LLM's Extractor–Reasoner–Executor) for QA over financial tables. The strongest quantitative evidence (Hemmer et al.) shows domain-level arithmetic validation removes 56–88% of zero-shot LLM extractions on CORD/SROIE but raises F1 on what remains by ~4–13 points.

### Cited Findings
- "Neurosymbolic Information Extraction from Transactional Documents", Arthur Hemmer, Mickaël Coustaty, Nicola Bartolo, Jean-Marc Ogier; IJDAR 28, 475–485 (2025) (ICDAR 2025 journal track); arXiv:2512.09666. LLMs generate candidates; filtered by syntactic, task-level and domain-level validation; domain constraints: subtotal = Σ line items; gross total = net total + taxes; base taxable amount = Σ line-item net totals; 0.5% relative tolerance; ≥1 line item; gross or net total present; tax rate in [0,1]. — [arXiv abs](https://arxiv.org/abs/2512.09666); [arXiv HTML](https://arxiv.org/html/2512.09666)
- Hemmer et al. zero-shot (Table 1; % documents remaining → F1): CORD_TD Ministral-8B 100% → 60.0 (base), 76% → 65.0 (task), 25% → 69.3 (domain); CORD_TD Pixtral-12B 100% → 69.0, 83% → 70.3, 44% → 74.0; SROIE_TD Ministral-8B 100% → 39.4, 41% → 48.1, 11.7% → 52.7; SROIE_TD Pixtral-12B 100% → 40.5, 55.7% → 42.9, 19.9% → 45.4. Document-level exact accuracy was 0–4.5% zero-shot. — [arXiv HTML](https://arxiv.org/html/2512.09666)
- Hemmer et al.: only 28–49% of zero-shot outputs were domain-valid at base (CORD_TD Ministral 28.0%, Pixtral 49.0%; SROIE_TD 25.0%, 26.8%). — [arXiv HTML](https://arxiv.org/html/2512.09666)
- Hemmer et al., fine-tuned Ministral-8B upper bound: CORD_TD base F1 95.7 / doc-acc 74.0 → domain-filtered F1 98.1 / doc-acc 83.5 at 85% retention; SROIE_TD 80.6 → 90.6 F1 at 46.4% retention. — [arXiv HTML](https://arxiv.org/html/2512.09666)
- Hemmer et al., sampling (Pixtral-12B): drawing 16 samples and keeping valid ones raises domain-filter retention from 44.0% to 83.0% (CORD_TD) and 19.9% to 51.2% (SROIE_TD), but base F1 of individual samples falls (69.0 → 57.3; 40.5 → 16.7). — [arXiv HTML](https://arxiv.org/html/2512.09666)
- Hemmer et al., distillation with domain-validated labels beats unfiltered labels: CORD_TD Ministral-8B 69.7 → 77.4 F1; SROIE_TD Qwen-2.5-14B 43.9 → 46.2. — [arXiv HTML](https://arxiv.org/html/2512.09666)
- Hemmer et al.: even ground-truth annotations satisfy all constraints in only 96.5% (CORD_TD) and 95.5% (SROIE_TD) of documents — i.e. 3.5–4.5% of real documents are not internally consistent (or the schema cannot express them). — [arXiv HTML](https://arxiv.org/html/2512.09666)
- ReceiptBench: two-stage training (SFT then Metric-Aware GRPO) aimed at "structural consistency"; search snippet describes an arithmetic-consistency reward in GRPO **[reward detail snippet only]**. — [arXiv abs](https://arxiv.org/abs/2605.22413)
- "Program of Thoughts Prompting: Disentangling Computation from Reasoning for Numerical Reasoning Tasks", Wenhu Chen, Xueguang Ma, Xinyi Wang, William W. Cohen; TMLR 2023; arXiv:2211.12588: ~12% average gain over CoT across evaluated datasets; PoT + self-consistency reaches near-SoTA on financial datasets (FinQA, ConvFinQA, TAT-QA). — [arXiv abs](https://arxiv.org/abs/2211.12588)
- TAT-LLM (ICAIF 2024): Extractor → Reasoner → Executor step-wise pipeline, used to prompt GPT-4 and to fine-tune LLaMA-2. — [arXiv abs](https://arxiv.org/abs/2401.13223)
- "Perception, Layout, and Validation: Calibrated Confidence for Reliable Straight-Through Processing of Financial Documents", Yichao Jin et al., arXiv:2609.20110 (17 Sep 2026; preprint): uses a "validation" channel as one of three confidence components (see Q5); search snippet says the extraction prompt defines gross = net + tax **[snippet only]**. — [arXiv abs](https://arxiv.org/abs/2609.20110)
- "Automated Invoice Data Extraction: Using LLM and OCR", Khanchandani et al., arXiv:2511.05547: describes a validation layer reconciling item totals, subtotal, tax (against stated rate) and grand total **[snippet only]**. — [arXiv](https://arxiv.org/pdf/2511.05547)
- "Information Extraction From Fiscal Documents Using LLMs", Vikram Aggarwal et al., arXiv:2511.10659 (ACM ICAIF 2025 workshop): uses hierarchical totals in Karnataka state fiscal tables for multi-level validation without ground truth. A search snippet claimed an 84% pass rate across seven volumes; this was **not** found on the abstract page. — [arXiv abs](https://arxiv.org/abs/2511.10659)
- Self-consistency as a confidence signal: on DocILE with GPT-4o, 5-call self-consistency gives ROC AUC 0.744 vs logprob-mean 0.705 (see Q5). — [arXiv HTML](https://arxiv.org/html/2606.24420)

### Inferences
- Arithmetic validation behaves as a high-precision, low-coverage filter on zero-shot LLM output: large F1 gains on the retained subset but most documents get rejected — consistent with using it as an abstention/routing signal rather than a correction mechanism.
- Because ~4% of genuine documents fail strict constraints, a verifier needs tolerance (Hemmer: 0.5% relative) and a "constraint not evaluable / document inconsistent" outcome distinct from "extraction wrong".
- Sampling + validity filtering (Hemmer) is a cheap self-consistency variant: it raises the share of documents with a valid parse without changing the model.

### Gaps
- No paper found measuring how often MLLM outputs violate Σ line items = subtotal on a standard benchmark *before* filtering, broken down by model (Hemmer reports only domain-valid rates for two small open models).
- No retrieved study of verification prompts ("check your arithmetic") vs external code checks for invoice extraction with numbers.
- No Vietnamese-invoice-specific (VAT 0/5/8/10%) consistency study found.

## Q4. Industry / benchmark reports on invoice extraction accuracy

### Takeaway
Public invoice benchmarks with primary-source numbers in 2022–2026 are DocILE (supervised baselines ≤0.70 F1 KILE, ≤0.72 LIR), VRDU (line items and unseen templates hardest), and ReceiptBench (frontier MLLMs 0.71–0.74 overall F1). Industry reports are mostly vendor blogs without reproducible methodology.

### Cited Findings
- DocILE baselines and matching protocol: see Q1. — [arXiv HTML](https://arxiv.org/html/2302.05658)
- VRDU qualitative findings: see Q1. — [arXiv abs](https://arxiv.org/abs/2211.15421)
- ReceiptBench: see Q1–Q2. — [arXiv HTML](https://arxiv.org/html/2605.22413v1)
- "Better Bill GPT: Comparing Large Language Models against Legal Invoice Reviewers" (arXiv:2504.02881): about compliance review of legal invoices, not extraction; line-item classification F-score Gemini 2.0 Flash Thinking 0.806 vs GPT-4o 0.631 **[snippet only]**. — [arXiv HTML](https://arxiv.org/html/2504.02881v1)
- "Robustness of Structured Data Extraction from Perspectively Distorted Documents" (arXiv:2511.17607) found in search, not opened **[title only]**. — [arXiv](https://arxiv.org/pdf/2511.17607)
- Vendor/blog tests (HackerNoon, Businessware) — anecdotal; see Q1.

### Inferences
- Benchmarks reporting both header-field and line-item accuracy consistently show line items as the weakest part, so any reported "invoice accuracy" headline number without a line-item breakdown should be treated as optimistic.

### Gaps
- DocILE competition (ICDAR 2023) winning-team results and any LLM results on the official DocILE leaderboard were not retrieved.
- Kleister-Charity/NDA LLM-era results not retrieved.
- No independent, peer-reviewed industry-scale invoice accuracy report (e.g. from AP-automation vendors) was found.

## Q5. Calibration / confidence estimation for extracted fields

### Takeaway
2026 work shows native MLLM confidence is poorly suited to field-level routing: GPT-4o logprob-mean gives ROC AUC 0.705 and verbalized confidence 0.692 on DocILE; VLM verbalized confidence gives AUROC 0.54–0.74 and under conformal risk control can auto-approve only 0.1–7.0% of fields. Multi-signal confidence (OCR quality, layout, validation/arithmetic checks) raises AUROC to 0.90–0.99 and auto-approves 49–72% of fields at a bounded error target.

### Cited Findings
- ExtractConf (Kumar, arXiv:2606.24420, IJCAI-ECAI 2026 RobustifAI workshop), DocILE test, GPT-4o: ROC AUC / AURC / ECE — logprob mean 0.705 / 0.145 / 0.245; verbalized 0.692 / 0.146 / 0.163; self-consistency (5 calls) 0.744 / 0.138 / 0.075; logprobs+entropy 0.880 / 0.076 / 0.180; OCR features only 0.896 / 0.079 / 0.197; full ExtractConf (gradient-boosted meta-classifier over LLM uncertainty, document quality, spatial layout) 0.928 / 0.043 / 0.199; + isotonic 0.926 / 0.044 / 0.034. 70% AURC reduction vs logprob mean; 99.1% accuracy in top band at 80% coverage vs 73.3% base rate. CORD zero-shot transfer AUC 0.858 (ECE 0.237 → 0.025 after Lasso recalibration). Numeric fields reported as well calibrated; free-text fields overconfident at high probability. Minor internal inconsistency: conclusion cites AURC 0.042 (that is M8, not M6). — [arXiv HTML](https://arxiv.org/html/2606.24420)
- Jin et al., arXiv:2609.20110 (preprint, Sep 2026): perception + layout + validation confidence channels, then conformal risk control for straight-through processing; three public datasets (real invoices, synthetic invoices, ad-buy forms); models Qwen3.6-27B and Gemini-3.1-Flash-Lite. AUROC 0.54–0.74 (VLM verbalized) → 0.90–0.99 (decomposed); native confidence under <10% error target clears only 0.1–7.0% of fields; proposed method auto-approves 49–72% with accepted-tier empirical error ≤ target. — [arXiv abs](https://arxiv.org/abs/2609.20110)
- Related work cited by ExtractConf (not independently verified): HYCEDIS (Nguyen et al., multi-signal KIE confidence); Rombach & Mehdiyev, IJDAR 2026, conformal prediction for KIE confidence; Hemmer et al. 2024 ConfBERT (confidence-aware OCR error detection); Jagannatha & Yu, ACL 2020 **[background]** calibration of structured-output predictors; Geifman & El-Yaniv **[background]** selective prediction. — [arXiv HTML](https://arxiv.org/html/2606.24420)
- MMLongBench-Doc: model abstention style differs ("aggressive" GPT-4o/Claude-3 Opus vs "cautious" Gemini-1.5-Pro) **[snippet only]**. — [NeurIPS PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/ae0e43289bffea0c1fa34633fc608e92-Paper-Datasets_and_Benchmarks_Track.pdf)
- General LLM calibration: post-trained models tend to be more overconfident than base models (BaseCal, arXiv:2601.03042) **[snippet only]**. — [arXiv](https://arxiv.org/pdf/2601.03042)

### Inferences
- Both 2026 papers independently find that signals external to the generator (OCR quality, layout, validation rules) carry most of the predictive power for "is this field wrong" — consistent with a neuro-symbolic design where symbolic checks feed a selective-prediction / conformal routing layer.
- Self-consistency alone (AUC 0.744) is a weak error detector for invoice fields, and costs 5× calls.

### Gaps
- Rombach & Mehdiyev (IJDAR 2026) conformal KIE paper and HYCEDIS were not opened; exact titles/venues unverified.
- No per-field-type (amount vs date vs ID) calibration numbers found.
- Neither 2026 calibration paper's ablation of the validation (arithmetic) channel alone was retrieved; its marginal contribution is not quantified here.
