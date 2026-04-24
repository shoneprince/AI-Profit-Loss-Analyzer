"""
financial_keywords.py
=====================
Central keyword registry for financial statement label matching.

All keyword lists in kpi_engine.py, cleaner.py, financial_chunker.py,
and server.py are sourced from here so there is ONE place to update.

Coverage:
  - US GAAP (10-K, 10-Q)
  - Indian MCA Schedule III (Annual Reports) — including space variants around "/"
  - IFRS / UK GAAP
  - SME / startup P&Ls
  - Hospitality, Manufacturing, Services, SaaS, Retail, NBFC/Financial Services verticals
  - Multi-period comparison statements
  - OCR noise variants (spacing, slashes, brackets, typos)

Changelog v2:
  - Added "profit / (loss) for the year" with spaces (Indian MCA OCR variant)
  - Added NBFC revenue lines: interest income, dividend income, fair value gains,
    fees commission and other services
  - Added hospitality: food cost, beverage cost, room supplies, laundry
  - Added "total revenue" as standalone revenue keyword
  - Removed "pat" from NET_INCOME_KEYWORDS (false-positive on "particulars")
  - Added "profit for the year (a)" for Jio Financial style
  - Added "total tax expenses" to TAX_KEYWORDS
  - Added impairment on financial instruments to DEPRECIATION_KEYWORDS
  - Added raw material consumption variants
"""

# ════════════════════════════════════════════════════════════════════
# REVENUE
# ════════════════════════════════════════════════════════════════════
REVENUE_KEYWORDS = [
    # Generic
    "revenue", "revenues", "total revenue", "total revenues",
    "net revenue", "net revenues", "gross revenue", "gross revenues",
    # Sales variants
    "sales", "net sales", "gross sales", "total sales",
    "product sales", "service sales", "merchandise sales",
    # Operations-specific (Indian MCA, IFRS)
    "revenue from operations", "revenues from operations",
    "income from operations", "net income from operations",
    "total income from operations",
    "total operating revenue", "total operating revenues",
    # Turnover (UK/IFRS)
    "turnover", "net turnover", "total turnover",
    # Industry-specific
    "fee revenue", "fee income", "subscription revenue",
    "contract revenue", "room revenue",                            # hospitality
    "food and beverage revenue", "f&b revenue",
    "license revenue", "royalty revenue", "royalties",
    "premium income", "premium revenue",                          # insurance
    "grant income",
    # NBFC / Financial Services
    "interest income", "interest earned", "interest received",
    "dividend income", "dividend received",
    "fees commission and other services",
    "fees, commission and other services",
    "net gain on fair value changes",
    "gain on fair value changes",
    "net gain on sale of investments",
    "interest and fee income",                                    # banking
    # Segment / other
    "operating revenue", "operating revenues",
    "service revenue", "service revenues",
    "product revenue", "product revenues",
    # OCR noise
    "reuenue", "revnue", "rev.",
]

# ════════════════════════════════════════════════════════════════════
# OTHER INCOME  (non-operating)
# ════════════════════════════════════════════════════════════════════
OTHER_INCOME_KEYWORDS = [
    "other income", "other operating income",
    "non-operating income", "non operating income",
    "miscellaneous income", "sundry income",
    "income from investments",
    "gain on sale", "gain on disposal", "profit on sale of assets",
    "profit on disposal",
    "foreign exchange gain", "forex gain", "exchange gain",
    "rental income",
    "write-back", "liabilities written back",
    "insurance claim",
    "scrap sales",
]

# ════════════════════════════════════════════════════════════════════
# COST OF GOODS SOLD / COST OF REVENUE
# ════════════════════════════════════════════════════════════════════
COGS_KEYWORDS = [
    # Classic US
    "cost of goods sold", "cost of goods", "cogs",
    "cost of sales", "cost of revenue",
    "cost of products", "cost of products sold",
    "cost of services", "cost of services rendered",
    # Indian / manufacturing
    "cost of material consumed", "cost of materials consumed",
    "cost of raw material consumed", "raw material consumed",
    "material consumed", "materials consumed",
    "raw material consumption", "raw material cost", "material cost",
    "cost of material",
    "cost of merchandise sold", "cost of merchandise",
    "purchases", "purchases of stock-in-trade",
    "purchase of traded goods", "cost of traded goods",
    # Construction / project
    "contract costs", "project costs", "direct project costs",
    "subcontractor costs", "sub-contractor costs",
    # Hospitality / F&B
    "food and beverage costs", "f&b costs",
    "cost of food consumed", "cost of beverages consumed",
    "food cost", "beverage cost",
    # Retail
    "cost of products purchased",
    # SaaS / tech
    "cost of subscription revenue", "hosting costs", "infrastructure costs",
    # OCR noise
    "c.o.g.s", "cost of good sold",
]

