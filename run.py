"""Acquire frozen Census inputs and execute the complete notebook from a fresh kernel."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.request

FOLDER = Path(__file__).resolve().parent
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def numeric_digest(frame):
    """Hash date/value pairs independently of CSV formatting and line endings."""
    import pandas as pd
    long = frame.melt("YEAR", var_name="month", value_name="value").dropna()
    long["date"] = pd.to_datetime(long.YEAR.astype(str) + "-" + long.month, format="%Y-%b")
    long = long.sort_values("date")
    payload = "".join(f"{row.date:%Y-%m-%d},{int(row.value)}\n" for row in long.itertuples())
    return hashlib.sha256(payload.encode()).hexdigest()


def census_reconstruction():
    """Rebuild all 354 observations from original Census archives, not FRED services."""
    import pandas as pd
    from pypdf import PdfReader
    manifest = json.loads((FOLDER / "sources.json").read_text())
    cache = FOLDER / ".local" / "census-sources"
    cache.mkdir(parents=True, exist_ok=True)
    inputs = {}
    for spec in manifest["census_archives"]:
        path = cache / spec["file"]
        if not path.exists():
            request = urllib.request.Request(spec["url"], headers={"User-Agent": "retail-portfolio-reproduction"})
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = response.read()
            assert hashlib.sha256(payload).hexdigest() == spec["sha256"], f"Source changed: {path.name}"
            path.write_bytes(payload)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == spec["sha256"], f"Cache mismatch: {path.name}"
        inputs[spec["file"]] = path
    workbook = pd.ExcelFile(inputs["benchsales21.xls"], engine="xlrd")
    assert sorted(workbook.sheet_names) == [str(y) for y in range(1992, 2022)]
    records = {}
    for year in sorted(workbook.sheet_names):
        sheet = pd.read_excel(workbook, sheet_name=year, header=None)
        rows = sheet.index[sheet.iloc[:, 1].astype(str).str.strip().eq("Retail sales, total")]
        assert len(rows) == 2, f"Unexpected source layout for {year}"
        # I am selecting the second Retail total row, under ADJUSTED, not the unadjusted row.
        assert sheet.iloc[:rows[-1], 1].astype(str).str.strip().str.match(r"^ADJUSTED(?:\(\d+\))?$").any()
        values = pd.to_numeric(sheet.iloc[rows[-1], 2:14], errors="coerce").dropna()
        assert len(values) == (3 if year == "2021" else 12)
        for month, value in enumerate(values, 1):
            records[pd.Timestamp(int(year), month, 1)] = int(value)
    assert len(records) == 351
    # I am applying revisions in release order; a later release supersedes an earlier value.
    replacements = []
    for spec in manifest["census_archives"][1:]:
        page = PdfReader(inputs[spec["file"]]).pages[4]
        lines = [re.sub(r"\s+", " ", line).strip() for line in page.extract_text(extraction_mode="layout").splitlines()]
        rows = [line for line in lines if line.startswith("Retail ") and "food" not in line.lower() and re.search(r"\d,\d{3}", line)]
        assert len(rows) == 1, "Could not uniquely identify Table 1's Retail row"
        # The final five columns are adjusted current / previous two / prior-year comparison months.
        values = [int(value.replace(",", "")) for value in re.findall(r"\d[\d,]*", rows[0])[-5:]]
        assert values == spec["adjusted_retail_row_last_five"], "PDF extraction disagrees with verified source row"
        for date, value in zip(spec["adjusted_column_dates"], values):
            stamp = pd.Timestamp(date)
            prior = records.get(stamp)
            records[stamp] = value
            replacements.append({"date": date, "value": value, "previous": prior, "source": spec["file"]})
    series = pd.Series(records).sort_index()
    assert list(series.index) == list(pd.date_range("1992-01-01", "2021-06-01", freq="MS"))
    wide = pd.DataFrame(index=range(1992, 2022), columns=MONTHS, dtype=float)
    for date, value in series.items():
        wide.loc[date.year, MONTHS[date.month - 1]] = value
    wide = wide.rename_axis("YEAR").reset_index()
    assert numeric_digest(wide) == manifest["canonical_numeric_sha256"]
    path = cache / "us_retail_sales.csv"
    wide.to_csv(path, index=False)
    proof = {"acquisition": "Direct Census XLS plus three archived Census release PDFs", "census_files_hash_verified": 4,
             "canonical_numeric_sha256": numeric_digest(wide), "verified_course_observations_equal": 354,
             "census_revision_updates": replacements, "series": "Retail trade sales, excluding food services",
             "unit": "Millions of nominal U.S. dollars", "adjustment": "Seasonal, holiday, trading-day adjusted; not price adjusted",
             "snapshot_vintage": "2021-07-16", "real_time_vintage_backtest": False}
    return wide, path, proof


def load_retail_source():
    """Default is direct Census acquisition; an optional original CSV is never altered."""
    import pandas as pd
    configured = os.environ.get("PROJECT_DATA_DIR")
    if not configured:
        return census_reconstruction()
    manifest = json.loads((FOLDER / "sources.json").read_text())
    path = Path(configured).expanduser() / "us_retail_sales.csv"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["original_course_csv_sha256"], "Not the validated original source snapshot"
    frame = pd.read_csv(path)
    assert numeric_digest(frame) == manifest["canonical_numeric_sha256"]
    proof = {"acquisition": "Original snapshot; canonical values proven identical to direct Census reconstruction",
             "canonical_numeric_sha256": numeric_digest(frame), "verified_course_observations_equal": 354,
             "series": "Retail trade sales, excluding food services", "unit": "Millions of nominal U.S. dollars",
             "adjustment": "Seasonal, holiday, trading-day adjusted; not price adjusted",
             "snapshot_vintage": "2021-07-16", "real_time_vintage_backtest": False}
    return frame, path, proof


def main():
    os.chdir(FOLDER)
    for variable, directory in [("MPLCONFIGDIR", "matplotlib"), ("IPYTHONDIR", "ipython")]:
        location = FOLDER / ".local" / directory
        location.mkdir(parents=True, exist_ok=True)
        os.environ[variable] = str(location)
    import nbformat
    from nbclient import NotebookClient
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    notebook_path = FOLDER / "retail_sales_forecasting.ipynb"
    notebook = nbformat.read(notebook_path, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="retail-notebook-kernel-") as temp:
        kernel = Path(temp) / "kernels" / "python3"
        kernel.mkdir(parents=True)
        (kernel / "kernel.json").write_text(json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "Python 3", "language": "python"}))
        specs = KernelSpecManager(kernel_dirs=[str(kernel.parent)])
        manager = KernelManager(kernel_name="python3", kernel_spec_manager=specs)
        assert manager.kernel_spec.argv[0] == sys.executable
        client = NotebookClient(notebook, timeout=600, km=manager,
                                resources={"metadata": {"path": str(FOLDER)}}, allow_errors=False)
        try:
            client.execute()
        finally:
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
    nbformat.write(notebook, notebook_path)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert all(cell.execution_count is not None for cell in code_cells)
    assert not any(output.output_type == "error" for cell in code_cells for output in cell.outputs)
    evidence_path = FOLDER / "validation.json"
    evidence = json.loads(evidence_path.read_text())
    evidence["execution"] = {"fresh_kernel": True, "executed_code_cells": len(code_cells), "saved_errors": 0, "wall_seconds": time.monotonic() - started, "notebook_sha256": hashlib.sha256(notebook_path.read_bytes()).hexdigest()}
    evidence["release_hashes"] = {name: hashlib.sha256((FOLDER / name).read_bytes()).hexdigest() for name in ["run.py", "requirements.txt", "sources.json", "README.md"]}
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({"project": evidence["project"], "execution": evidence["execution"]}, indent=2))


if __name__ == "__main__":
    main()
