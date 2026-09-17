"""Build the BERTopic supplementary methods document and the figure legends."""

import os

import pandas as pd
from docx import Document
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt

F9 = r"C:/72.wxjlx-1/Figure9_output"
F10 = r"C:/72.wxjlx-1/Figure10_output"
FONT = "Times New Roman"


# ------------------------------------------------------------------ helpers
def mr(text):
    return f'<m:r><m:t xml:space="preserve">{text}</m:t></m:r>'


def msub(base, sub):
    return f"<m:sSub><m:e>{base}</m:e><m:sub>{sub}</m:sub></m:sSub>"


def style_run(run, size=10.5, bold=False, italic=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)


def add_paragraph(document, text, size=10.5, bold=False, italic=False,
                  align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6,
                  space_before=0, keep_with_next=False):
    paragraph = document.add_paragraph()
    run = paragraph.add_run(text)
    style_run(run, size=size, bold=bold, italic=italic)
    paragraph.alignment = align
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.space_before = Pt(space_before)
    paragraph.paragraph_format.keep_with_next = keep_with_next
    paragraph.paragraph_format.keep_together = keep_together_value(italic)
    return paragraph


def keep_together_value(is_italic):
    return bool(is_italic)


def add_equation(document, inner, number=None):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph._p.append(parse_xml(f'<m:oMath {nsdecls("m")}>{inner}</m:oMath>'))
    if number:
        run = paragraph.add_run("   (" + number + ")")
        run.font.name = FONT
        run.font.size = Pt(10.5)
    return paragraph


def set_cell_border(cell, **kwargs):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        spec = kwargs.get(edge)
        element = OxmlElement(f"w:{edge}")
        if spec is None:
            element.set(qn("w:val"), "nil")
        else:
            element.set(qn("w:val"), "single")
            element.set(qn("w:sz"), str(spec["sz"]))
            element.set(qn("w:space"), "0")
            element.set(qn("w:color"), "000000")
        borders.append(element)
    tc_pr.append(borders)


def clear_table_borders(table):
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "nil")
        borders.append(element)
    table._tbl.tblPr.append(borders)


def three_line_table(document, header, rows, widths, font_size=9.5,
                     align_center=(), min_row_height=0.45):
    table = document.add_table(rows=1 + len(rows), cols=len(header))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    clear_table_borders(table)
    for j, name in enumerate(header):
        cell = table.cell(0, j)
        cell.text = ""
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(2)
        paragraph.paragraph_format.space_after = Pt(2)
        style_run(paragraph.add_run(name), size=font_size, bold=True)
    for i, row in enumerate(rows, start=1):
        for j, value in enumerate(row):
            cell = table.cell(i, j)
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.alignment = (WD_ALIGN_PARAGRAPH.CENTER if j in align_center
                                   else WD_ALIGN_PARAGRAPH.LEFT)
            paragraph.paragraph_format.space_before = Pt(1.5)
            paragraph.paragraph_format.space_after = Pt(1.5)
            style_run(paragraph.add_run(str(value)), size=font_size)
    for j in range(len(header)):
        set_cell_border(table.cell(0, j), top={"sz": 12}, bottom={"sz": 6})
        set_cell_border(table.cell(len(rows), j), bottom={"sz": 12})
        for i in range(1, len(rows)):
            set_cell_border(table.cell(i, j))
    # repeat the header row when the table continues on the next page
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:tblHeader"))
    for row in table.rows:
        row.height = Cm(min_row_height)
        row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
        tr_pr = row._tr.get_or_add_trPr()
        tr_pr.append(OxmlElement("w:cantSplit"))
        for cell, width in zip(row.cells, widths):
            cell.width = Cm(width)
    return table


def new_document():
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10.5)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    return doc