# ════════════════════════════════════════════════════════════════════
# INVENTORY CHANGES
# ════════════════════════════════════════════════════════════════════
INVENTORY_CHANGE_KEYWORDS = [
    "changes in inventory", "change in inventory",
    "changes in inventories", "change in inventories",
    "changes in inventory of finished goods",
    "change in inventories of finished goods",
    "changes in stocks", "change in stocks",
    "increase / decrease in stocks", "increase/decrease in stocks",
    "(increase)/decrease in stock", "(increase) / decrease in stock",
    "opening stock", "closing stock",
    "movement in inventory",
    "change in inventories of wip",
    "change in inventories of work-in-progress",
]

# ════════════════════════════════════════════════════════════════════
# GROSS PROFIT
# ════════════════════════════════════════════════════════════════════
GROSS_PROFIT_KEYWORDS = [
    "gross profit", "gross margin", "gross income",
    "gross profit / (loss)", "gross profit/(loss)",
    "gross profit / loss",
    "contribution", "contribution margin",
]

# ════════════════════════════════════════════════════════════════════
# EMPLOYEE / STAFF COSTS
# ════════════════════════════════════════════════════════════════════
EMPLOYEE_COST_KEYWORDS = [
    # Indian MCA
    "employee benefits expense", "employee benefit expense",
    "employees benefit expenses", "employees benefit expense",
    "employee benefits cost", "employee benefit cost",
    "employees benefit cost",
    # Generic
    "staff costs", "staff expenses", "personnel expenses",
    "payroll", "payroll expenses", "payroll costs",
    "wages", "wages and salaries", "salaries and wages",
    "salaries", "salary expense",
    "compensation", "compensation and benefits",
    "employee compensation", "labour costs", "labor costs",
    "manpower costs",
    # Executive
    "director remuneration", "directors remuneration",
    # Benefits
    "provident fund", "gratuity", "pension costs",
    "employee provident fund", "epf",
    "esic", "esi contribution",
    # Contract labour
    "contract labour", "contract labor",
    "casual labour", "temporary staff",
    "engineering costs",
]

# ════════════════════════════════════════════════════════════════════
# DEPRECIATION & AMORTISATION
# ════════════════════════════════════════════════════════════════════
DEPRECIATION_KEYWORDS = [
    "depreciation", "depreciation expense",
    "depreciation and amortization", "depreciation and amortization expense",
    "depreciation and amortisation", "depreciation and amortisation expense",
    "d&a", "d & a",
    "amortization", "amortization expense",
    "amortisation", "amortisation expense",
    "amortization of intangibles",
    "depletion", "depletion and amortization",
    "impairment", "impairment of assets", "goodwill impairment",
    "impairment on financial instruments",
    "impairment loss on financial instruments",
    "write-off", "asset write-off",
    "right-of-use asset depreciation", "rou depreciation",
    "lease depreciation",
]

# ════════════════════════════════════════════════════════════════════
# FINANCE COSTS / INTEREST EXPENSE
# ════════════════════════════════════════════════════════════════════
FINANCE_COST_KEYWORDS = [
    # Indian MCA
    "finance costs", "finance cost", "finance charges",
    "finance and bank charges",
    # US / generic
    "interest expense", "interest expenses",
    "interest and finance charges", "interest charges",
    "interest on borrowings", "interest on loans",
    "interest on term loan", "interest on working capital",
    "bank charges", "bank interest", "bank fees",
    "borrowing costs", "cost of debt",
    # Lease
    "interest on lease liabilities", "lease interest",
    # Other
    "financial expenses", "financial charges",
    "debt issuance costs",
    "loss on extinguishment of debt",
]

# ════════════════════════════════════════════════════════════════════
# SELLING, GENERAL & ADMINISTRATIVE (SG&A)
# ════════════════════════════════════════════════════════════════════
SGA_KEYWORDS = [
    "sg&a", "sga", "s,g&a", "s.g.a",
    "selling general and administrative",
    "selling, general and administrative",
    "selling, general & administrative",
    "general and administrative", "general & administrative",
    "g&a", "g & a",
    "selling expenses", "selling costs",
    "distribution expenses", "distribution costs",
    "administrative expenses", "administrative costs",
    "admin expenses", "admin costs", "administration expenses",
    "overhead", "overheads", "general overheads",
    "office expenses", "office costs",
    "corporate expenses", "corporate overhead",
]

