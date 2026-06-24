"""The citation schema is the trust spine — lock its contract with tests."""

from parser.schema import CellRef, Value, PassageRef, Passage


def test_cellref_citation_with_header():
    ref = CellRef(file="region_b.xlsx", sheet="Demand", cell="C5", row=5, column="C", header="Product Y")
    assert ref.citation() == "region_b.xlsx · Demand!C5 (Product Y)"


def test_cellref_citation_without_header():
    ref = CellRef(file="f.xlsx", sheet="S", cell="A1", row=1, column="A")
    assert ref.citation() == "f.xlsx · S!A1"


def test_value_to_dict_carries_provenance():
    ref = CellRef(file="region_b.xlsx", sheet="Demand", cell="C5", row=5, column="C", header="Product Y")
    d = Value(value=70, ref=ref).to_dict()
    assert d["value"] == 70
    assert d["file"] == "region_b.xlsx"
    assert d["sheet"] == "Demand"
    assert d["cell"] == "C5"
    assert d["header"] == "Product Y"
    assert d["citation"] == "region_b.xlsx · Demand!C5 (Product Y)"


def test_passage_to_dict_carries_provenance():
    p = Passage(content="Product Y declined.", ref=PassageRef(document="memo.docx", passage=3))
    d = p.to_dict()
    assert d["content"] == "Product Y declined."
    assert d["document"] == "memo.docx"
    assert d["passage"] == 3
    assert d["citation"] == "memo.docx · passage 3"
