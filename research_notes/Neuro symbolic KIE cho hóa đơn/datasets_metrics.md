# Benchmark datasets and evaluation metrics for invoice/receipt KIE and document VQA (focus: Vietnamese financial documents)

Verification method used for these notes: arXiv identifiers, titles, first authors and dates were checked against the arXiv API (export.arxiv.org) on 2026-11-21. Size figures are quoted only where the paper abstract, official repo or dataset card states them. Anything recalled from memory but not confirmed in this session sits under **Gaps**, labelled "unverified".

## Q1. Open datasets: size, language, document type, annotation granularity, license, venue/year, known issues

### Takeaway
Only a few open receipt/invoice KIE sets are truly financial: SROIE, CORD, WildReceipt, DocILE and VRDU Ad-buy. All are small (about 1k documents) or English/Indonesian/Chinese. Only CORD, DocILE and VRDU annotate line items or hierarchy. None contains Vietnamese. Two widely used benchmarks have documented quality problems: FUNSD has inconsistent labels, and RVL-CDIP has about 8.1% label noise plus train/test overlap.

### Cited Findings

**KIE / form understanding**
- **FUNSD.** "FUNSD: A Dataset for Form Understanding in Noisy Scanned Documents", Guillaume Jaume et al., ICDAR 2019 OST workshop, arXiv:1905.13538. 199 real, fully annotated, noisy scanned forms (English). Tasks: text detection, OCR, layout, entity labelling and entity linking. — [arXiv:1905.13538](https://arxiv.org/abs/1905.13538)
- **FUNSD label noise.** Hieu M. Vu et al., "Revising FUNSD dataset for key-value detection in document images" (arXiv:2010.05322, 2020) "found several inconsistency in labeling" and released a revised version. — [arXiv:2010.05322](https://arxiv.org/abs/2010.05322)
- **CORD.** "CORD: A Consolidated Receipt Dataset for Post-OCR Parsing", Seunghyun Park et al., Document Intelligence Workshop @ NeurIPS 2019 (no arXiv). Indonesian shop/restaurant receipts. The README describes over 11,000 receipts, but only 1,000 are released (800 train / 100 dev / 100 test). 5 superclasses and 42 subclasses. Annotations: word-level text, quadrilateral boxes, `is_key`, `row_id`, `group_id`, nested `menu.sub_*` line items (`sub_group_id` added in v2). License CC BY 4.0. Known inconsistency: the README's class table header says "total 30" but lists 42 subclass rows. — [GitHub clovaai/cord](https://github.com/clovaai/cord)
- **SROIE.** "ICDAR2019 Competition on Scanned Receipt OCR and Information Extraction", Zheng Huang et al., ICDAR 2019 competition (report arXiv:2103.10213, 2021). 1,000 whole scanned receipt images. 3 tasks: text localisation, OCR, KIE. — [arXiv:2103.10213](https://arxiv.org/abs/2103.10213)
- **XFUND.** Introduced in "LayoutXLM: Multimodal Pre-training for Multilingual Visually-rich Document Understanding", Yiheng Xu et al., arXiv:2104.08836. Formal dataset paper: "XFUND: A Benchmark Dataset for Multilingual Visually Rich Form Understanding", Findings of ACL 2022, pp. 3214–3224. 7 languages (zh, ja, es, fr, it, de, pt; **no Vietnamese**). Key-value pairs manually labelled. 199 forms per language (1,393 total), split 149 train / 50 test. — [arXiv:2104.08836](https://arxiv.org/abs/2104.08836); [ACL Anthology 2022.findings-acl.253](https://aclanthology.org/2022.findings-acl.253)
- **XFUND license is ambiguous across mirrors.** One HF mirror states CC BY-NC-SA 4.0. Other copies say "other" or MIT, where MIT applies to a separate re-annotation. — [HF FrancophonIA/XFUND (via search)](https://huggingface.co/datasets/FrancophonIA/XFUND)
- **EPHOIE.** "Towards Robust Visual Information Extraction in Real World: New Dataset and Novel Solution", Jiapeng Wang et al., AAAI 2021, arXiv:2102.06732. 1,494 Chinese examination-paper-head images with 15,771 handwritten or printed text instances. Annotated for both text spotting and VIE. Not financial. — [arXiv:2102.06732](https://arxiv.org/abs/2102.06732)
- **SIBR.** "Modeling Entities as Semantic Points for Visual Information Extraction in the Wild", Zhibo Yang et al., arXiv:2303.13095 (2023). Real-application images with blur, occlusion and printing shift. Entity labelling and linking. Distributed via ModelScope. — [arXiv:2303.13095](https://arxiv.org/abs/2303.13095)
- **WildReceipt.** Released with "Spatial Dual-Modality Graph Reasoning for Key Information Extraction" (SDMG-R), Hongbin Sun et al., arXiv:2103.14470 (2021). Built for unseen-template KIE. 25 key-information categories, about 69,000 text boxes. — [arXiv:2103.14470](https://arxiv.org/abs/2103.14470)
- **DocILE.** "DocILE Benchmark for Document Information Localization and Extraction", Štěpán Šimsa et al., ICDAR 2023, arXiv:2302.05658. 6.7k annotated business documents (invoice-like), 100k synthetic, about 1M unlabelled. 55 classes. Tasks: KILE plus Line Item Recognition. The test set includes zero-shot and few-shot layouts. It also ran as a CLEF 2023 lab (teaser at ECIR 2023, arXiv:2301.12394). — [arXiv:2302.05658](https://arxiv.org/abs/2302.05658); [arXiv:2301.12394](https://arxiv.org/abs/2301.12394)
- **VRDU.** "VRDU: A Benchmark for Visually-rich Document Understanding", Zilong Wang et al., KDD 2023, arXiv:2211.15421. Two datasets: Registration Forms (FARA; 3 templates, simple fields) and Ad-buy Forms (DeepForm; dozens of templates, nested/repeated line-item fields). Three settings: Single, Mixed and Unseen Template Learning, each with 10/50/100/200 training docs. Evaluated with type-specific matchers (DateMatch, NumericalMatch, PriceMatch). The authors note models "struggle with hierarchical fields such as line-items in an invoice". — [arXiv:2211.15421](https://arxiv.org/abs/2211.15421); [GitHub google-research-datasets/vrdu](https://github.com/google-research-datasets/vrdu)
- **Kleister.** "Kleister: Key Information Extraction Datasets Involving Long Documents with Complex Layouts", Tomasz Stanisławek et al., ICDAR 2021, arXiv:2105.05796. English. Kleister Charity: 2,788 charity annual financial reports, 61,643 pages, 21,612 entities. Kleister NDA: 540 NDAs, 3,229 pages, 2,160 entities. Best baseline F1: 81.77 (NDA) and 83.57 (Charity). — [arXiv:2105.05796](https://arxiv.org/abs/2105.05796)
- **SVRD (ICDAR 2023).** "ICDAR 2023 Competition on Structured Text Extraction from Visually-Rich Document Images", Wenwen Yu et al., arXiv:2306.03287; LNCS 14188, DOI 10.1007/978-3-031-41679-8_32. Two tracks: HUST-CELL (end-to-end complex entity linking and labelling) and Baidu-FEST (zero-/few-shot structured text extraction). More than 50 document types, mostly from enterprise applications. — [arXiv:2306.03287](https://arxiv.org/abs/2306.03287); [Springer](https://link.springer.com/chapter/10.1007/978-3-031-41679-8_32)
- **Recent receipt sets (2024–2026):** ReceiptSense (Abdelrahman Abdallah et al., arXiv:2406.04493): 20,000 Arabic-English receipts, 10,000 item-level annotations, a Receipt QA subset. ReceiptBench (Yandi Wang et al., arXiv:2605.22413, May 2026): 10k human-annotated receipts across 4 sub-tasks (perception, format normalisation, semantic reasoning, nested line-item parsing). VAREX (Udi Barzelay et al., arXiv:2603.15118, 2026): 1,777 synthetic government-form documents with 1,771 schemas. — [arXiv:2406.04493](https://arxiv.org/abs/2406.04493); [arXiv:2605.22413](https://arxiv.org/abs/2605.22413); [arXiv:2603.15118](https://arxiv.org/abs/2603.15118)

**Document VQA**
- **DocVQA.** "DocVQA: A Dataset for VQA on Document Images", Minesh Mathew et al., WACV 2021, arXiv:2007.00398. 50,000 questions on 12,000+ document images. Human accuracy 94.36%. Leaderboard at docvqa.org. — [arXiv:2007.00398](https://arxiv.org/abs/2007.00398)
- **InfographicVQA.** "InfographicVQA", Minesh Mathew et al., arXiv:2104.12756 (WACV 2022). Questions need joint reasoning over layout, text, graphics and data visualisation, with elementary arithmetic. — [arXiv:2104.12756](https://arxiv.org/abs/2104.12756)
- **ChartQA.** "ChartQA: A Benchmark for Question Answering about Charts with Visual and Logical Reasoning", Ahmed Masry et al., Findings of ACL 2022, arXiv:2203.10244. 9.6K human-written questions plus 23.1K questions generated from chart summaries. — [arXiv:2203.10244](https://arxiv.org/abs/2203.10244)
- **TAT-DQA.** "Towards Complex Document Understanding By Discrete Reasoning", Fengbin Zhu et al., ACM MM 2022, arXiv:2207.11871. 3,067 pages from real financial reports with tables and text, 16,558 QA pairs, many needing discrete numerical reasoning. **Non-commercial use only.** — [arXiv:2207.11871](https://arxiv.org/abs/2207.11871)
- **MP-DocVQA.** "Hierarchical multimodal transformers for Multi-Page DocVQA", Rubèn Tito et al., arXiv:2212.05935 (2022). Extends DocVQA to multi-page documents and adds a page-evidence prediction task. — [arXiv:2212.05935](https://arxiv.org/abs/2212.05935)
- **SlideVQA.** "SlideVQA: A Dataset for Document Visual Question Answering on Multiple Images", Ryota Tanaka et al., AAAI 2023, arXiv:2301.04883. 2.6k+ decks, 52k+ slide images, 14.5k questions. Arithmetic expressions are annotated for numerical answers. — [arXiv:2301.04883](https://arxiv.org/abs/2301.04883)

**Classification / pre-training corpora**
- **RVL-CDIP.** Adam W. Harley et al., "Evaluation of Deep Convolutional Nets for Document Image Classification and Retrieval", arXiv:1502.07058 (ICDAR 2015). 400,000 images in 16 categories, drawn as a labelled subset of IIT-CDIP. — [arXiv:1502.07058](https://arxiv.org/abs/1502.07058)
- **RVL-CDIP issues.** Stefan Larson et al., "On Evaluation of Document Classification using RVL-CDIP", EACL 2023 (arXiv:2306.12550). Estimated label noise is 8.1% (1.6–16.9% per class). The paper also finds many ambiguous or multi-label documents, "a large overlap between test and train splits", and US SSNs and other PII in the data. SOTA error rates now fall within the label-error rate. — [arXiv:2306.12550](https://arxiv.org/abs/2306.12550)

**Tables**
- **PubTabNet.** "Image-based table recognition: data, model, and evaluation", Xu Zhong et al., arXiv:1911.10683 (ECCV 2020). 568k table images with HTML structure, auto-generated by matching PMC-OA XML and PDF (scientific, not financial). Introduced the **TEDS** metric. — [arXiv:1911.10683](https://arxiv.org/abs/1911.10683)
- **FinTabNet.** Introduced in "Global Table Extractor (GTE)…", Xinyi Zheng et al., WACV 2021, arXiv:2005.00589. Financial-report tables with automatically derived cell-structure labels. — [arXiv:2005.00589](https://arxiv.org/abs/2005.00589)
- **TableFormer** (Ahmed Nassar et al., arXiv:2203.01017, CVPR 2022) reports TEDS on PubTabNet rising from 91% to 98.5% on simple tables and from 88.7% to 95% on complex ones. This suggests PubTabNet is close to saturation. — [arXiv:2203.01017](https://arxiv.org/abs/2203.01017)

### Inferences
- For Vietnamese invoice work, the most relevant structural templates are **CORD** (nested menu/line items, CC BY 4.0), **DocILE** (55 classes plus line items, invoice-like) and **VRDU** (unseen-template protocol, typed matchers). FUNSD and XFUND are forms, not financial documents.
- Automatic labelling (PubTabNet, FinTabNet) and the documented noise in FUNSD and RVL-CDIP mean that a high score near the ceiling should be checked against label quality before it is read as model quality.
- TAT-DQA's non-commercial license and the CC BY-NC-SA mirror license reported for XFUND both restrict use in a product pipeline. Check each license before training on these sets.

### Gaps
- Exact sizes not confirmed in this session (unverified recollection, do not cite without checking): InfographicVQA (~5.4k images / ~30k Q), MP-DocVQA (~46k Q / ~48k pages), WildReceipt (~1.7k images), SIBR (~1k images, Chinese/English), VRDU (~1.9k registration forms / ~641 ad-buy forms), FinTabNet (~112k tables), IIT-CDIP (~7M pages; Lewis et al., SIGIR 2006).
- Licenses not verified for: FUNSD (non-commercial research use, per my recollection), SROIE, EPHOIE, SIBR, WildReceipt, DocILE, VRDU, Kleister, DocVQA family, ChartQA, SlideVQA, PubTabNet/FinTabNet (CDLA-Permissive, per my recollection).
- SROIE label noise and DocVQA/ChartQA contamination of LLM pre-training data are widely discussed, but I found no primary source this session.
- I did not confirm XFUND's original-repo license (microsoft/unilm). It is the authoritative source.

## Q2. What is "SDU-ST"?

### Takeaway
I found no dataset called "SDU-ST" for invoice parsing (or any other task). A targeted web search for "SDU-ST" invoice dataset returned only University of Southern Denmark (SDU) invoicing pages. It most likely comes from a mixed-up or hallucinated name. Do not cite it.

### Cited Findings
- A search for "SDU-ST" dataset invoice returned only University of Southern Denmark invoicing/terms pages and the generic "SDU" disambiguation page, with no dataset. — [SDU invoicing page](https://www.sdu.dk/en/om-sdu/indkoeb/elektroniske_fakturaer); [Wikipedia "SDU"](https://en.wikipedia.org/wiki/SDU)
- The most plausible intended name is **SVRD**, the ICDAR 2023 "Structured text extraction from Visually-Rich Document images" competition. "ST" matches "Structured Text", and its tracks HUST-CELL and Baidu-FEST cover enterprise documents. — [arXiv:2306.03287](https://arxiv.org/abs/2306.03287)
- Other candidates with similar letters:
  - **SROIE**, "Scanned Receipt OCR and Information Extraction", the standard receipt KIE set. — [arXiv:2103.10213](https://arxiv.org/abs/2103.10213)
  - **ST-VQA**, "Scene Text VQA", the paper that introduced ANLS. — [arXiv:1905.13648](https://arxiv.org/abs/1905.13648)

### Inferences
- If the name appeared in an LLM-generated draft, assume it was fabricated. Ask where the user saw it before substituting another dataset.

### Gaps
- "SDU" is also the name of a workshop series (Scientific Document Understanding, at AAAI), which could be the source of the confusion. This was not verified this session.

## Q3. Vietnamese datasets (receipts, invoices, VQA, OCR, handwriting, e-invoice)

### Takeaway
I found no public, labelled Vietnamese **invoice** (hóa đơn GTGT / e-invoice) KIE benchmark. The Vietnamese financial resources that do exist are receipt sets:
- **MC-OCR 2021**: about 2.4k mobile receipts, 4 fields.
- **ReceiptVQA**: 9k+ receipts, 60k+ QA pairs.
- **UIT-MLReceipts**: about 2k receipts, mentioned only by a secondary source.

The others are scene-text VQA or handwriting sets. "UIT-ViOCD" is not an OCR dataset: it is a complaint-detection text corpus.

### Cited Findings
- **MC-OCR 2021.** "MC-OCR Challenge: Mobile-Captured Image Document Recognition for Vietnamese Receipts", Xuan-Son Vu et al., RIVF 2021 (Hanoi, 19–21 Aug 2021, IEEE). There is no arXiv version; the preprint is on the author's page. Two tasks: receipt image-quality assessment and KIE of 4 fields (SELLER, SELLER ADDRESS, TIMESTAMP, TOTAL COST). 105 participants, about 1,285 submissions. — [MC-OCR preprint](https://people.cs.umu.se/sonvx/files/MCOCR_Preprint.pdf); [Codalab competition 27798](https://competitions.codalab.org/competitions/27798)
- **MC-OCR size.** A later paper describes the RIVF 2021 data as 2,436 mobile-captured Vietnamese receipt images. — [ReceiptSense arXiv:2406.04493](https://arxiv.org/abs/2406.04493). The Vietnamese DAR survey says "over 2,000". — [arXiv:2506.05061](https://arxiv.org/abs/2506.05061). An unofficial HF mirror exists. — [HF tqhuyen/MC_OCR2021](https://huggingface.co/datasets/tqhuyen/MC_OCR2021)
- **MC-OCR participant papers (RIVF 2021):**
  - Doanh C. Bui et al., "MC-OCR Challenge 2021: Deep Learning Approach for Vietnamese Receipts OCR". — [dblp](https://dblp.org/rec/conf/rivf/BuiTVN21.html)
  - Hoai Viet Nguyen et al., "…Towards Document Understanding for Unconstrained Mobile-Captured Vietnamese Receipts", DOI 10.1109/RIVF51545.2021.9642126. — [Crossref](https://api.crossref.org/works/10.1109%2FRIVF51545.2021.9642126)
- **ReceiptVQA.** Released with "LiGT: Layout-infused Generative Transformer for Visual Question Answering on Vietnamese Receipts", Thanh-Phong Le et al., arXiv:2502.19202, accepted at IJDAR. 9,000+ Vietnamese receipt images and 60,000+ manually annotated QA pairs. Described as the first large-scale Vietnamese document VQA dataset for receipts. — [arXiv:2502.19202](https://arxiv.org/abs/2502.19202)
- **UIT-MLReceipts (2024).** More than 2,000 receipt images with 4 bounding-box classes, similar to the MC-OCR fields. Source is a GitHub project, not a dataset paper. — [GitHub WyzanDev/VietReceiptAI](https://github.com/WyzanDev/VietReceiptAI)
- **ViTextVQA.** "ViTextVQA: A Large-Scale Visual Question Answering Dataset and a Novel Multimodal Feature Fusion Method for Vietnamese Text Comprehension in Images", Quan Van Nguyen et al., arXiv:2404.10652 (Expert Systems with Applications). 16,000+ images and 50,000+ QA pairs of scene-text VQA. — [arXiv:2404.10652](https://arxiv.org/abs/2404.10652)
- **ViOCRVQA.** Huy Quang Pham et al., arXiv:2404.18397 (2024). 28,000+ images and 120,000+ QA pairs. Best reported result: EM 0.4116, F1 0.6990. — [arXiv:2404.18397](https://arxiv.org/abs/2404.18397)
- **EVJVQA (often called "UIT-EVJVQA").** "EVJVQA Challenge: Multilingual Visual Question Answering", Ngan Luu-Thuy Nguyen et al., VLSP 2022 shared task, arXiv:2302.11752. 33,000+ QA pairs in vi/en/ja on about 5,000 images taken in Vietnam. Top private-test F1 was 0.4392. General VQA, not documents. — [arXiv:2302.11752](https://arxiv.org/abs/2302.11752)
- **OpenViVQA.** Nghia Hieu Nguyen et al., arXiv:2305.04183 (2023). 11,000+ images and 37,000+ open-ended QA pairs. General VQA. — [arXiv:2305.04183](https://arxiv.org/abs/2305.04183)
- **UIT-ViOCD is not an OCR dataset.** It is "Vietnamese Open-domain Complaint Detection in E-commerce Websites" (SoMeT 2021, arXiv:2104.11969): 5,485 product reviews in 4 domains. The SEACrowd mirror lists its license as unknown. — [arXiv:2104.11969](https://arxiv.org/abs/2104.11969); [HF SEACrowd/uit_viocd](https://huggingface.co/datasets/SEACrowd/uit_viocd/blob/main/uit_viocd.py)
- **Vietnamese OCR and handwriting sets**, as listed in "A Survey on Vietnamese Document Analysis and Recognition: Challenges and Future Directions" (Anh Le et al., arXiv:2506.05061, June 2025):
  - HANDS-VNOnDB: online handwriting, 1,146 paragraphs, 2018.
  - UIT-HWDB: RIVF 2022.
  - Cinnamon AI handwriting: 1,838 images.
  - Kaggle handwritten words: 110k+ images.
  - Nexdata: 4,995 images.
  - DataoceanAI: 5,006 images.
  - VNDoc: 226 documents covering legal documents, **invoices** and resumes; text detection only.
  - VinText and VnSceneText: scene text.

  The survey names no Vietnamese table or layout dataset and does not discuss e-invoices. — [arXiv:2506.05061](https://arxiv.org/html/2506.05061v1)
- **Vintern-1B** (Khang T. Doan et al., arXiv:2408.12480) open-sourced Vietnamese VQA data generated with Gemini 1.5 Flash. A search summary describes its Viet-Receipt-VQA as built on MC-OCR. That makes it synthetic labelling, not human ground truth. — [arXiv:2408.12480](https://arxiv.org/abs/2408.12480)
- **Vietnamese e-invoice legal and data resources (no ML dataset found):**
  - Decree 123/2020/NĐ-CP is the base invoice regulation. Circular 78/2021/TT-BTC (effective 01/07/2022) guided it. — [thuvienphapluat: TT 78/2021](https://thuvienphapluat.vn/van-ban/thue-phi-le-phi/thong-tu-78-2021-tt-btc-huong-dan-luat-quan-ly-thue-nghi-dinh-123-2020-nd-cp-hoa-don-chung-tu-477966.aspx)
  - E-invoices use an XML data standard with a business-data component and a digital-signature component. The XML tags and structure are set by Quyết định 1450/QĐ-TCT (2021). — [Tạp chí Công Thương](https://tapchicongthuong.vn/hoa-don-dien-tu-nhung-thay-doi-sau-nghi-dinh-so-123-2020-nd-cp-va-thong-tu-so-78-2021-tt-btc-102903.htm); [QĐ 1450/QĐ-TCT](https://thuvienphapluat.vn/van-ban/thue-phi-le-phi/quyet-dinh-1450-qd-tct-2021-thanh-phan-chua-du-lieu-nghiep-vu-hoa-don-dien-tu-490526.aspx)
  - Three invoice categories exist: with a tax-authority code, without a code, and generated from a connected cash register. — [Tạp chí Công Thương](https://tapchicongthuong.vn/hoa-don-dien-tu-nhung-thay-doi-sau-nghi-dinh-so-123-2020-nd-cp-va-thong-tu-so-78-2021-tt-btc-102903.htm)
  - **Update:** Decree 70/2025/NĐ-CP (issued 20/3/2025, effective 01/6/2025) amends Decree 123. Circular 32/2025/TT-BTC (31/5/2025) guides it and is reported to replace Circular 78/2021. — [LuatVietnam: NĐ 70/2025](https://luatvietnam.vn/tin-van-ban-moi/da-co-nghi-dinh-70-2025-nd-cp-sua-doi-nghi-dinh-123-2020-186-101431-article.html); [LuatVietnam: TT 32/2025](https://luatvietnam.vn/tin-van-ban-moi/da-co-thong-tu-32-2025-tt-btc-huong-dan-nghi-dinh-123-nghi-dinh-70-ve-hoa-don-chung-tu-186-102343-article.html); [PwC Vietnam brief](https://www.pwc.com/vn/vn/publications/2025/250416-changes-to-invoicing-regulations.pdf)

### Inferences
- MC-OCR's 4-field schema has no line items, VAT breakdown, tax code (MST) or amount-in-words. ReceiptVQA is QA-style, not schema-style. No public Vietnamese resource covers VAT-invoice KIE with line items.
- Because e-invoices are XML-native (QĐ 1450 schema), a Vietnamese benchmark could pair rendered or printed invoice images with the authoritative XML as ground truth, similar to VAREX's "reverse annotation" idea. This would yield deterministic labels without manual annotation. This is a design suggestion, not an existing resource.
- Any benchmark built in 2026 should follow the post-01/6/2025 regime (NĐ 70/2025 + TT 32/2025). Older samples follow NĐ 123 + TT 78, so a dataset will contain both regimes.

### Gaps
- Exact MC-OCR split sizes: the preprint has a per-phase table, but its PDF text could not be extracted this session. A 1,155-image training split is cited only by community repos. The MC-OCR license is not stated in the sources found.
- VinText citation conflict: the survey cites it as "Huy et al. (2023)". My recollection is the VinAI CVPR 2021 paper "Dictionary-guided Scene Text Recognition" (Nguyen et al.), not verified here.
- Licenses and availability of ReceiptVQA, ViTextVQA, ViOCRVQA, OpenViVQA and UIT-HWDB were not confirmed. UIT datasets are typically research-only on request, which is also unverified.
- No VinAI or other Vietnamese **invoice** dataset was found, and no VLSP shared task on invoices or receipts was found.

## Q4. Metric definitions, proposers and caveats

### Takeaway
- **ANLS** (Biten et al., ICCV 2019) is the de-facto DocVQA metric. **ANLS\*** (Peer et al., 2024) extends it to dicts and lists for generative structured output.
- For KIE, the usual metrics are entity-level F1 (seqeval / CoNLL style), field exact match, and Donut's normalised tree-edit-distance accuracy.
- For tables, the standard is TEDS (Zhong et al., 2019).
- Arithmetic or "consistency-check pass rate" metrics exist only in recent preprints and vendor projects. None is standardised, and they can be gamed by consistent hallucination.

### Cited Findings
- **ANLS** was proposed with ST-VQA in "Scene Text Visual Question Answering", Ali Furkan Biten et al., ICCV 2019, arXiv:1905.13648. The paper describes it as a metric that accounts for "both for reasoning errors as well as shortcomings of the text recognition module". — [arXiv:1905.13648](https://arxiv.org/abs/1905.13648)
- **ANLS\*.** "ANLS* -- A Universal Document Processing Metric for Generative Large Language Models", David Peer, Philemon Schöpf, Volckmar Nebendahl, Alexander Rietzler, Sebastian Stabinger. arXiv:2402.03848 (v10, April 2025, no venue listed). Apache-2.0 code. It is a drop-in extension, backward-compatible with ANLS. Rules:
  - Strings: normalised Levenshtein similarity.
  - Tuples: best-matching alternative, as in classic ANLS.
  - Lists: order-free; Hungarian matching pairs predicted and gold items, and both missing and invented items are penalised.
  - Dicts: key-based; "Missing keys as well as hallucinated keys are penalized".
  - None: a None gold answer penalises any non-None prediction. A predicted None key absent from gold is ignored.

  — [arXiv:2402.03848](https://arxiv.org/abs/2402.03848); [GitHub deepopinion/anls_star_metric](https://github.com/deepopinion/anls_star_metric)
- **TEDS** was proposed in Zhong et al., "Image-based table recognition: data, model, and evaluation" (arXiv:1911.10683). It is a Tree-Edit-Distance-based Similarity on the HTML tree that "more appropriately captures multi-hop cell misalignment and OCR errors" than adjacency-relation metrics. — [arXiv:1911.10683](https://arxiv.org/abs/1911.10683)
- **Donut** (Geewook Kim et al., "OCR-free Document Understanding Transformer", ECCV 2022, arXiv:2111.15664) evaluates KIE on CORD-style JSON. The scores were updated "with the latest test script" in v5. — [arXiv:2111.15664](https://arxiv.org/abs/2111.15664)
- **VRDU** uses a "carefully designed matching algorithm" with type-specific matchers (DateMatch, NumericalMatch, PriceMatch) instead of plain string F1. — [arXiv:2211.15421](https://arxiv.org/abs/2211.15421); [GitHub vrdu](https://github.com/google-research-datasets/vrdu)
- **Kleister** reports entity-level F1 (best 81.77 / 83.57). **MC-OCR** split its tasks into image-quality regression and field KIE. — [arXiv:2105.05796](https://arxiv.org/abs/2105.05796); [MC-OCR preprint](https://people.cs.umu.se/sonvx/files/MCOCR_Preprint.pdf)
- **Consistency / numerical metrics:**
  - Sai Yashwant, "Invoice Information Extraction: Methods and Performance Evaluation" (arXiv:2510.15727, Oct 2025), proposes field-level precision, **consistency-check failures** and exact-match accuracy for invoices. A search summary reports pass rates of 93% versus 80% for two extractors, with failures from line-item/summary mismatches and tax-field errors. — [arXiv:2510.15727](https://arxiv.org/abs/2510.15727)
  - ReceiptBench (Yandi Wang et al., arXiv:2605.22413, May 2026) uses cross-field checks such as "sum of line items matches total". It reports that MLLMs alter line prices or hallucinate a "Tax" item to force the sums to agree. It also trains with "Metric-Aware GRPO" for structural consistency. — [arXiv:2605.22413](https://arxiv.org/abs/2605.22413)
  - An open-source project lists the deterministic checks `amount == qty × unit_price`, `Σ lines == subtotal` and `subtotal − discount + tax == total`. It reports that a consistently recomputed price change passed every check in 49 of 49 trials. — [GitHub AGTNurat/LLM-invoice-extraction](https://github.com/AGTNurat/LLM-invoice-extraction)
  - InvoiceBenchmark (HF) injects deliberate total errors (60% correct, 20% total_error, among others), so models must flag inconsistency rather than repair it. — [HF jngb-labs/InvoiceBenchmark](https://huggingface.co/datasets/jngb-labs/InvoiceBenchmark)

### Inferences
These are standard definitions, stated for the report writer. They are consistent with the cited papers, but the exact formulas were not re-read in the PDFs this session.
- **ANLS:** for each question, s = max over gold answers of (1 − NL(gold, pred)) if NL < τ, else 0. NL is Levenshtein distance divided by the longer string's length, and τ = 0.5. ANLS is the mean of s over questions.
- **Caveat on ANLS:** it gives partial credit to near-miss strings. For amounts and tax codes, one wrong digit can still score about 0.9. It should not be used alone for numeric or ID fields; pair it with exact match.
- **Entity-level F1 (seqeval, CoNLL-2000 style; Hiroki Nakayama, GitHub "chakki-works/seqeval", 2018):** an entity counts as correct only if its span and type match exactly; P/R/F1 are micro-averaged over entities. It needs token-level BIO tags and does not apply directly to generative output.
- **Donut TED accuracy:** max(0, 1 − TED(pred, gt) / TED(∅, gt)), computed on the JSON tree (Zhang–Shasha). Donut reports it alongside field-level F1.
- **TEDS:** TEDS(Ta, Tb) = 1 − EditDist(Ta, Tb) / max(|Ta|, |Tb|). TEDS-struct is the same computation with cell content ignored, so it scores structure only.
- **CER/WER:** (S + D + I) / N, at character or word level. For Vietnamese, report CER both with and without diacritics, and normalise Unicode (NFC vs NFD) first. Otherwise composed and decomposed forms of the same character count as errors.
- **Consistency pass rate:** a pass on an internal-consistency check is necessary but not sufficient. Report it alongside field accuracy against gold, and separately track whether the model edits source values to make the sums agree.

### Gaps
- I did not retrieve primary text for:
  - the exact ANLS formula and τ;
  - Donut's TED-accuracy formula;
  - the seqeval citation (GitHub, no paper);
  - the first paper to define **TEDS-struct**. It is widely used (e.g., in table-recognition papers after 2021), but I could not confirm who introduced it.
- I found no peer-reviewed, venue-published "constraint satisfaction rate" or "sum-check pass rate" metric. The sources above are an arXiv preprint (2510.15727), a 2026 preprint (2605.22413) and practitioner repos.

## Q5. What a Vietnamese financial benchmark needs that existing ones lack

### Takeaway
Existing benchmarks lack:
- Vietnamese text with diacritics in financial layouts;
- VAT-invoice schemas (MST tax codes, VAT-rate breakdown, amount-in-words);
- line items with arithmetic ground truth;
- handwriting on receipts and invoices;
- a legal-regime field (NĐ 123/TT 78 vs NĐ 70/TT 32);
- metrics that check numeric and ID exactness and cross-field consistency, not only string similarity.

### Cited Findings
- **Vietnamese-specific OCR difficulties** per the survey: "complex diacritics, tonal variations, and lack of large-scale annotated datasets". Multiple diacritics change meaning. Word boundaries are not like English. Handwriting varies greatly across writers. — [arXiv:2506.05061](https://arxiv.org/html/2506.05061v1)
- **No language coverage:** XFUND covers 7 languages without Vietnamese. CORD is Indonesian, SROIE is English, and EPHOIE is Chinese. — [arXiv:2104.08836](https://arxiv.org/abs/2104.08836); [GitHub clovaai/cord](https://github.com/clovaai/cord); [arXiv:2103.10213](https://arxiv.org/abs/2103.10213); [arXiv:2102.06732](https://arxiv.org/abs/2102.06732)
- **No invoice schema:** MC-OCR has only 4 fields (seller, address, timestamp, total). — [MC-OCR preprint](https://people.cs.umu.se/sonvx/files/MCOCR_Preprint.pdf)
- **Line items are rare and hard:** only DocILE, CORD and VRDU include them, and VRDU finds models struggle on them. — [arXiv:2302.05658](https://arxiv.org/abs/2302.05658); [arXiv:2211.15421](https://arxiv.org/abs/2211.15421)
- **Generative models "fix" arithmetic by hallucination,** so a benchmark must test detection of inconsistencies, not only extraction. — [arXiv:2605.22413](https://arxiv.org/abs/2605.22413); [GitHub AGTNurat/LLM-invoice-extraction](https://github.com/AGTNurat/LLM-invoice-extraction); [HF InvoiceBenchmark](https://huggingface.co/datasets/jngb-labs/InvoiceBenchmark)
- **Vietnamese e-invoices have an authoritative XML schema** (QĐ 1450/QĐ-TCT), and the rules changed on 01/6/2025 (NĐ 70/2025, TT 32/2025). — [QĐ 1450](https://thuvienphapluat.vn/van-ban/thue-phi-le-phi/quyet-dinh-1450-qd-tct-2021-thanh-phan-chua-du-lieu-nghiep-vu-hoa-don-dien-tu-490526.aspx); [LuatVietnam](https://luatvietnam.vn/tin-van-ban-moi/da-co-nghi-dinh-70-2025-nd-cp-sua-doi-nghi-dinh-123-2020-186-101431-article.html)

### Inferences
Suggested benchmark requirements, derived from the gaps above:
1. **Schema.** Include seller and buyer MST (validated format), invoice form/series/number (ký hiệu, số hóa đơn), date, per-line name/unit/qty/unit price/amount, a per-rate subtotal and VAT block, the grand total, and **amount-in-words** (số tiền bằng chữ).
2. **Verifiable constraints as gold.** Store `qty × price = amount`, `Σ amounts per VAT rate = subtotal_r`, `subtotal_r × rate = VAT_r`, `Σ = total`, `words(total) == digits(total)`, plus MST checksum validity. Then report a constraint-satisfaction rate and a constraint-violation detection F1 on injected-error documents.
3. **Diacritic-aware OCR metrics.** Report CER with and without diacritics after NFC normalisation, and a separate field EM for diacritic-sensitive fields (names, addresses).
4. **Number formats.** Handle Vietnamese thousands separators (dot) versus decimal comma, and ₫/VND/đồng suffixes. Use typed matchers (as in VRDU) rather than ANLS for amounts.
5. **Capture conditions.** Include scanned PDFs, born-digital e-invoice renderings (XML as ground truth), and mobile photos (as in MC-OCR), plus handwritten receipts and handwritten corrections.
6. **Template-generalisation splits.** Use unseen-seller/template splits (as in VRDU UTL and the DocILE zero-shot layouts) to avoid layout memorisation. Track the legal-regime period (pre/post 01/6/2025) as metadata.
7. **Hygiene.** Deduplicate across splits, which RVL-CDIP shows matters. Redact PII (names, MST, phone numbers), which RVL-CDIP shows is a real risk. Publish a clear license.

### Gaps
- I did not retrieve the exact legal list of mandatory invoice fields (Decree 123 Article 10) this session, including whether the total must be written both in digits and in words.
- Current VAT rate sets were not verified this session: standard 0/5/10%, plus the temporary 8% reduction under National Assembly resolutions.
- The MST format (10 digits, or 13 with a 3-digit branch suffix, with a check digit) and its checksum algorithm are from memory. Confirm them in the Circular on tax registration before encoding them as benchmark constraints. The repo's `src/document_intake/verify/ids.py` may already implement this and should be checked against the regulation.