# ════════════════════════════════════════════════════════════════════
# MARKETING & ADVERTISING
# ════════════════════════════════════════════════════════════════════
MARKETING_KEYWORDS = [
    "marketing", "marketing expenses", "marketing costs",
    "advertising", "advertising expenses", "advertising costs",
    "marketing and advertising",
    "sales and marketing", "sales & marketing",
    "promotional expenses", "promotions",
    "business development", "biz dev",
    "brand expenses",
    "digital marketing",
    "public relations", "pr expenses",
    "trade shows", "conferences",
]

# ════════════════════════════════════════════════════════════════════
# RESEARCH & DEVELOPMENT
# ════════════════════════════════════════════════════════════════════
RD_KEYWORDS = [
    "research and development", "research & development",
    "r&d", "r & d", "r and d",
    "research and development expense",
    "research expense", "development expense",
    "product development", "technology development",
    "innovation expense",
]

# ════════════════════════════════════════════════════════════════════
# OTHER OPERATING EXPENSES  (catch-all)
# ════════════════════════════════════════════════════════════════════
OTHER_EXPENSE_KEYWORDS = [
    "other expenses", "other operating expenses",
    "other costs", "other expenditure",
    "miscellaneous expenses", "sundry expenses",
    "general expenses",
    "rent", "rent expense", "rent and rates",
    "utilities", "electricity", "power and fuel",
    "insurance", "insurance expense", "insurance premium",
    "repairs", "repairs and maintenance",
    "maintenance", "maintenance costs",
    "professional fees", "legal fees", "audit fees",
    "consulting fees", "consultancy fees",
    "travelling", "travel expenses", "travel and entertainment",
    "conveyance", "conveyance expense",
    "communication", "telephone", "internet expense",
    "printing and stationery", "office supplies",
    "vehicle expenses", "vehicle running costs",
    "security", "security expenses",
    "housekeeping", "cleaning expenses",
    "rates and taxes",
    "license fees",
    # Hospitality specific
    "laundry expenses", "linen expenses", "guest supplies",
    "room supplies",
]

# ════════════════════════════════════════════════════════════════════
# TOTAL OPERATING EXPENSES
# ════════════════════════════════════════════════════════════════════
TOTAL_OPEX_KEYWORDS = [
    "total expenses", "total operating expenses",
    "total expenditure", "total costs",
    "opex", "total opex",
    "total cost of operations",
    "total cost of revenue",
]

# ════════════════════════════════════════════════════════════════════
# OPERATING INCOME / EBIT
# ════════════════════════════════════════════════════════════════════
OPERATING_INCOME_KEYWORDS = [
    "operating income", "operating profit",
    "ebit", "e.b.i.t",
    "profit from operations", "income from operations",
    "operating earnings",
    "profit before interest and tax", "pbit",
    "profit before interest, tax", "profit before interest & tax",
    "net operating income", "noi",
    # Indian MCA
    "operating profit before working capital changes",
    "profit before exceptional items",
    "profit before exceptional and extraordinary items",
    "profit before exceptional & extraordinary items",
    "profit before exceptional & extraordinary items and tax",
    "profit before exceptional items and tax",
]

# ════════════════════════════════════════════════════════════════════
# EBITDA
# ════════════════════════════════════════════════════════════════════
EBITDA_KEYWORDS = [
    "ebitda", "e.b.i.t.d.a",
    "earnings before interest, taxes, depreciation and amortization",
    "earnings before interest taxes depreciation and amortization",
    "adjusted ebitda", "normalised ebitda", "normalized ebitda",
    "ebitda margin",
]

# ════════════════════════════════════════════════════════════════════
# PROFIT BEFORE TAX (PBT)
# ════════════════════════════════════════════════════════════════════
PBT_KEYWORDS = [
    "profit before tax", "profit before taxation",
    # Indian MCA — with and without spaces around "/"
    "profit / (loss) before tax",
    "profit/(loss) before tax",
    "profit/loss before tax",
    "profit / (loss) before taxation",
    "income before tax", "income before income tax",
    "earnings before tax", "ebt",
    "net profit before tax",
    # Indian MCA exceptional items
    "profit before exceptional & extraordinary items and tax",
    "profit before exceptional and extraordinary items and tax",
    "profit before extraordinary items and tax",
    "profit before extraordinary item",
    "profit / (loss) before extraordinary item",
    "profit/(loss) before extraordinary item",
    # Loss variants
    "loss before tax", "loss / (profit) before tax",
    "(loss)/profit before tax",
]