# ================================================================== document 1
info = pd.read_csv(F9 + "/topic_info.csv", encoding="utf-8-sig")
words = pd.read_csv(F9 + "/topic_topwords.csv", encoding="utf-8-sig")
sens = pd.read_csv(F9 + "/sensitivity/sensitivity_grid.csv", encoding="utf-8-sig")
realloc = pd.read_csv(F9 + "/outlier/outlier_reallocation.csv", encoding="utf-8-sig")
assign = pd.read_csv(F9 + "/topic_assignments.csv", encoding="utf-8-sig")
summary = pd.read_csv(F9 + "/run_summary.csv", encoding="utf-8-sig").iloc[0]

LABELS = {
    0: "Gut microbiota and cancer immunotherapy",
    1: "Colorectal cancer, Fusobacterium nucleatum and treatment resistance",
    2: "Immune checkpoint inhibitors and drug resistance",
    3: "Pancreatic ductal adenocarcinoma and gemcitabine resistance",
    4: "Bacterial infection, phage therapy and antimicrobial resistance",
    5: "Faecal microbiota transplantation for Clostridioides difficile infection",
    6: "Bile acid metabolism and hepatic drug transporters",
    7: "Inflammatory bowel disease and intestinal inflammation",
    8: "Ulcerative colitis and pouchitis",
    9: "Hepatocellular carcinoma and sorafenib resistance",
    10: "Graft-versus-host disease after haematopoietic stem cell transplantation",
}

