# Open challenges in processing noisy, real-world, multi-page financial documents with complex nested tables (2022–2026)

Scope note: I checked every citation below against its arXiv abstract or HTML page, ACL Anthology, a project page, or a repository copy during this session. Where the only source for a number is a secondary page (a model card, a project page or a search snippet), I say so. Venue fields give only what the source page states. A paper with no venue on its page is listed as an "arXiv preprint".

## 1. Multi-page and long-document understanding: how performance drops with page count, and what helps

### Takeaway
As documents get longer, scores fall sharply. On short multi-page sets (MP-DocVQA, 1–20 pages), ANLS is about 0.84. On MMLongBench-Doc (about 49 pages per document) the best model reaches only 42.7 F1, and on LongDocURL (about 86 pages) the best reaches 64.5 while the best open model reaches 30.6. Retrieving pages with a visual retriever (ColPali + Qwen2-VL, as in M3DocRAG) gives large gains on short multi-page sets and open-domain corpora. On genuinely long documents it still leaves accuracy around 21–23.

### Cited Findings
- **MP-DocVQA / Hi-VT5.** Tito, Karatzas, Valveny, "Hierarchical multimodal transformers for Multi-Page DocVQA", arXiv:2212.05935 (v1 Dec 2022, v2 Apr 2023). The arXiv page lists no venue. The method also predicts which page holds the answer, and the authors offer this as an explainability signal. — [arXiv:2212.05935](https://arxiv.org/abs/2212.05935)
  - MP-DocVQA asks questions over documents of 1–20 pages. Hi-VT5 reaches ANLS 0.6201 and answer-page identification accuracy 79.23%, per the authors' Hugging Face model card (secondary source). — [HF model card rubentito/hivt5-base-mpdocvqa](https://huggingface.co/rubentito/hivt5-base-mpdocvqa)
- **DUDE.** Van Landeghem et al., "Document Understanding Dataset and Evaluation (DUDE)", ICCV 2023, arXiv:2305.08455. It is a benchmark over multi-page, visually rich documents. The abstract reports no scores. — [arXiv:2305.08455](https://arxiv.org/abs/2305.08455)
- **MMLongBench-Doc.** Ma et al., "MMLongBench-Doc: Benchmarking Long-context Document Understanding with Visualizations", NeurIPS 2024 Datasets & Benchmarks (Spotlight), arXiv:2407.01523. — [arXiv:2407.01523](https://arxiv.org/abs/2407.01523)
  - The benchmark has 1,062 expert-annotated questions over 130 PDFs, averaging 49.4 pages and 20,971 text tokens. 22.8% of the questions are unanswerable.
  - The best model is GPT-4o at **42.7% F1**, followed by GPT-4V at 31.4%.
  - Of 14 LVLMs, **12 scored worse than their text-only LLM counterparts given lossy OCR-parsed text**. Current LVLMs therefore do not use page images well at long context lengths.
- **LongDocURL.** Deng et al., "LongDocURL: a Comprehensive Multimodal Long Document Benchmark Integrating Understanding, Reasoning, and Locating", arXiv:2412.18424 (v3 Jul 2025; the arXiv page gives no venue). — [arXiv:2412.18424](https://arxiv.org/abs/2412.18424); [HTML v3](https://arxiv.org/html/2412.18424v3)
  - It covers 396 documents, on average **85.6 pages** each (over 33,000 pages in total), with 2,325 QA pairs and 20 sub-tasks. The authors evaluated 26 model configurations.
  - GPT-4o scores highest at **64.5**. The best open-source model (Qwen2-VL) reaches only **30.6**.
  - **Table questions get the lowest scores** of all evidence types. The authors call this a sign of "deficiencies in document structure parsing".
  - With text input (PyMuPDF parse), the best LLM trails the best LVLM by about 30 points. GPT-4o loses 31.6 points on reasoning and 22.4 on locating when given text instead of images.
  - GPT-4o and Qwen-VL-Max score lower on multi-page *locating* questions than on single-page ones.
- **M3DocRAG.** Cho et al., "M3DocRAG: Multi-modal Retrieval is What You Need for Multi-page Multi-document Understanding", arXiv:2411.04952 (the page gives no venue). It also introduces M3DocVQA, an open-domain set of more than 3,000 PDFs and more than 40,000 pages. — [arXiv:2411.04952](https://arxiv.org/abs/2411.04952); [HTML](https://arxiv.org/html/2411.04952)
  - On MP-DocVQA (test), M3DocRAG (ColPali + Qwen2-VL 7B) reaches **ANLS 0.8444** and R@1 81.05. Prior systems score: Arctic-TILT 0.8122, GRAM 0.8032, ScreenAI 5B 0.7711, and text RAG (ColBERT v2 + Llama 3.1 8B) 0.5603.
  - On MMLongBench-Doc with 4 retrieved pages, M3DocRAG gets **21.0 accuracy / 22.6 F1** and text RAG gets 23.5 / 19.7. The best non-RAG multimodal entry, InternLM-XC2-4KHD fed up to 120 pages, gets 10.3 / 9.8.
  - On M3DocVQA (open-domain) at 4 pages, M3DocRAG reaches 31.4 EM / 36.5 F1, against 17.8 / 23.7 for text RAG.
  - Retrieving more pages helps. On M3DocVQA, F1 goes from 32.3 with 1 page to 36.5 with 4. On MMLongBench-Doc, accuracy goes from 18.8 to 21.0.
  - Approximate indexing trades accuracy for speed. At 1 page, exact FlatIP gives 33.7 F1 at 21.0 s, IVFFlat 32.3 F1 at 1.8 s, and IVFPQ 30.3 F1 at 0.2 s.
- **ColPali.** Faysse et al., "ColPali: Efficient Document Retrieval with Vision Language Models", ICLR 2025, arXiv:2407.01449. It introduces the ViDoRe visual-document retrieval benchmark. The abstract reports no numbers. — [arXiv:2407.01449](https://arxiv.org/abs/2407.01449)

### Inferences
- A rough length scale emerges: about 0.84 ANLS at ≤20 pages, about 42.7 F1 at ~49 pages, and 64.5 for the best closed model (30.6 open) at ~86 pages. These are different metrics and question mixes, so this is a trend rather than a controlled curve.
- In M3DocRAG, retrieval accounts for most of the gain on MP-DocVQA: text RAG reaches 0.56 ANLS against 0.84 with visual retrieval. On MMLongBench-Doc, however, accuracy and F1 stay near 21–23. The bottleneck there is reasoning that combines evidence from many pages, not finding the page.
- Financial dossiers (annual reports, multi-page invoices, statements) are long and full of tables. Table-evidence questions are the weakest category in LongDocURL, so this is the most exposed sub-area.

### Gaps
- I found no controlled curve of accuracy against total page count for MP-DocVQA. The paper reports ANLS by answer-page position, but I could not get the figure's values.
- I did not verify DocBench (arXiv:2407.10701) or SlideVQA (arXiv:2301.04883, AAAI 2023) numbers this session, so they are left out.
- I did not separately verify DUDE leaderboard numbers or the calibration and abstention metrics DUDE may report.
- LongDocURL's venue (possibly ACL 2025) is unconfirmed; the arXiv page states none.

## 2. Table structure recognition for complex and nested tables

### Takeaway
Structure recognition on *cropped* tables is close to saturated: S-TEDS is about 97–99 on FinTabNet and PubTabNet. The hard part has moved to page-level and multi-page extraction, exact content match, and tables split across pages. PubTables-v2 is the first large benchmark for these. On it, small page-by-page models collapse on multi-page tables (GriTS_Con 0.577) while frontier models with full-document context reach about 0.93.

### Cited Findings
- **UniTable.** Peng et al., "UniTable: Towards a Unified Framework for Table Recognition via Self-Supervised Pretraining", arXiv:2403.04822 (the page gives no venue). It claims SOTA on four large table-recognition datasets. — [arXiv:2403.04822](https://arxiv.org/abs/2403.04822); [HTML v2](https://arxiv.org/html/2403.04822v2)
  - On PubTabNet (TEDS / S-TEDS): EDD 88.30 / 89.90, TableFormer 93.60 / 96.75, VAST 96.31 / 97.23, UniTable-Large **96.50 / 97.89**.
  - On FinTabNet (S-TEDS): GTE 91.02, TableFormer 96.80, VAST 98.63, UniTable-Large **98.89**.
  - On PubTables-1M (cell-detection AP50), DETR's 97.10 beats UniTable-Large's 95.68.
  - On SynthTabNet subsets (500 samples), GPT-4V scores about 57–70 S-TEDS, the best LLaVA-v1.6 variant about 41–50, and UniTable-Large about 99.1–99.6. GPT-4V "tends to omit content in large tables" and does worse on spanning and empty cells.
  - 53.10% of PubTables-1M training tables have at least one word box outside the image bounds, which means annotation noise affects evaluation.
- **PubTables-v2.** Smock et al., "PubTables-v2: A new large-scale dataset for full-page and multi-page table extraction", arXiv:2512.10888. The arXiv comments field says it was accepted to WACV 2027. — [arXiv:2512.10888](https://arxiv.org/abs/2512.10888); [HTML v3](https://arxiv.org/html/2512.10888v3)
  - The dataset has three parts:
    - 135,578 long or wide cropped tables.
    - 467,541 single pages containing 548,414 tables.
    - 9,172 full documents (137,095 pages) with **9,492 multi-page tables**, some running to 13 pages; over 200 span 5 or more pages.
  - The authors know of no earlier published dataset with structure annotations for multi-page tables.
  - **Cropped tables (GriTS_Con):** TATR-v1.2-Pub with direct text 0.980, TATR with docTR OCR 0.929, Gemini 3.1 Pro 0.924, dots.ocr 0.801, SmolDocling-256M 0.192.
  - **Page level:** POTATR (a 29M-parameter image-to-graph extension of TATR) with direct text 0.964, Gemini 3.1 Pro 0.942, POTATR with docTR 0.880.
  - **Full document, multi-page:** Gemini 3.1 Pro 0.931 and Claude Opus 4.6 0.908, both with full context. dots.ocr page-by-page reaches 0.577, and **0.684 with cross-page merging**. A ViT classifier predicts whether a table continues onto the next page at F1 0.991.
  - The abstract puts the frontier-over-small-model gap at +0.354 GriTS_Con on full-document multi-page extraction. On cropped tables, targeted training reverses the gap to −0.056.
  - **Open problems:**
    - No model fully recovers a single-page split table; exact match with content is 0 for all models.
    - Exact full-table match with content stays low even for frontier models, about 0.1–0.37 on cropped tables.
    - Models over- or under-count the tables on a page.
    - At page level, POTATR's remaining error comes mostly from OCR text quality.

### Inferences
- Structure metrics (TEDS, S-TEDS, GriTS) at 0.93–0.99 hide the fact that whole tables are rarely reproduced exactly. Audit work needs every cell value right, so exact table or cell match is the metric that matters, and it remains very low.
- OCR text quality is a large source of error. TATR loses 0.051 GriTS_Con on cropped tables when it uses docTR instead of embedded text (0.980 vs 0.929), and POTATR loses 0.084 at page level (0.964 vs 0.880). Scanned financial documents therefore lose accuracy even when the structure is right.

### Gaps
- I did not verify TableFormer's venue (CVPR 2022) or PubTables-1M / TATR's (CVPR 2022) from primary pages this session. TableFormer numbers above come from UniTable's comparison table.
- I did not retrieve results from the ICDAR 2019 cTDaR, ICDAR 2021 table-recognition or ICDAR 2023 competitions.
- I found no verified benchmark that isolates **borderless** or **nested-header** tables. PubTables-v2 does not single out borderless tables, and it annotates spanning cells without reporting them as a separate difficulty.
- I found no benchmark of financial tables in Vietnamese or another low-resource language.

## 3. Robustness to scan noise, blur, rotation, handwriting and capture conditions

### Takeaway
Clean-benchmark scores overstate real-world performance. GPT-4o loses an average of 35.3 points on photographed documents (WildDoc). RoDLA's 36-perturbation layout benchmarks show large robustness degradation across PubLayNet, DocLayNet and M6Doc.

### Cited Findings
- **WildDoc.** "WildDoc: How Far Are We from Achieving Comprehensive and Robust Document Understanding in the Wild?", EMNLP 2025 main conference (ACL Anthology 2025.emnlp-main.1172), arXiv:2505.11015, from ByteDance. — [ACL Anthology](https://aclanthology.org/2025.emnlp-main.1172); [arXiv:2505.11015](https://arxiv.org/abs/2505.11015v2); [project page](https://bytedance.github.io/WildDoc)
  - It contains over 12,000 document images. Each document is photographed four times, varying environment, illumination, view, distortion and effect.
  - The project page reports an **average 35.3-point drop for GPT-4o** compared with the scanned or digital counterparts in DocVQA, ChartQA and similar benchmarks.
  - The best consistency score is 50.6, from Doubao-1.5-pro. The authors read this as weak robustness.
- **RoDLA.** Chen et al., "RoDLA: Benchmarking the Robustness of Document Layout Analysis Models", CVPR 2024, arXiv:2403.14442. — [arXiv:2403.14442](https://arxiv.org/abs/2403.14442)
  - It defines a taxonomy of 36 document perturbations and builds PubLayNet-P, DocLayNet-P and M6Doc-P, 450K images in total.
  - The RoDLA model reaches mean Robustness Degradation (mRD) of 115.7, 135.4 and 150.4 on the three sets, and improves mAP over prior methods by +3.8, +7.1 and +12.1.
- **PubTables-v2** (see section 2) shows the effect of OCR noise: TATR drops from 0.980 to 0.929 GriTS_Con when it uses docTR OCR instead of embedded PDF text. — [HTML v3](https://arxiv.org/html/2512.10888v3)

### Inferences
- Mobile-captured invoices and receipts, a typical SME intake channel, fall squarely in the WildDoc setting. A drop of about 35 points means clean-benchmark accuracy cannot be used as a deployment estimate.
- On RoDLA's mRD, degradation is worst on M6Doc-P (150.4), the most heterogeneous source set. Diverse real-world layouts appear to compound the effect of perturbations.

### Gaps
- I verified no 2022–2026 benchmark that isolates **handwriting** in financial forms. The Vietnamese survey in section 4 reports handwriting CER/WER on other domains only.
- I verified no robustness benchmark specific to receipts or invoices with controlled noise levels, and no number for low-resolution degradation in KIE.
- I did not fetch the WildDoc per-model and per-factor tables, so the 35.3 figure comes from the project page rather than the paper's tables.

## 4. Low-resource and non-Latin, diacritic-heavy languages (focus on Vietnamese)

### Takeaway
Even the best general multimodal models read Vietnamese worse than English or Chinese: CC-OCR gives Vietnamese F1 of 78.5 for Gemini-1.5-Pro, 70.1 for GPT-4o and 64.4 for Qwen2-VL-72B. Vietnamese document resources are small and fragmented: a receipt VQA set (~9–9.5K images), MC-OCR 2021 receipts (~2K images), and OCR-VQA sets mostly built on book covers or scene text. A 2025 survey finds no specialized Vietnamese LLM for document analysis and no unified metrics.

### Cited Findings
- **CC-OCR.** Yang et al. (Alibaba), "CC-OCR: A Comprehensive and Challenging OCR Benchmark for Evaluating Large Multimodal Models in Literacy", arXiv:2412.02210, also listed on the CVF open-access site as ICCV 2025. — [arXiv HTML v3](https://arxiv.org/html/2412.02210v3); [CVF ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/html/Yang_CC-OCR_A_Comprehensive_and_Challenging_OCR_Benchmark_for_Evaluating_Large_ICCV_2025_paper.html)
  - It has 4 tracks, 39 subsets and 7,058 images. The multilingual track covers 10 languages, Vietnamese among them; each language has 10 real-shot document images and 140 scene images.
  - **Vietnamese** F1 (full-text multiset matching, word unit): Gemini-1.5-Pro 78.49, GPT-4o 70.11, Qwen2-VL-72B 64.37, Claude-3.5-Sonnet 59.58. Korean scores for the same models are 80.01, 74.20, 69.13 and 58.72; Arabic scores are 85.70, 72.31, 68.48 and 65.29.
  - The authors find most models weaker in other languages than in Chinese and English.
  - Best KIE-track score: Qwen2-VL-72B at 71.76 field-level F1. Best document-parsing score: Gemini-1.5-Pro at 62.37.
- **CC-OCR v2.** arXiv:2605.03903 covers 32 multilingual recognition subsets and 17 LMMs. Arabic degrades most consistently across model families, and aggregate multilingual scores hide language-specific weaknesses. I saw only snippets, not the full tables. — [arXiv:2605.03903](https://arxiv.org/pdf/2605.03903)
- **Vietnamese DAR survey.** Le et al., "A Survey on Vietnamese Document Analysis and Recognition: Challenges and Future Directions", arXiv:2506.05061 (June 2025, no venue). — [arXiv HTML](https://arxiv.org/html/2506.05061v1)
  - It names diacritics as a core OCR hazard: words such as "ma", "má" and "mà" differ only in tone marks.
  - It finds a lack of unified metrics and **no specialized Vietnamese LLM for document analysis**.
  - **MC-OCR 2021**, as the survey reports it:
    - About 2,000 mobile-captured receipts, with KIE fields SELLER, SELLER ADDRESS, TIMESTAMP and TOTAL COST.
    - Task 2 best CER was 0.22 (DataMining VC). Other teams scored SDSV AICR 0.23, UIT CS AIClub 0.30 and BK OCR 0.39.
    - Several teams used VietOCR; SDSV AICR used PaddleOCR for text detection.
  - **Other numbers the survey reports:**
    - ViOCRVQA: EM 0.4116, F1 0.6990.
    - Vietnamese ID cards: over 96.7% character-level and 89.7% word-level accuracy.
    - Handwritten tetanus medical records: CER 2%, WER 12%.
- **Vietnamese receipt VQA.** Le et al., "LiGT: Layout-infused Generative Transformer for Visual Question Answering on Vietnamese Receipts", arXiv:2502.19202. The arXiv comments field says it was accepted to IJDAR. — [arXiv:2502.19202](https://arxiv.org/abs/2502.19202)
  - The abstract describes a receipt VQA dataset of 9,000+ images and 60,000+ QA pairs. A search snippet gave 9,500 images and 64,812 pairs. The abstract reports no scores.
- **ViTextVQA**, arXiv:2404.10652, has 16,762 images and 50,342 QA pairs. **ViOCRVQA**, arXiv:2404.18397, has over 28,000 images and 120,000 QA pairs. — [arXiv:2404.10652](https://arxiv.org/abs/2404.10652); [arXiv:2404.18397](https://arxiv.org/abs/2404.18397v1)
- **Vintern-1B**, arXiv:2408.12480, is a Vietnamese MLLM built on InternVL-1.5 (Qwen2-0.5B + InternViT-300M). It was fine-tuned on over 3 million image-question-answer pairs, including a Viet-Receipt-VQA set. — [arXiv:2408.12480](https://arxiv.org/html/2408.12480v2)

### Inferences
- On CC-OCR, GPT-4o and Gemini-1.5-Pro lose about 8–22 points of word-level F1 on Vietnamese compared with their scores on high-resource tracks. For invoices, where one dropped tone mark can change a name or an amount-in-words string, this argues for script-aware post-checks such as diacritic normalisation and number-word ↔ digit cross-checks rather than relying on the raw MLLM output.
- I found no public Vietnamese benchmark of **multi-page financial documents or tables**. Every Vietnamese KIE resource found is a single receipt or ID card.

### Gaps
- I did not verify VinAI-specific document OCR or KIE papers this session.
- I found no published per-benchmark accuracy for PaddleOCR or VietOCR on Vietnamese invoices.
- I did not verify Thai or Indic document-model evidence.
- The survey states that its MC-OCR numbers come from the 2021 challenge, which predates this note's 2022 window; I include them as background.
- ReceiptVQA/LiGT scores and the IJDAR volume details are not verified.

## 5. Explainability and grounding (evidence pointers, bounding-box citations)

### Takeaway
Grounded extraction is now measurable, and it is weak. On CiteVQA's strict attributed accuracy (answer correct *and* supporting region correct), the best model scores 76.0 and the best open model 22.5, even though answers are often right with the wrong region cited. LMDX showed early that LLM extraction needs explicit localization to be trusted.

### Cited Findings
- **LMDX.** Perot et al., "LMDX: Language Model-based Document Information Extraction and Localization", arXiv:2309.10952 (v2 Jun 2024; the arXiv page lists no venue). — [arXiv:2309.10952](https://arxiv.org/abs/2309.10952)
  - It treats the absence of a grounding mechanism as a barrier to LLM-based extraction, and it provides "grounding guarantees" by localizing entities in the document.
  - It is evaluated on VRDU and CORD with PaLM 2-S and Gemini Pro. The abstract gives no numbers.
- **CiteVQA.** Ma et al., "CiteVQA: Benchmarking Evidence Attribution for Trustworthy Document Intelligence", arXiv:2605.12882 (v2 Oct 2026, no venue). — [arXiv:2605.12882](https://arxiv.org/abs/2605.12882)
  - It has 1,897 questions over 711 PDFs, covering 7 domains and 2 languages, and audits 20 MLLMs.
  - Best Strict Attributed Accuracy: **76.0 (Gemini-3.1-Pro-Preview)**. Best open-source model: **22.5**.
  - It reports "attribution hallucination": the answer is right but the cited region is wrong.
- **TRIG-Bench.** Li et al., "Towards Visual Text Grounding of Multimodal Large Language Model", arXiv:2504.04974. It has an 800-pair human-annotated benchmark plus synthetic training data, and finds "substantial limitations" in MLLMs' grounding on text-rich images. — [arXiv:2504.04974](https://arxiv.org/abs/2504.04974)
- **Hi-VT5** predicts the answer page, which the authors present as an explainability signal (see section 1). — [arXiv:2212.05935](https://arxiv.org/abs/2212.05935)
- Other grounding resources found only in search results, not individually verified:
  - BBox-DocVQA (arXiv:2511.15090; about 3.6K documents and 32K QA pairs with single- and multi-page boxes)
  - DocAttriBench (arXiv:2609.20574)
  - DocExplainerV0 (arXiv:2509.10129), a plug-in box predictor
  - — [BBox-DocVQA](https://arxiv.org/html/2511.15090v1); [DocAttriBench](https://arxiv.org/pdf/2609.20574); [DocExplainerV0](https://arxiv.org/pdf/2509.10129v2)

### Inferences
- In audit and finance, a reviewer must be able to trace each extracted figure to a region of the source. A gap of more than 50 points between closed and open models on strict attribution (76.0 vs 22.5) means an on-device or open-weight pipeline cannot rely on the model's own citations. Deterministic grounding, such as OCR-token alignment of extracted values or LMDX-style localization, is needed instead.
- Correct answers with wrong citations are dangerous because they pass answer-only metrics.

### Gaps
- I found no finance-specific grounded-extraction benchmark, such as cell-level citations into multi-page financial tables.
- I did not verify answer-only accuracy on CiteVQA, so the size of the answer-vs-attribution gap is not quantified here.

## 6. Human-in-the-loop and selective automation (abstention, conformal or certified accuracy)

### Takeaway
Formal guarantees for document KIE are only starting to appear. The clearest data point is an IJDAR 2026 paper applying split conformal prediction to receipt KIE: 98.3% marginal coverage at α = 0.02, with 70% of predictions being confident singletons that can be auto-processed and the rest flagged for review. Earlier work (HYCEDIS, 2022) addressed confidence engines without coverage guarantees. I found no work on certified accuracy for multi-page or table extraction.

### Cited Findings
- **Conformal KIE.** "Beyond Accuracy: Understanding Model Confidence in Key Information Extraction with Conformal Prediction", IJDAR 2026, vol. 29, pp. 551–563, DOI 10.1007/s10032-026-00572-y (DFKI / Saarland). I confirmed the metadata from a repository copy and search snippets; I could not open the publisher page (login redirect), and the PDF text could not be extracted. — [Saarland repository PDF](https://jahrbib.sulb.uni-saarland.de/bitstream/20.500.11880/42305/1/s10032-026-00572-y.pdf); [DFKI copy](https://www-live.dfki.de/fileadmin/user_upload/import/17320_s10032-026-00572-y.pdf); [DOI](https://doi.org/10.1007/s10032-026-00572-y)
  - The method is a post hoc split-CP layer on multimodal transformers fine-tuned on a receipt dataset. Entity-level prediction sets satisfy a user-specified error rate.
  - **98.3% marginal coverage at α = 0.02; 70% of predictions are singletons.**
  - It proposes routing by prediction-set size: auto-process singletons, flag uncertain cases for human review. It argues that extraction errors in invoice processing can cause costly overpayments.
  - It reports that CP exposes positional biases and label confusions that F1 and document accuracy miss.
- **HYCEDIS.** Nguyen et al., "HYCEDIS: HYbrid Confidence Engine for Deep Document Intelligence System", arXiv:2206.02628 (2022; the comments field says Document Intelligence @ KDD 2021 Workshop). It is a multi-modal confidence engine for information extraction from scanned documents. Its abstract states that no reliable confidence solution existed for that task; it gives no numbers. — [arXiv:2206.02628](https://arxiv.org/abs/2206.02628)
- MMLongBench-Doc includes 22.8% unanswerable questions, which tests whether models abstain on long documents. — [arXiv:2407.01523](https://arxiv.org/abs/2407.01523)

### Inferences
- Marginal coverage is not conditional coverage. A 98.3% marginal guarantee can still hide much worse coverage on rare fields such as totals and tax IDs, or on noisy captures. Finance needs per-field or per-document guarantees, which these papers do not show.
- An automation rate of about 70% at α = 0.02 is a useful baseline for selective automation, but it comes from single receipts. I found no equivalent figure for multi-page dossiers or table cells.
- Combining conformal sets with deterministic verifiers is an open direction: checksums, cross-field arithmetic (line items summing to the total), and number-word ↔ digit agreement. Rule-based checks could supply a guarantee that does not depend on exchangeability.

### Gaps
- I verified no deployed-system paper or industry blog that reports numbers for human-review routing thresholds or straight-through-processing rates.
- I did not verify whether DUDE reports calibration or selective-prediction metrics (ECE, AURC).
- I found no conformal or certified approach for table structure or multi-page QA.