# ════════════════════════════════════════════════════════════════════
# TAX EXPENSE
# ════════════════════════════════════════════════════════════════════
TAX_KEYWORDS = [
    "tax expense", "tax expenses",
    "income tax", "income tax expense",
    "income tax provision", "provision for income tax",
    "provision for taxes", "provision for income taxes",
    "tax charge", "tax on profit",
    "total tax expenses", "total tax expense",
    # Components
    "current tax", "current income tax",
    "deferred tax", "deferred income tax",
    "deferred tax charge", "deferred tax credit",
    "deferred tax charge/ (credit)",
    "mat", "mat credit", "mat credit entitlement",
    "minimum alternate tax",
    # International
    "corporate tax", "corporation tax",
    "withholding tax",
    "tax related to earlier years", "prior year tax",
    # Indian specific
    "tax expense of continuing operation",
    "tax of continuing operations",
    "taxes relating to prior years",
    "taxes related to prior years",
]

# ════════════════════════════════════════════════════════════════════
# NET INCOME / NET PROFIT (BOTTOM LINE)
#
# NOTE: "pat" (Profit After Tax abbreviation) is intentionally NOT
# included as a standalone 3-letter keyword because it causes
# false-positive matches against "particulars" (the header row in
# Indian MCA statements). PAT is handled via fuzzy matching in
# kpi_engine.py (SequenceMatcher threshold 0.82).
# ════════════════════════════════════════════════════════════════════
NET_INCOME_KEYWORDS = [
    # Generic
    "net income", "net profit", "net earnings",
    "net loss",
    # After-tax
    "profit after tax", "profit after taxation",
    "profit / (loss) after tax",
    "profit/(loss) after tax",
    "income after tax", "earnings after tax",
    "net income after tax",
    # Indian MCA — standard and OCR space variants around "/"
    "profit for the year",
    "profit/(loss) for the year",
    "profit / (loss) for the year",
    "profit / loss for the year",
    "loss for the year",
    "loss / (profit) for the year",
    "profit/loss for the year",
    # Continuing operations (Indian MCA, IFRS)
    "profit from continuing operation",
    "profit from continuing operation (after tax)",
    "profit from continuing operations",
    "profit from continuing operations (after tax)",
    "profit from continuing operation after tax",
    # Net profit variants
    "net profit for the year",
    "net profit / (loss)",
    "net profit/(loss)",
    "(loss)/profit",
    "profit/(loss)",
    # NBFC / Jio Financial style
    "profit for the year (a)",
    # Non-profits
    "net surplus", "surplus for the year",
    # Attribution
    "profit attributable to shareholders",
    "profit attributable to equity holders",
    "comprehensive income",
    "total comprehensive income",
    # OCR noise
    "net incorne", "net prolit",
]

# ════════════════════════════════════════════════════════════════════
# BALANCE SHEET — completeness (not used in P&L KPIs)
# ════════════════════════════════════════════════════════════════════
TOTAL_ASSETS_KEYWORDS = [
    "total assets", "total asset",
]
TOTAL_LIABILITIES_KEYWORDS = [
    "total liabilities", "total liability",
    "total liabilities and equity", "total liabilities and shareholders equity",
]
EQUITY_KEYWORDS = [
    "total equity", "shareholders equity", "stockholders equity",
    "total shareholders funds", "net worth",
    "total net assets",
]
CASH_KEYWORDS = [
    "cash and cash equivalents", "cash & cash equivalents",
    "cash and equivalents", "cash",
    "closing cash", "closing cash and cash equivalents",
]
DEBT_KEYWORDS = [
    "long-term debt", "long term debt", "long-term borrowings",
    "long term borrowings", "short-term borrowings",
    "short term borrowings", "total borrowings",
    "total debt", "bank overdraft",
]