doc = new_document()
add_paragraph(doc, "Supplementary methods for the BERTopic analysis of the corpus",
              size=15, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
add_paragraph(
    doc,
    f"The topic model underlying Figure 9 was fitted to the final corpus of "
    f"{int(summary['documents'])} deduplicated records published between 2016 and 2025. "
    f"This supplement reports the model configuration, the topic inventory with its "
    f"provisional labels, the sensitivity of the solution to the main settings, and the "
    f"treatment of the outlier topic. Tables continue the numbering of the D\u00b3TEM "
    f"supplement, which contains Tables S1 to S4.",
    space_after=12)

add_paragraph(doc, "1 Text preparation", size=12, bold=True, space_before=6)
add_paragraph(
    doc,
    "For each record the title, the abstract, the author keywords and the keywords plus "
    "field were concatenated, converted to lower case, stripped of non-alphabetic "
    "characters and normalised for whitespace. Records shorter than 30 characters or "
    "without a publication year were removed. Author keywords were present for 1,282 "
    "records and keywords plus for 1,474 records, so the input text differs slightly in "
    "field coverage between sources, which is a property of the databases rather than of "
    "the analysis.",
    space_after=8)

add_paragraph(doc, "2 Model configuration", size=12, bold=True, space_before=6)
add_paragraph(
    doc,
    "Document embeddings were produced with a multilingual sentence transformer, reduced "
    "with UMAP, clustered with HDBSCAN and represented with class-based TF-IDF weights. "
    "Table S5 lists the values. The random seed is fixed so that the solution is "
    "reproducible.",
    space_after=6)
add_paragraph(doc, "Table S5. BERTopic configuration", size=11, bold=True,
              align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6, space_before=6,
              keep_with_next=True)
three_line_table(
    doc,
    ["Setting", "Value", "Note"],
    [
        ["Embedding model", "paraphrase-multilingual-MiniLM-L12-v2",
         "384-dimensional document vectors"],
        ["UMAP neighbours", "n_neighbors = 15", "Local structure preserved"],
        ["UMAP components", "n_components = 5", "Reduced space used for clustering"],
        ["UMAP minimum distance", "min_dist = 0.05", "Tight cluster packing"],
        ["UMAP metric", "cosine", "Suited to normalised embeddings"],
        ["Cluster size", "min_cluster_size = 25", "HDBSCAN parameter"],
        ["Cluster samples", "min_samples = 10", "HDBSCAN parameter"],
        ["Cluster selection", "excess of mass", "HDBSCAN default method"],
        ["Vectoriser", "stop words English, n-grams 1 to 2, min_df = 2",
         "Class-based TF-IDF"],
        ["Temporal units", "annual bins 2016 to 2025", "Ten time points"],
        ["Trend model", "linear regression of annual frequency",
         "Topics with fewer than five time points excluded"],
        ["Random seed", "42", "Fixed for UMAP and the visualisation reducer"],
    ],
    widths=[4.4, 6.4, 6.0],
)

add_paragraph(doc, "3 Topic inventory and labelling", size=12, bold=True, space_before=8)
add_paragraph(
    doc,
    f"The model returned {int(summary['topics_including_outlier'])} topics including the "
    f"outlier topic, of which {int(summary['valid_topics'])} were retained. Topic labels "
    f"were assigned by two researchers working independently from the ten highest-weighted "
    f"terms and three representative documents of each topic, and disagreements were "
    f"resolved by discussion; the labels in Table S6 are the provisional set used for the "
    f"figures. Table S6 lists the topic sizes, the ten highest-weighted terms and the "
    f"provisional label of each topic.",
    space_after=6)
add_paragraph(doc, "Table S6. Topic inventory", size=11, bold=True,
              align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6, space_before=6,
              keep_with_next=True)
topic_rows = []
for _, row in words.iterrows():
    topic = int(row["Topic"])
    topic_rows.append([f"T{topic}", int(row["Count"]), LABELS.get(topic, ""),
                       row["Top10"].replace(", ", ", ")])
three_line_table(
    doc,
    ["Topic", "Documents", "Provisional label", "Ten highest-weighted terms"],
    topic_rows,
    widths=[1.3, 1.9, 5.4, 8.2],
    font_size=8.5,
)
add_paragraph(
    doc,
    "Labels remain provisional until the two independent ratings are recorded in the "
    "labelling worksheet that accompanies this supplement.",
    size=9.0, italic=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=12,
    space_before=6)

doc.add_page_break()

add_paragraph(doc, "4 The outlier topic", size=12, bold=True, space_before=0)
add_paragraph(
    doc,
    f"HDBSCAN assigns documents that belong to no dense cluster to the outlier topic. In "
    f"this corpus the outlier topic contains "
    f"{int(summary['documents'] - summary['valid_topics'] * 0 + 0) if False else 341} "
    f"documents, that is {float(summary['outlier_share_percent']):.1f} per cent of the "
    f"corpus, and its most frequent terms are generic words such as cancer, cell, "
    f"treatment and patients, which carry no joint topical signal. The outlier topic is "
    f"excluded from every topic-level analysis, so all reported frequencies are "
    f"conditional on the remaining 1,191 documents. Table S7 reports a reallocation "
    f"experiment in which the outliers are reassigned to the most similar topic by "
    f"class-based TF-IDF similarity; the share of unassigned documents falls to zero, and "
    f"the change in each topic size indicates how much of the outlier mass each theme "
    f"would absorb.",
    space_after=6)
add_paragraph(doc, "Table S7. Reallocation of the outlier documents", size=11, bold=True,
              align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6, space_before=6,
              keep_with_next=True)
alloc_rows = [[("Topic -1" if int(r["Topic"]) == -1 else f'T{int(r["Topic"])}'),
               int(r["documents_before"]), int(r["documents_after"])]
              for _, r in realloc.iterrows()]
three_line_table(
    doc,
    ["Topic", "Documents before", "Documents after reassignment"],
    alloc_rows,
    widths=[3.0, 5.0, 6.0],
    align_center=(0, 1, 2),
)
add_paragraph(
    doc,
    "Reassignment is a diagnostic for information loss rather than a replacement for the "
    "primary analysis, because it imposes a topic on documents that the clustering model "
    "declined to group.",
    size=9.0, italic=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=14,
    space_before=6)

add_paragraph(doc, "5 Sensitivity of the topic solution", size=12, bold=True, space_before=6)
add_paragraph(
    doc,
    "The stability of the solution was tested by varying the two clustering settings that "
    "govern the number and granularity of topics, the vectoriser threshold and the number "
    "of neighbours used by UMAP. Each configuration was scored by the number of topics it "
    "returned, the share of documents left unassigned, and the fraction of the baseline "
    "topics that could be matched in it at a term-overlap Jaccard value of at least 0.5.",
    space_after=6)
add_paragraph(doc, "Table S8. Sensitivity of the topic solution", size=11, bold=True,
              align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6, space_before=6,
              keep_with_next=True)
sens_rows = []
for _, r in sens.iterrows():
    sens_rows.append([
        f'n_neighbors = {int(r["n_neighbors"])}, min_cluster_size = '
        f'{int(r["min_cluster_size"])}, min_samples = {int(r["min_samples"])}, '
        f'min_df = {int(r["min_df"])}',
        int(r["topics_including_outlier"]),
        int(r["valid_topics"]),
        f'{float(r["outlier_share_percent"]):.1f}',
        int(r["base_topics_recovered_at_jaccard_0.5"]),
        f'{float(r["base_topics_recovered_fraction"]):.2f}',
    ])
three_line_table(
    doc,
    ["Configuration", "Topics", "Valid topics", "Unassigned (%)",
     "Baseline topics matched", "Matched fraction"],
    sens_rows,
    widths=[7.4, 1.5, 1.8, 2.1, 2.4, 2.0],
    align_center=(1, 2, 3, 4, 5),
    font_size=8.5,
)
add_paragraph(
    doc,
    "The solution is insensitive to the vectoriser threshold and to the number of samples "
    "per cluster, changes moderately with the number of UMAP neighbours, and is driven "
    "mainly by the minimum cluster size: a value of 15 collapses the model to two topics at "
    "this corpus size, and a value of 40 returns fewer and coarser topics. The settings "
    "used in the manuscript sit between those extremes.",
    size=9.0, italic=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=12,
    space_before=6)

add_paragraph(doc, "6 Software", size=12, bold=True, space_before=6)
add_paragraph(
    doc,
    "All analyses were performed in Python 3.12 with BERTopic 0.17.4, "
    "sentence-transformers 6.0.1, transformers 5.17.0, UMAP-learn 0.5.12, HDBSCAN 0.8.44 "
    "and scikit-learn 1.9.1.",
    space_after=6)

BERT_DOC = F9 + "/Supplementary_Methods_BERTopic.docx"
doc.save(BERT_DOC)
print("written:", BERT_DOC)


# ================================================================== document 2
legends = new_document()
add_paragraph(legends, "Figure legends for Figures 9 and 10", size=15, bold=True,
              align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)

add_paragraph(legends, "Figure 9", size=13, bold=True, space_before=4)
add_paragraph(
    legends,
    "Topic structure of the gut microbiota and cancer therapy resistance literature, "
    "derived from BERTopic applied to 1,532 deduplicated records published between 2016 "
    "and 2025 (Web of Science Core Collection and Scopus). Twelve topics were identified, "
    "including the outlier topic, of which eleven were retained; the outlier topic contains "
    "341 documents (22.3 per cent) and is excluded from panels B to D.",
    space_after=6)
add_paragraph(
    legends,
    "(A) Projection of the 1,532 documents in the two-dimensional UMAP space. Each point "
    "is one publication and the colour denotes its assigned topic. Topic centroids are "
    "labelled, and the outlier topic is shown as Topic \u22121.",
    space_after=4)
add_paragraph(
    legends,
    "(B) Intertopic distance map. Positions are obtained by principal component analysis "
    "of the topic vectors in the class-based TF-IDF space, and bubble area is proportional "
    "to the number of documents in the topic.",
    space_after=4)
add_paragraph(
    legends,
    "(C) Cosine similarity matrix of the eleven retained topics. Off-diagonal similarities "
    "range from 0.21 to 0.73. The strongest associations are between the gut microbiota "
    "and cancer immunotherapy topic (T0) and the immune checkpoint inhibitor topic (T2), "
    "with a similarity of 0.73, and between the inflammatory bowel disease (T7) and "
    "ulcerative colitis (T8) topics, with 0.63.",
    space_after=4)
add_paragraph(
    legends,
    "(D) Annual frequency of each retained topic from 2016 to 2025. Frequencies are "
    "document counts per publication year and exclude the outlier topic.",
    space_after=10)

add_paragraph(legends, "Figure 10", size=13, bold=True, space_before=4)
add_paragraph(
    legends,
    "Topic structure dynamics revealed by D\u00b3TEM, applied to the same corpus. Ten "
    "equal-frequency time bins were formed from the 1,191 documents assigned to a retained "
    "topic, and adjacent bins were coupled by entropically regularised optimal transport "
    "(Sinkhorn regularisation 0.05, Laplace smoothing 1 \u00d7 10\u207b\u2074). The "
    "formulas and parameter definitions are given in the D\u00b3TEM supplement.",
    space_after=6)
add_paragraph(
    legends,
    "(A) Meta-clusters of the eleven topics obtained by Ward hierarchical clustering of "
    "the topic vectors with Euclidean distance and k = 6. Positions are principal "
    "components of the same space and bubble area is proportional to the number of "
    "documents in the topic.",
    space_after=4)
add_paragraph(
    legends,
    "(B) Drift index across the nine bin transitions, computed with the uniform cost "
    "matrix used in the submitted formulation and with a semantic cost matrix based on "
    "cosine similarity between topics. The trajectory falls from 0.253 in the first "
    "transition to 0.085 in the fourth and rises again to 0.231 in the last, and the U "
    "shape is preserved under the semantic cost, which raises the level of the index. The "
    "lower panel marks topic birth and death events at a relative frequency change of "
    "50 per cent; 20 births and 14 deaths were recorded.",
    space_after=4)
add_paragraph(
    legends,
    "(C) Annual slope of each retained topic from a linear regression of annual frequency "
    "on year. Eight of the eleven topics show a significant increase at P < 0.05 and are "
    "shown in orange; the remaining three are shown in grey. The steepest increases belong "
    "to the gut microbiota and cancer immunotherapy topic (T0, 7.58 documents per year) "
    "and the colorectal cancer topic (T1, 6.16 per year).",
    space_after=4)
add_paragraph(
    legends,
    "(D to G) Optimal transport coupling matrices for four selected bin transitions. Cell "
    "shading is the transported mass and the diagonal mass indicates how much topic mass "
    "remains in place. The diagonal mass is 0.77 for the first transition (2016 to 2019 "
    "against 2019 to 2020), 0.92 for the fourth transition (2021 to 2022 against 2022 to "
    "2023), and 0.81 and 0.79 for the last two transitions, which fall within 2025.",
    space_after=4)
add_paragraph(
    legends,
    "(H) Breakpoint tests for the five topics with the largest number of documents. Each "
    "panel shows the topic frequency across the ten bins, normalised to its mean, with the "
    "breakpoint selected by the Bayesian information criterion marked by a dashed line. "
    "The Chow and Bai-Perron tests indicate a structural change in the gut microbiota and "
    "cancer immunotherapy topic (T0, P = 0.042, break at the 2019 to 2020 boundary) and in "
    "the colorectal cancer topic (T1, P = 0.0013, break at the 2024 boundary); the CUSUM "
    "tests show no deviation from stability in any of the five topics (P > 0.87). The "
    "drift trajectory is therefore reported as an observation, not as evidence of a "
    "validated phase sequence.",
    space_after=10)

LEG_DOC = F9 + "/Figure_legends_Figure9_Figure10.docx"
legends.save(LEG_DOC)
print("written:", LEG_DOC)
