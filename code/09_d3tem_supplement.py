"""Build the D3TEM supplementary methods document (formulas + three-line tables)."""

import os

import pandas as pd
from docx import Document
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt

SRC = r"C:/72.wxjlx-1/Figure10_output"
SENS = SRC + "/sensitivity/sensitivity_d3tem_grid.csv"
DST = r"C:/72.wxjlx-1/Figure10_output/Supplementary_Methods_D3TEM.docx"
FONT = "Times New Roman"


# ------------------------------------------------------------------ helpers
def mr(text):
    return f'<m:r><m:t xml:space="preserve">{text}</m:t></m:r>'


def msub(base, sub):
    return f"<m:sSub><m:e>{base}</m:e><m:sub>{sub}</m:sub></m:sSub>"


def mfrac(num, den):
    return f"<m:f><m:num>{num}</m:num><m:den>{den}</m:den></m:f>"


def add_equation(document, inner, number=None):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(6)
    math = parse_xml(f'<m:oMath {nsdecls("m")}>{inner}</m:oMath>')
    paragraph._p.append(math)
    if number:
        run = paragraph.add_run("   (" + number + ")")
        run.font.name = FONT
        run.font.size = Pt(10.5)
    return paragraph


def style_run(run, size=10.5, bold=False, italic=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)


def add_paragraph(document, text, size=10.5, bold=False, italic=False,
                  align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6,
                  space_before=0, style=None, keep_with_next=False,
                  keep_together=False):
    paragraph = document.add_paragraph(style=style)
    run = paragraph.add_run(text)
    style_run(run, size=size, bold=bold, italic=italic)
    paragraph.alignment = align
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.space_before = Pt(space_before)
    paragraph.paragraph_format.keep_with_next = keep_with_next
    # table notes are the only italic paragraphs, and they should never be split
    # across a page boundary
    paragraph.paragraph_format.keep_together = keep_together or italic
    return paragraph


def keep_rows_together(table):
    """Stop Word from splitting a row across pages."""
    for row in table.rows:
        tr_pr = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        tr_pr.append(cant_split)


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
                     align_center=(), min_row_height=0.5):
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
    header_tr_pr = table.rows[0]._tr.get_or_add_trPr()
    header_tr_pr.append(OxmlElement("w:tblHeader"))
    for row in table.rows:
        row.height = Cm(min_row_height)
        row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
        for cell, width in zip(row.cells, widths):
            cell.width = Cm(width)
    keep_rows_together(table)
    return table


# ------------------------------------------------------------------ data
drift_u = pd.read_csv(SRC + "/Figure10B_drift_uniform.csv", encoding="utf-8-sig")
drift_s = pd.read_csv(SRC + "/Figure10B_drift_semantic.csv", encoding="utf-8-sig")
breaks = pd.read_csv(SRC + "/Figure10H_breakpoints.csv", encoding="utf-8-sig")
grid = pd.read_csv(SENS, encoding="utf-8-sig")
bins = pd.read_csv(SRC + "/Figure10B_bin_frequencies.csv", encoding="utf-8-sig")

n_bins = len(bins)
n_topics = len([c for c in bins.columns if c.startswith("T")])

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
for style_name in ("Title", "Heading 1", "Heading 2"):
    style = doc.styles[style_name]
    style.font.name = FONT
    style.font.color.rgb = None
    style.font.color.theme_color = None