# ════════════════════════════════════════════════════════════════════
# EARNINGS PER SHARE (EPS)
# ════════════════════════════════════════════════════════════════════
EPS_KEYWORDS = [
    "earnings per share", "eps",
    "basic eps", "diluted eps",
    "basic earnings per share", "diluted earnings per share",
    "basic and diluted earnings per share",
    "earnings per equity share",
    "basic earning per share", "diluted earning per share",
    "basic and diluted (in rs)",
]

# ════════════════════════════════════════════════════════════════════
# ROWS TO SKIP / IGNORE
# ════════════════════════════════════════════════════════════════════
SKIP_ROW_KEYWORDS = [
    "particulars", "description", "line item",
    "sr no", "sr. no", "serial no",
    "note no", "note no.", "schedule no",
    "in thousands", "in millions",
    "in hundreds", "in lakhs", "in crores",
    "auditor", "director", "signature",
    "significant accounting", "accounting policies",
    "basis of preparation",
]

# ════════════════════════════════════════════════════════════════════
# SECTION MAP — used by financial_chunker.py
# ════════════════════════════════════════════════════════════════════
SECTION_MAP = {
    "Revenue":              REVENUE_KEYWORDS + OTHER_INCOME_KEYWORDS,
    "Cost of Goods Sold":   COGS_KEYWORDS + INVENTORY_CHANGE_KEYWORDS,
    "Gross Profit":         GROSS_PROFIT_KEYWORDS,
    "Employee Expenses":    EMPLOYEE_COST_KEYWORDS,
    "Depreciation":         DEPRECIATION_KEYWORDS,
    "Finance Costs":        FINANCE_COST_KEYWORDS,
    "Marketing":            MARKETING_KEYWORDS,
    "R&D":                  RD_KEYWORDS,
    "SG&A":                 SGA_KEYWORDS,
    "Other Expenses":       OTHER_EXPENSE_KEYWORDS,
    "Operating Expenses":   TOTAL_OPEX_KEYWORDS,
    "Operating Income":     OPERATING_INCOME_KEYWORDS,
    "EBITDA":               EBITDA_KEYWORDS,
    "Profit Before Tax":    PBT_KEYWORDS,
    "Tax":                  TAX_KEYWORDS,
    "Net Income":           NET_INCOME_KEYWORDS,
    "EPS":                  EPS_KEYWORDS,
}

# ════════════════════════════════════════════════════════════════════
# LABEL ALIAS MAP — used by cleaner.py to standardise row labels
# ════════════════════════════════════════════════════════════════════
def _build_alias_map() -> dict[str, str]:
    """Build lowercase_label -> canonical_name alias dict."""
    alias = {}
    mapping = [
        (REVENUE_KEYWORDS,          "Revenue"),
        (OTHER_INCOME_KEYWORDS,     "Other Income"),
        (COGS_KEYWORDS,             "Cost of Goods Sold"),
        (INVENTORY_CHANGE_KEYWORDS, "Inventory Changes"),
        (GROSS_PROFIT_KEYWORDS,     "Gross Profit"),
        (EMPLOYEE_COST_KEYWORDS,    "Employee Expenses"),
        (DEPRECIATION_KEYWORDS,     "Depreciation & Amortization"),
        (FINANCE_COST_KEYWORDS,     "Finance Costs"),
        (SGA_KEYWORDS,              "SG&A"),
        (MARKETING_KEYWORDS,        "Marketing Expenses"),
        (RD_KEYWORDS,               "R&D Expenses"),
        (OTHER_EXPENSE_KEYWORDS,    "Other Expenses"),
        (TOTAL_OPEX_KEYWORDS,       "Total Operating Expenses"),
        (OPERATING_INCOME_KEYWORDS, "Operating Income"),
        (EBITDA_KEYWORDS,           "EBITDA"),
        (PBT_KEYWORDS,              "Profit Before Tax"),
        (TAX_KEYWORDS,              "Tax Expense"),
        (NET_INCOME_KEYWORDS,       "Net Income"),
        (EPS_KEYWORDS,              "EPS"),
        (TOTAL_ASSETS_KEYWORDS,     "Total Assets"),
        (TOTAL_LIABILITIES_KEYWORDS,"Total Liabilities"),
        (EQUITY_KEYWORDS,           "Total Equity"),
        (CASH_KEYWORDS,             "Cash & Equivalents"),
        (DEBT_KEYWORDS,             "Total Debt"),
    ]
    for kw_list, canonical in mapping:
        for kw in kw_list:
            alias[kw.lower()] = canonical
    return alias

LABEL_ALIAS_MAP = _build_alias_map()