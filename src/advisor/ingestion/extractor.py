"""Extractor orchestrator.

``extract_from_grid`` is the pure, testable core that turns a :class:`SheetGrid`
into a canonical :class:`IncomeStatement`. ``extract_income_statement`` is a thin
file-I/O wrapper that adds source provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ..schema import (
    EntityMeta,
    IncomeStatement,
    LineItem,
    OperatingExpenses,
    Period,
    PeriodMeta,
    SourceMeta,
)
from .errors import MissingRequiredLineError, NoPeriodsFoundError
from .labels import LineKey, match_line
from .numbers import is_blank, parse_amount
from .periods import PeriodColumn, detect_period_columns
from .scale import detect_scale
from .workbook import Cell, SheetGrid, load_grid

_OPEX_CATEGORY_KEYS: dict[LineKey, str] = {
    LineKey.OPEX_SELLING_DISTRIBUTION: "selling_distribution",
    LineKey.OPEX_ADMINISTRATIVE: "administrative",
    LineKey.OPEX_OTHER: "other_opex",
}


@dataclass(frozen=True)
class ExtractOptions:
    """Tunable knobs for extraction.

    ``entity`` supplies the company profile (name, currency, fiscal year end);
    the fiscal year end drives period sub-index / YoY alignment.
    """

    sheet: str | None = None
    scale: Decimal | None = None
    label_column: int | None = None
    require_volume: bool = False
    entity: EntityMeta | None = None
    extracted_with: str = "master-of-coin-ingest/1.0"


def extract_income_statement(
    path: str | Path, options: ExtractOptions | None = None
) -> IncomeStatement:
    """Load an .xlsx and extract a canonical :class:`IncomeStatement`."""
    options = options or ExtractOptions()
    p = Path(path)
    grid = load_grid(p, sheet=options.sheet)
    source = SourceMeta(
        source_file=str(p),
        sheet_name=grid.title,
        source_scale=options.scale if options.scale is not None else Decimal("1"),
        extracted_with=options.extracted_with,
    )
    return extract_from_grid(grid, options=options, source=source)


def extract_from_grid(
    grid: SheetGrid, *, options: ExtractOptions, source: SourceMeta | None = None
) -> IncomeStatement:
    """Pure core: build an :class:`IncomeStatement` from an in-memory grid."""
    entity = options.entity if options.entity is not None else EntityMeta()
    label_col = (
        options.label_column if options.label_column is not None else _detect_label_column(grid)
    )
    header_row, period_cols = _find_header(grid, label_col, entity.fiscal_year_end_month)

    scale = detect_scale(_header_texts(grid, header_row), override=options.scale)
    if source is not None and options.scale is None:
        source = source.model_copy(update={"source_scale": scale})

    n = len(period_cols)
    mapped: list[dict[LineKey, Decimal]] = [{} for _ in range(n)]
    opex_items: list[list[LineItem]] = [[] for _ in range(n)]
    extra: list[list[LineItem]] = [[] for _ in range(n)]

    for row in grid.rows[header_row + 1 :]:
        label_cell = _cell_at(row, label_col)
        if label_cell is None or is_blank(label_cell.value):
            continue
        raw_label = str(label_cell.value).strip()
        key = match_line(raw_label, coord=label_cell.coord)
        for idx, pcol in enumerate(period_cols):
            cell = _cell_at(row, pcol.col_index)
            if cell is None:
                continue
            amount = parse_amount(cell.value, coord=cell.coord)
            if amount is None:
                continue
            if key is None:
                extra[idx].append(_item(raw_label, amount * scale, cell))
            elif key == LineKey.VOLUME_MT:
                mapped[idx].setdefault(key, amount)  # MT is not scaled
            elif key in _OPEX_CATEGORY_KEYS:
                mapped[idx].setdefault(key, amount * scale)
                opex_items[idx].append(
                    _item(raw_label, amount * scale, cell, category=_OPEX_CATEGORY_KEYS[key])
                )
            else:
                mapped[idx].setdefault(key, amount * scale)

    periods = [
        _build_period(period_cols[i].meta, mapped[i], opex_items[i], extra[i], options)
        for i in range(n)
    ]
    return IncomeStatement(entity=entity, periods=periods, source=source)


def _item(label: str, amount: Decimal, cell: Cell, *, category: str | None = None) -> LineItem:
    return LineItem(
        label=label, amount=amount, raw_label=label, source_ref=cell.coord, category=category
    )


def _build_period(
    meta: PeriodMeta,
    mapped: dict[LineKey, Decimal],
    opex_items: list[LineItem],
    extra: list[LineItem],
    options: ExtractOptions,
) -> Period:
    revenue = mapped.get(LineKey.REVENUE)
    if revenue is None:
        raise MissingRequiredLineError("revenue", meta.label)
    cogs = mapped.get(LineKey.COGS)
    if cogs is None:
        raise MissingRequiredLineError("cogs", meta.label)
    volume = mapped.get(LineKey.VOLUME_MT)
    if options.require_volume and volume is None:
        raise MissingRequiredLineError("volume_mt", meta.label)

    opex = OperatingExpenses(
        selling_distribution=mapped.get(LineKey.OPEX_SELLING_DISTRIBUTION),
        administrative=mapped.get(LineKey.OPEX_ADMINISTRATIVE),
        other_opex=mapped.get(LineKey.OPEX_OTHER),
        total=mapped.get(LineKey.OPEX_TOTAL),
        items=opex_items,
    )
    return Period(
        meta=meta,
        revenue=revenue,
        cogs=cogs,
        gross_profit=mapped.get(LineKey.GROSS_PROFIT),
        opex=opex,
        operating_profit=mapped.get(LineKey.OPERATING_PROFIT),
        other_income=mapped.get(LineKey.OTHER_INCOME),
        finance_cost=mapped.get(LineKey.FINANCE_COST),
        profit_before_tax=mapped.get(LineKey.PROFIT_BEFORE_TAX),
        tax_expense=mapped.get(LineKey.TAX_EXPENSE),
        net_profit=mapped.get(LineKey.NET_PROFIT),
        volume_mt=volume,
        extra_lines=extra,
    )


def _cell_at(row: tuple[Cell, ...], col: int) -> Cell | None:
    return row[col] if 0 <= col < len(row) else None


def _detect_label_column(grid: SheetGrid) -> int:
    ncols = max((len(r) for r in grid.rows), default=0)
    best_col, best_count = 0, -1
    for col in range(ncols):
        count = 0
        for row in grid.rows:
            cell = _cell_at(row, col)
            if cell is not None and isinstance(cell.value, str) and match_line(cell.value):
                count += 1
        if count > best_count:
            best_col, best_count = col, count
    return best_col


def _find_header(
    grid: SheetGrid, label_col: int, fy_end_month: int
) -> tuple[int, list[PeriodColumn]]:
    for i, row in enumerate(grid.rows):
        header_cells = [(c.col, c.value) for c in row if c.col != label_col]
        try:
            cols = detect_period_columns(
                header_cells, fiscal_year_end_month=fy_end_month, sheet=grid.title
            )
        except NoPeriodsFoundError:
            continue
        return i, cols
    raise NoPeriodsFoundError(grid.title)


def _header_texts(grid: SheetGrid, header_row: int) -> list[str]:
    texts: list[str] = []
    for row in grid.rows[: header_row + 1]:
        texts.extend(str(c.value) for c in row if isinstance(c.value, str))
    return texts
