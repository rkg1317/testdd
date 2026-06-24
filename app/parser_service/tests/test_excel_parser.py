"""Excel parsing must preserve exact cell-address provenance."""

from openpyxl import Workbook

from parser.excel_parser import parse_workbook


def _make_xlsx(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Demand"
    ws.append(["Month", "Product X", "Product Y"])
    ws.append(["Jan", 100, 120])
    ws.append(["Feb", 105, 118])
    wb.save(path)
    return path


def test_parse_returns_one_table_per_sheet(tmp_path):
    p = _make_xlsx(tmp_path / "region_b.xlsx")
    tables = parse_workbook(p)
    assert set(tables) == {"Demand"}
    assert tables["Demand"].headers == ["Month", "Product X", "Product Y"]
    assert len(tables["Demand"].rows) == 2


def test_value_has_correct_cell_address_and_header(tmp_path):
    p = _make_xlsx(tmp_path / "region_b.xlsx")
    table = parse_workbook(p)["Demand"]

    # Jan / Product Y is in cell C2 (col C, row 2) and equals 120.
    jan_y = table.cell(0, "Product Y")
    assert jan_y.value == 120
    assert jan_y.ref.cell == "C2"
    assert jan_y.ref.column == "C"
    assert jan_y.ref.row == 2
    assert jan_y.ref.header == "Product Y"
    assert jan_y.ref.file == "region_b.xlsx"
    assert jan_y.ref.citation() == "region_b.xlsx · Demand!C2 (Product Y)"


def test_column_accessor_returns_values_in_order(tmp_path):
    p = _make_xlsx(tmp_path / "region_b.xlsx")
    table = parse_workbook(p)["Demand"]
    px = [v.value for v in table.column("Product X")]
    assert px == [100, 105]


def test_compact_summary_stays_small(tmp_path):
    p = _make_xlsx(tmp_path / "region_b.xlsx")
    table = parse_workbook(p)["Demand"]
    s = table.compact_summary(sample=3)
    assert s["file"] == "region_b.xlsx"
    assert s["sheet"] == "Demand"
    assert s["n_rows"] == 2
    assert len(s["sample_cells"]) == 3