add_paragraph(doc, "Supplementary methods for the D\u00b3TEM analysis of topic structure dynamics",
              size=15, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
add_paragraph(
    doc,
    "This supplement documents the Dynamic Three-dimensional Topic Evolution Model "
    "(D\u00b3TEM) applied to the final corpus of 1,532 deduplicated records published between "
    "2016 and 2025. It states the formulas, the parameter values and the sensitivity "
    "analyses, so that the drift index and the lifecycle results reported in Figure 10 can "
    "be reproduced and audited. All analyses were performed in Python 3.12 with BERTopic "
    "0.17.4, SciPy 1.18.1, POT 0.9.7 and statsmodels 0.15.0.",
    space_after=12)

add_paragraph(doc, "1 Input from topic modelling", size=12, bold=True, space_before=6)
add_paragraph(
    doc,
    f"Stage 1 reuses the BERTopic solution described in the main Methods. Each topic is "
    f"represented by its class-based TF-IDF vector over the full vocabulary, and the "
    f"{n_topics} valid topics are used as the units of all later stages. The outlier topic, "
    f"which contains 341 documents (22.3 per cent of the corpus), is excluded because it "
    f"carries no shared topical signal. Let u\u1d62 denote the c-TF-IDF vector of topic i.",
    space_after=8)

add_paragraph(doc, "2 Ward meta-clustering of topics", size=12, bold=True, space_before=6)
add_paragraph(
    doc,
    "Topics are clustered with Ward linkage on Euclidean distances, which merges the pair "
    "of clusters whose merge increases the within-cluster sum of squares the least:",
    space_after=4)
add_equation(
    doc,
    mr("\u0394(A,B) = ") + mfrac(mr("|A| |B|"), mr("|A| + |B|"))
    + mr(" \u2016") + msub(mr("c"), mr("A")) + mr(" \u2212")
    + msub(mr("c"), mr("B")) + mr("\u2016") + mr("\u00b2"),
    "1")
add_paragraph(
    doc,
    "where |A| and |B| are cluster sizes and the centroids are the cluster means. The number "
    "of meta-clusters was set to k = 6. Because the drift index defined below acts on the "
    "topic distribution rather than on the clustering, k affects only the description of "
    "the knowledge architecture and not the drift trajectory, which is confirmed in Table S4.",
    space_after=8)

add_paragraph(doc, "3 Equal-frequency time bins", size=12, bold=True, space_before=6)
add_paragraph(
    doc,
    f"The corpus is sorted by publication year and divided into B = {n_bins} bins of equal "
    f"document count rather than equal calendar width, so that every bin carries comparable "
    f"statistical weight. The midpoint of a bin is the mean publication year of its "
    f"documents. Let a = (a\u2081, ..., a\u2099) and b = (b\u2081, ..., b\u2099) be the topic frequency "
    f"distributions of two adjacent bins, each summing to one.",
    space_after=8)

add_paragraph(doc, "4 Entropic optimal transport between adjacent bins", size=12, bold=True,
              space_before=6)
add_paragraph(
    doc,
    "Both marginals are smoothed with a Laplace term before transport, which prevents zero "
    "probabilities from making the transport plan degenerate:",
    space_after=4)
add_equation(
    doc,
    msub(mr("a\u0303"), mr("i")) + mr(" = ")
    + mfrac(msub(mr("a"), mr("i")) + mr(" + \u03b5"),
            mr("\u03a3") + msub(mr("a"), mr("j")) + mr(" + \u03b5")),
    "2")
add_paragraph(
    doc,
    "with \u03b5 = 1 \u00d7 10\u207b\u2074. The transport plan is the solution of the "
    "entropically regularised problem",
    space_after=4)
add_equation(
    doc,
    msub(mr("\u03c0"), mr("*")) + mr(" = arg min ") + msub(mr("\u03c0"), mr(""))
    + mr(" \u27e8\u03c0, C\u27e9 + \u03bb \u03a3") + msub(mr("\u03c0"), mr("ij"))
    + mr(" (ln ") + msub(mr("\u03c0"), mr("ij")) + mr(" \u2212 1)"),
    "3")
add_paragraph(
    doc,
    "\u03c0 is constrained to the set of matrices with row sums a\u0303 and column sums "
    "b\u0303. The problem is solved with the log-stabilised Sinkhorn algorithm "
    "(ot.sinkhorn in POT) at regularisation \u03bb = 0.05. Two cost matrices are reported. "
    "The first reproduces the submitted formulation, in which every cross-topic transfer "
    "costs the same:",
    space_after=4)
add_equation(
    doc,
    msub(mr("C"), mr("ij")) + mr(" = 0.5 if i = j, and 1.0 if i \u2260 j"),
    "4")
add_paragraph(
    doc,
    "Because that matrix is uniform off the diagonal, the resulting index can only reflect "
    "a change in topic proportions, not semantic movement between topics. A second, semantic "
    "cost matrix is therefore reported alongside it, in which the cost of transferring mass "
    "between two topics follows their cosine similarity in the c-TF-IDF space:",
    space_after=4)
add_equation(
    doc,
    msub(mr("C"), mr("ij")) + mr(" = 1 \u2212 0.5 cos(") + msub(mr("u"), mr("i"))
    + mr(", ") + msub(mr("u"), mr("j")) + mr(")"),
    "5")

add_paragraph(doc, "5 Drift index", size=12, bold=True, space_before=6)
add_paragraph(
    doc,
    f"The drift index summarises how much topic mass fails to remain in place between two "
    f"adjacent bins:",
    space_after=4)
add_equation(
    doc,
    mr("d = ") + mfrac(mr("1 \u2212 tr(\u03c0)"), mr("1 \u2212 1 / n")),
    "6")
add_paragraph(
    doc,
    f"where tr(\u03c0) is the mass transported along the diagonal and n = {n_topics} is the "
    f"number of valid topics. The index equals 0 when the topic distribution is unchanged and "
    f"approaches n / (n \u2212 1) = {n_topics / (n_topics - 1):.3f} when the distribution is "
    f"completely reorganised. Under the published uniform cost the index measures "
    f"proportional reorganisation of topic mass; under the semantic cost it additionally "
    f"penalises movement between semantically distant topics.",
    space_after=8)

add_paragraph(doc, "6 Topic birth and death", size=12, bold=True, space_before=6)
add_paragraph(
    doc,
    "A topic is recorded as born or dead in a bin transition when its relative frequency "
    "changes beyond a fixed threshold:",
    space_after=4)
add_equation(
    doc,
    msub(mr("\u0394"), mr("i")) + mr(" = ")
    + mfrac(msub(mr("b"), mr("i")) + mr(" \u2212 ") + msub(mr("a"), mr("i")),
            msub(mr("a"), mr("i"))),
    "7")
add_paragraph(
    doc,
    "with birth when \u0394\u1d62 \u2265 \u03b8 and death when \u0394\u1d62 \u2264 \u2212\u03b8, "
    "where \u03b8 = 0.50. The threshold is a reporting convention rather than a fitted "
    "parameter, and Table S4 shows how the event count responds to \u03b8 = 0.40 and "
    "\u03b8 = 0.60.",
    space_after=8)

add_paragraph(doc, "7 Structural breakpoint tests", size=12, bold=True, space_before=6)
add_paragraph(
    doc,
    "Three tests are applied to the frequency series of the five topics with the largest "
    "number of documents. The Chow test compares a pooled regression with two segment "
    "regressions at a candidate break,",
    space_after=4)
add_equation(
    doc,
    mr("F = ")
    + mfrac(
        mr("[") + msub(mr("RSS"), mr("p")) + mr(" \u2212 (")
        + msub(mr("RSS"), mr("1")) + mr(" + ") + msub(mr("RSS"), mr("2")) + mr(")] / k"),
        mr("(") + msub(mr("RSS"), mr("1")) + mr(" + ") + msub(mr("RSS"), mr("2"))
        + mr(") / (n \u2212 2k)")),
    "8")
add_paragraph(
    doc,
    "where k is the number of parameters per segment. The Bai-Perron style search selects "
    "the single breakpoint that minimises",
    space_after=4)
add_equation(
    doc,
    mr("BIC(m) = n ln(") + msub(mr("RSS"), mr("m")) + mr(" / n) + p ln n"),
    "9")
add_paragraph(
    doc,
    "and the CUSUM test is applied to the OLS recursive residuals with 5 per cent "
    "significance bounds (breaks_cusumolsresid in statsmodels). All three tests were "
    "implemented in statsmodels 0.15.0. Their outcomes are reported as they stand, including "
    "the non-significant results, and no phase boundary is declared on the basis of the "
    "drift trajectory alone.",
    space_after=10)

add_paragraph(doc, "Table S1. D\u00b3TEM parameter definitions", size=11, bold=True,
              align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6, space_before=12,
              keep_with_next=True)
three_line_table(
    doc,
    ["Parameter", "Symbol", "Value", "Basis"],
    [
        ["Number of time bins", "B", n_bins, "Equal document count per bin"],
        ["Binning scheme", "\u2013", "equal frequency", "Equal statistical weight per bin"],
        ["Number of meta-clusters", "k", 6, "Reported in the submitted formulation"],
        ["Laplace smoothing", "\u03b5", "1 \u00d7 10\u207b\u2074",
         "Numerical stability of the marginals"],
        ["Sinkhorn regularisation", "\u03bb", 0.05, "Submitted value, justified in Table S4"],
        ["Uniform transport cost", "C", "0.5 diagonal, 1.0 off diagonal",
         "Submitted formulation, retained for comparability"],
        ["Semantic transport cost", "C",
         "1 \u2212 0.5 \u00d7 topic similarity",
         "Added to test semantic reorganisation, equation 5"],
        ["Birth and death threshold", "\u03b8", 0.50, "Submitted value, tested in Table S4"],
        ["Valid topics", "n", n_topics, "Topics retained after removing the outlier topic"],
    ],
    widths=[4.6, 1.6, 4.6, 6.2],
    align_center=(1,),
)
add_paragraph(
    doc,
    "The outlier topic is excluded from every stage, so all frequencies are conditional on "
    "the 1,191 documents assigned to a valid topic.",
    size=9.0, italic=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=16,
    space_before=6)

add_paragraph(doc, "Table S2. Drift index for each bin transition", size=11, bold=True,
              align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6, space_before=12,
              keep_with_next=True)
drift_rows = []
for i in range(len(drift_u)):
    drift_rows.append([
        i + 1,
        drift_u["transition"][i],
        f'{drift_u["drift_index"][i]:.4f}',
        f'{drift_u["diagonal_mass"][i]:.4f}',
        f'{drift_s["drift_index"][i]:.4f}',
        f'{drift_s["diagonal_mass"][i]:.4f}',
    ])
three_line_table(
    doc,
    ["Step", "Time bins", "d, uniform cost", "tr(\u03c0), uniform",
     "d, semantic cost", "tr(\u03c0), semantic"],
    drift_rows,
    widths=[1.4, 4.6, 2.7, 2.7, 2.7, 2.7],
    align_center=(0, 2, 3, 4, 5),
)
add_paragraph(
    doc,
    "The trajectory is U-shaped under both cost matrices: it falls from the first to the "
    "fourth transition and rises again towards the end of the period. The semantic cost "
    "raises the level of the index without changing its shape.",
    size=9.0, italic=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=16,
    space_before=6)

add_paragraph(doc, "Table S3. Breakpoint tests for the five core topics", size=11, bold=True,
              align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6, space_before=12,
              keep_with_next=True)
break_rows = [[
    f'T{int(r["topic"])}',
    f'{r["chow_F"]:.3f}' if pd.notna(r["chow_F"]) else "na",
    f'{r["chow_P"]:.4f}' if pd.notna(r["chow_P"]) else "na",
    f'{r["bai_perron_break_midpoint"]:.2f}'
    if pd.notna(r["bai_perron_break_midpoint"]) else "na",
    f'{r["bai_perron_P"]:.4f}' if pd.notna(r["bai_perron_P"]) else "na",
    f'{r["cusum_statistic"]:.4f}' if pd.notna(r["cusum_statistic"]) else "na",
    f'{r["cusum_P"]:.4f}' if pd.notna(r["cusum_P"]) else "na",
] for _, r in breaks.iterrows()]
three_line_table(
    doc,
    ["Topic", "Chow F", "Chow P", "Break midpoint", "Bai-Perron P",
     "CUSUM statistic", "CUSUM P"],
    break_rows,
    widths=[1.5, 1.8, 1.8, 2.6, 2.4, 2.6, 1.9],
    align_center=(0, 1, 2, 3, 4, 5, 6),
)
add_paragraph(
    doc,
    "The Chow and Bai-Perron tests identify a structural change in two of the five core "
    "topics (T0 at the 2019 to 2020 boundary and T1 at the 2024 boundary), while the CUSUM "
    "tests do not indicate a deviation from stability in any topic. The evidence is "
    "therefore mixed and topic-specific, and it is reported as such rather than as "
    "confirmation of a shared phase boundary.",
    size=9.0, italic=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=16,
    space_before=6)

add_paragraph(doc, "Table S4. Sensitivity of the drift index to the analysis settings",
              size=11, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6,
              space_before=12, keep_with_next=True)
grid_rows = []
for _, r in grid.iterrows():
    configuration = (f'k = {int(r["k"])}, {str(r["scheme"]).replace("_", " ")}, '
                     f'{r["cost"]} cost, \u03bb = {r["reg"]:g}, '
                     f'\u03b8 = {r["threshold"]:g}')
    grid_rows.append([
        configuration,
        f'{r["mean_drift"]:.4f}',
        f'{r["min_drift"]:.4f}',
        f'{r["max_drift"]:.4f}',
        "yes" if bool(r["U_shape_preserved"]) else "no",
        int(r["birth_events"]),
        int(r["death_events"]),
    ])
three_line_table(
    doc,
    ["Configuration", "Mean d", "Min d", "Max d", "U shape", "Births", "Deaths"],
    grid_rows,
    widths=[8.4, 1.5, 1.4, 1.4, 1.4, 1.3, 1.4],
    align_center=(1, 2, 3, 4, 5, 6),
    font_size=9.0,
)
add_paragraph(
    doc,
    "The drift index is invariant to the number of meta-clusters, because k does not enter "
    "the transport problem. Raising the Sinkhorn regularisation from 0.05 to 0.20 inflates "
    "the index to 0.47 by over-smoothing the transport plan, which supports keeping "
    "\u03bb = 0.05. Equal-width binning and the semantic cost change the level but not the "
    "shape of the trajectory. The U shape is preserved in all eleven configurations.",
    size=9.0, italic=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=12,
    space_before=6)

add_paragraph(doc, "Notes on interpretation", size=12, bold=True, space_before=8)
add_paragraph(
    doc,
    "First, the drift index quantifies how much topic mass moves between adjacent bins. It "
    "is not a measure of semantic distance unless the semantic cost matrix is used, and both "
    "are reported here for that reason.",
    space_after=4)
add_paragraph(
    doc,
    "Second, equal-frequency bins cover unequal calendar intervals, so the early bins span "
    "several years while the last bins cover a single year. Within-bin frequencies should "
    "therefore be read as shares of a fixed number of documents, not as annual rates. Annual "
    "rates are reported separately from the publication-year counts.",
    space_after=4)
add_paragraph(
    doc,
    "Third, the U-shaped trajectory is an observation about the data, not a validated "
    "sequence of phases. The breakpoint tests reported in Table S3 are the appropriate test "
    "of that stronger claim, and they do not support a common change point.",
    space_after=4)

doc.save(DST)
print("written:", DST)
print("bins:", n_bins, "| topics:", n_topics, "| sensitivity configurations:", len(grid))
