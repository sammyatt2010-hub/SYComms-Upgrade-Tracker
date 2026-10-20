import calendar
import hmac
import html as html_lib
import inspect
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="SYComms Renewals & Sales Command Center", page_icon="📅", layout="wide"
)

UK_TZ = ZoneInfo("Europe/London")


# --- Prospect Engine styling (design system shared across Sam's apps) ---
# Presentation only — no business logic. The dataframe grid's own colours
# can't be reached by CSS, which is why the matching dark theme also lives in
# .streamlit/config.toml alongside this file.
_PE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{--bg:#0A0E1A;--surface:#111827;--surface-2:#161F33;--surface-3:#1C2740;--border:rgba(148,163,184,.14);--border-strong:rgba(148,163,184,.26);--text:#E7EAF3;--muted:#8C98B0;--faint:#5E6A82;--accent:#7C83FF;--accent-2:#38D6F5;--accent-soft:rgba(124,131,255,.14);--good:#34D399;--warn:#FBBF24;--risk:#FB923C;--bad:#F87171;--radius:14px;--grad:linear-gradient(135deg,#7C83FF 0%,#38D6F5 100%);}
html,body,[class*="css"],.stApp,button,input,textarea,select{font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif!important}
.stApp{background:radial-gradient(1200px 500px at 85% -10%,rgba(56,214,245,.07),transparent 60%),radial-gradient(900px 500px at 10% -20%,rgba(124,131,255,.10),transparent 60%),var(--bg)}
[data-testid="stHeader"]{background:transparent}[data-testid="stDecoration"]{display:none}footer{visibility:hidden}
.block-container{padding-top:1.6rem!important;padding-bottom:3rem!important;max-width:1500px}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0D1322 0%,#0A0E1A 100%);border-right:1px solid var(--border)}
[data-testid="stWidgetLabel"] p{font-size:.76rem!important;font-weight:600!important;color:var(--muted)!important;text-transform:uppercase;letter-spacing:.06em}
[data-testid="stCaptionContainer"]{color:var(--muted)!important}
[class*="st-key-card-"]{background:linear-gradient(180deg,rgba(22,31,51,.85) 0%,rgba(17,24,39,.85) 100%);border:1px solid var(--border)!important;border-radius:var(--radius);padding:22px 22px 18px;box-shadow:0 1px 0 rgba(255,255,255,.03) inset,0 20px 40px -24px rgba(0,0,0,.6);margin-bottom:18px}
[class*="st-key-appt-"],[class*="st-key-day-"]{background:linear-gradient(180deg,rgba(22,31,51,.7) 0%,rgba(17,24,39,.7) 100%);border:1px solid var(--border)!important;border-radius:12px;padding:14px 16px 10px;box-shadow:0 1px 0 rgba(255,255,255,.03) inset;margin-bottom:10px}
[data-baseweb="input"],[data-baseweb="select"]>div,[data-baseweb="textarea"]{background:var(--surface)!important;border:1px solid var(--border-strong)!important;border-radius:10px!important}
[data-baseweb="input"]:focus-within,[data-baseweb="select"]>div:focus-within,[data-baseweb="textarea"]:focus-within{border-color:var(--accent)!important;box-shadow:0 0 0 3px var(--accent-soft)!important}
[data-baseweb="input"]>div,[data-baseweb="base-input"]{background:transparent!important}
.stButton button,.stDownloadButton button,.stFormSubmitButton button{border-radius:10px!important;font-weight:600!important;border:1px solid var(--border-strong)!important;background:var(--surface-2)!important;color:var(--text)!important;transition:all .15s ease}
.stButton button:hover,.stDownloadButton button:hover{border-color:var(--accent)!important;transform:translateY(-1px)}
.stButton button[kind="primary"],.stDownloadButton button[kind="primary"],.stFormSubmitButton button,[data-testid="stBaseButton-primary"],[data-testid="stBaseLinkButton-primary"]{background:var(--grad)!important;border:none!important;color:#0A0E1A!important;box-shadow:0 8px 24px -10px rgba(124,131,255,.8)}
.stButton button[kind="primary"] p,[data-testid="stBaseButton-primary"] p,.stFormSubmitButton button p,[data-testid="stBaseLinkButton-primary"] p{color:#0A0E1A!important;font-weight:700!important}
[data-testid="stTabs"] [role="tablist"],[data-baseweb="tab-list"]{gap:4px;background:var(--surface);padding:4px;border-radius:12px;border:1px solid var(--border);width:fit-content}
[data-testid="stTabs"] [role="tab"],[data-baseweb="tab"]{border-radius:9px!important;padding:8px 16px!important;color:var(--muted)!important;background:transparent!important}
[data-testid="stTabs"] [role="tab"][aria-selected="true"],[data-baseweb="tab"][aria-selected="true"]{background:var(--surface-3)!important;color:var(--text)!important}
[data-baseweb="tab-highlight"],[data-baseweb="tab-border"],[data-testid="stTabs"] .react-aria-SelectionIndicator{display:none!important}
[data-testid="stDataFrame"]{border:1px solid var(--border);border-radius:12px;overflow:hidden}
[data-testid="stExpander"] details{background:var(--surface);border:1px solid var(--border)!important;border-radius:12px!important}
[data-testid="stAlert"]{border-radius:12px!important}
.pe-hero{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap;padding:6px 2px 22px;margin-bottom:18px;border-bottom:1px solid var(--border)}
.pe-eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--accent-2);margin-bottom:8px}
.pe-eyebrow .dot{width:7px;height:7px;border-radius:50%;background:var(--good);box-shadow:0 0 0 4px rgba(52,211,153,.15)}
.pe-title{font-size:2.05rem;font-weight:800;letter-spacing:-.035em;line-height:1.1;color:var(--text)}
.pe-title span{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.pe-sub{color:var(--muted);font-size:.95rem;margin-top:8px;max-width:620px}
.pe-section{display:flex;align-items:center;gap:12px;margin-bottom:16px;scroll-margin-top:20px}
.pe-section .badge{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;background:var(--accent-soft);color:var(--accent);font-weight:800;font-size:.85rem;border:1px solid rgba(124,131,255,.3)}
.pe-section .t{font-size:1.08rem;font-weight:700;color:var(--text)}.pe-section .s{font-size:.82rem;color:var(--muted);margin-top:2px}
.pe-chip{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;font-size:.76rem;font-weight:600;background:var(--surface-3);color:var(--text);border:1px solid var(--border);white-space:nowrap}
.pe-chip.accent{background:var(--accent-soft);color:#B9BDFF;border-color:rgba(124,131,255,.3)}
.pe-chip.good{background:rgba(52,211,153,.12);color:var(--good);border-color:rgba(52,211,153,.3)}
.pe-chip.warn{background:rgba(251,191,36,.12);color:var(--warn);border-color:rgba(251,191,36,.3)}
.pe-chip.bad{background:rgba(248,113,113,.12);color:var(--bad);border-color:rgba(248,113,113,.3)}
.pe-logo{width:40px;height:40px;border-radius:12px;background:var(--grad);display:grid;place-items:center;color:#0A0E1A;font-weight:800;box-shadow:0 10px 24px -10px rgba(124,131,255,.9)}
.pe-brand{display:flex;align-items:center;gap:12px;margin-bottom:6px}
.pe-brand .name{font-weight:800;color:var(--text);font-size:1rem;letter-spacing:-.02em}
.pe-brand .tag{color:var(--muted);font-size:.76rem}
.pe-status-row{display:flex;align-items:center;gap:8px;font-size:.82rem;color:var(--muted);margin:14px 0 18px}
.pe-status-row .dot{width:7px;height:7px;border-radius:50%;background:var(--good);box-shadow:0 0 0 3px rgba(52,211,153,.15)}
.pe-mini-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:18px}
.pe-mini{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:10px 12px}
.pe-mini .l{font-size:.66rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--faint)}
.pe-mini .v{font-size:1.25rem;font-weight:800;color:var(--text);margin-top:2px}
.pe-login-head{text-align:center;margin:6vh 0 22px}.pe-login-head .pe-logo{width:54px;height:54px;margin:0 auto 16px;border-radius:16px;font-size:1.1rem}
.pe-login-head .t{font-size:1.6rem;font-weight:800;letter-spacing:-.03em;color:var(--text)}.pe-login-head .s{color:var(--muted);font-size:.92rem;margin-top:6px}
.pe-kpi{background:var(--surface);border:1px solid var(--border);border-top:2px solid var(--accent);border-radius:14px;padding:16px 18px;height:100%}
.pe-kpi .l{font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.pe-kpi .v{font-size:1.8rem;font-weight:800;letter-spacing:-.03em;color:var(--text);margin-top:6px}
.pe-subhead{display:flex;align-items:center;gap:10px;margin:18px 0 8px;scroll-margin-top:20px}.pe-subhead .n{font-weight:600;color:var(--text)}.pe-kpi-link{display:block;text-decoration:none!important;cursor:pointer;transition:all .15s ease}
.pe-kpi-link:hover{border-color:var(--accent);transform:translateY(-2px);box-shadow:0 10px 24px -12px rgba(124,131,255,.6)}
.pe-kpi-link .l,.pe-kpi-link .v{display:block}.pe-kpi-link{min-height:112px;box-sizing:border-box;padding:16px 12px 16px 14px}.pe-kpi-link .l{font-size:.63rem;letter-spacing:.03em;overflow-wrap:normal;word-break:normal;hyphens:none;min-height:3.9em}
.pe-kpi-link .v{color:var(--accent-2)!important}
.pe-kpi{min-height:112px;box-sizing:border-box}
.pe-kpi.bad{border-top-color:var(--bad)}.pe-kpi.warn{border-top-color:var(--warn)}.pe-kpi.good{border-top-color:var(--good)}.pe-kpi.muted{border-top-color:var(--faint)}.pe-kpi.cyan{border-top-color:var(--accent-2)}
.pe-kpi-sub{font-size:.74rem;color:var(--muted);margin-top:2px}
.pe-anchor{scroll-margin-top:20px;height:0}
[data-testid="stMetric"]{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:14px 18px}
</style>
"""
st.markdown(_PE_CSS, unsafe_allow_html=True)


def esc(v):
    """Escapes any scraped or user-typed text before it goes into HTML —
    skipping this is how an account called 'Smith & Co' breaks the page."""
    return html_lib.escape(str(v if v is not None else ""), quote=True)


def render_html(markup, target=None):
    # Flatten lines: indented HTML inside st.markdown would otherwise render
    # as a code block rather than as HTML.
    (target or st).markdown("".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def chip(text, tone=""):
    return f'<span class="pe-chip {tone}">{esc(text)}</span>'


def section_header(num, title, subtitle="", anchor_id=None):
    id_attr = f' id="{esc(anchor_id)}"' if anchor_id else ""
    render_html(
        f'<div class="pe-section"{id_attr}><div class="badge">{num}</div><div><div class="t">{esc(title)}</div>'
        + (f'<div class="s">{esc(subtitle)}</div>' if subtitle else "")
        + "</div></div>"
    )


def kpi_tile(label, value, href=None, tone=""):
    """One KPI tile. With href it becomes a clickable link that jumps to that
    section of the page (inline <span>s rather than <div>s inside the <a>, as
    block elements inside a link get split into separate links by the
    markdown renderer)."""
    if href:
        return (
            f'<a href="#{esc(href)}" class="pe-kpi pe-kpi-link {tone}">'
            f'<span class="l">{esc(label)} ↓</span><span class="v">{esc(value)}</span></a>'
        )
    return f'<div class="pe-kpi {tone}"><div class="l">{esc(label)}</div><div class="v">{esc(value)}</div></div>'


def _full_width():
    try:
        if "width" in inspect.signature(st.button).parameters:
            return {"width": "stretch"}
    except (TypeError, ValueError):
        pass
    return {"use_container_width": True}


FULL_WIDTH = _full_width()
try:
    DF_WIDTH = {"width": "stretch"} if "width" in inspect.signature(st.dataframe).parameters else {"use_container_width": True}
except (TypeError, ValueError):
    DF_WIDTH = {"use_container_width": True}
# --- END styling helpers ---


# --- Simple password gate ---
def check_password():
    """Ask for a password before showing anything else on the page. The
    correct password lives in Streamlit secrets (app_password) rather than
    in this file. Fails closed if that secret is missing (so a blank
    password never gets anyone in), and compares with hmac.compare_digest
    rather than == so the check can't leak timing information."""

    def password_entered():
        correct_password = st.secrets.get("app_password")
        entered_password = st.session_state.get("password_input", "")
        if correct_password and hmac.compare_digest(entered_password, correct_password):
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct"):
        return True

    render_html(
        '<div class="pe-login-head">'
        '<div class="pe-logo">SC</div>'
        '<div class="t">SYComms Command Center</div>'
        '<div class="s">Sign in to view live renewals &amp; sales pipeline data from Zoho CRM.</div>'
        "</div>"
    )
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        with st.container(key="card-login"):
            st.text_input("Password", type="password", on_change=password_entered, key="password_input")
            if st.session_state.get("password_correct") is False:
                st.error("Incorrect password")
    return False


if not check_password():
    st.stop()

# Reserve the hero banner's slot now; it's filled in at the very end of the
# script once the live counts are known (it still appears at the top).
hero_placeholder = st.empty()


def render_hero(target, customer_count, deal_count):
    render_html(
        '<div class="pe-hero"><div>'
        '<div class="pe-eyebrow"><span class="dot"></span> LIVE · ZOHO CRM</div>'
        '<div class="pe-title">SYComms Renewals &amp; Sales <span>Command Center</span></div>'
        '<div class="pe-sub">Contract renewals, new accounts and the live sales pipeline, '
        "straight from Zoho CRM.</div></div>"
        '<div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;">'
        + chip(f"{customer_count} customers tracked", "accent")
        + chip(f"{deal_count} deals in pipeline", "accent")
        + chip(f"Last refreshed {datetime.now(UK_TZ).strftime('%H:%M:%S')}")
        + "</div></div>",
        target=target,
    )


# --- Zoho CRM Connection & Loading ---
ZOHO_ACCOUNTS_URL = "https://accounts.zoho.eu/oauth/v2/token"
ZOHO_API_DOMAIN = "https://www.zohoapis.eu"
ACCOUNT_FIELDS = (
    "Account_Name,Account_Type,Tag,Phone,Post_Code,Owner,"
    "Primary_Contact_Name,Primary_Contact_Number,"
    "Contract_Date_End,Contact_Term,Network_Signed,No_of_Handsets"
)

# Accounts are identified primarily by the "Account Type" picklist, but a
# couple of tags need checking too — see the exclusion rules in load_accounts().
ACCOUNT_TYPE = "SYC Customer"

# A "MY PA" tag alone means this isn't a real SYComms customer — but some
# genuine customers carry MY PA *and* SYC together, so only exclude when
# MY PA shows up on its own, without the SYC tag alongside it.
EXCLUDE_UNLESS_ALSO_TAGGED = ("MY PA", "SYC")

# Accounts tagged DEAD ACCOUNT are closed and should never appear here.
DEAD_ACCOUNT_TAG = "DEAD ACCOUNT"

URGENCY_ORDER = ["Red", "Amber", "OK", "Unknown"]
URGENCY_LABEL = {
    "Red": "🔴 Red — under 12 months",
    "Amber": "🟠 Amber — 12–24 months",
    "OK": "🟢 OK — 24+ months",
    "Unknown": "⚪ No end date on file",
}

# Org ID for building direct "open this record in Zoho" links in the tables
# below. Zoho's own record URLs follow this pattern.
ZOHO_ORG_ID = "20098805637"


def zoho_account_url(account_id):
    return f"https://crm.zoho.eu/crm/org{ZOHO_ORG_ID}/tab/Accounts/{account_id}"


def zoho_deal_url(deal_id):
    # Zoho's deal record URLs still use the module's old internal name.
    return f"https://crm.zoho.eu/crm/org{ZOHO_ORG_ID}/tab/Potentials/{deal_id}"


# Deals fields. Monthly_Lease_Spend / Total_Lease_Value / Monthly_Network_Spend
# are the fields this org actually populates when closing a deal (confirmed
# live against a real closed-won deal); Potential_Value / Services_Value sit
# empty, so they're only used as a fallback.
DEAL_FIELDS = (
    "Deal_Name,Owner,Account_Name,Appt_Date_Time,Potential_Value,Services_Value,"
    "Monthly_Lease_Spend,Total_Lease_Value,Monthly_Network_Spend,Stage,Closing_Date"
)
CLOSED_WON_STAGE = "Closed Won"
SOLD_DEALS_WINDOW_DAYS = 30

# This org's Deals module holds both SYComms and SYPLUS business — the only
# thing separating them on the Deal record itself is who owns it. SYComms
# consultants are on @sycomms.co.uk, SYPLUS's on @syplus.co.uk.
SYCOMMS_EMAIL_DOMAIN = "@sycomms.co.uk"

# Sales pipeline stage groupings (matched case-insensitively).
STAGES_EARLY = ["Meeting Booked", "Booked", "2nd Dem", "Pending"]
STAGES_ACTIVE = ["Create Proposal", "Send for Signature", "Negotiations", "On-Hold"]
STAGES_WON = ["Sold", "Closed Won"]
STAGES_LOST = ["Closed Lost", "Not Sold", "Lost", "Unsuccessful"]
STAGE_DOT_COLORS = {
    "sold": "#34D399", "closed won": "#34D399", "2nd dem": "#38D6F5",
    "meeting booked": "#FBBF24", "booked": "#FBBF24", "pending": "#8C98B0",
    "on-hold": "#FB923C", "create proposal": "#7C83FF", "send for signature": "#7C83FF",
    "negotiations": "#34D399", "closed lost": "#F87171", "not sold": "#F87171",
}

ACCENT = "#7C83FF"


def render_leaderboard(series, category_label, y_label):
    """Renders a single-series leaderboard bar chart, sorted highest first.

    Built by hand with Altair rather than st.bar_chart: Streamlit's built-in
    chart types always call Altair's .interactive() under the hood, which
    binds mouse-wheel scrolling over the chart to zoom — so scrolling the
    page while the cursor happens to be over the chart zooms it instead of
    scrolling. Building the same chart without .interactive() keeps normal
    page scrolling working. Styled to match the dark theme."""
    if series.empty:
        st.info("Nothing to show yet.")
        return
    chart_df = series.rename_axis(category_label).reset_index(name=y_label)
    chart = (
        alt.Chart(chart_df)
        .mark_bar(color=ACCENT, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(f"{category_label}:N", sort="-y", title="", axis=alt.Axis(labelAngle=-25)),
            y=alt.Y(f"{y_label}:Q", title=y_label),
            tooltip=[category_label, y_label],
        )
        .properties(height=260)
        .configure(background="transparent")
        .configure_axis(
            labelColor="#8C98B0", titleColor="#8C98B0", gridColor="#1C2740",
            domainColor="#26324D", tickColor="#26324D",
        )
        .configure_view(strokeOpacity=0)
    )
    try:
        st.altair_chart(chart, width="stretch", theme=None)
    except TypeError:
        st.altair_chart(chart, use_container_width=True, theme=None)


def date_range_presets(reference_date):
    """Returns {button label: (start_date, end_date)} for the quick-pick
    shortcuts shown above each date-range picker, all as plain datetime.date
    objects relative to reference_date (normally 'today')."""
    this_month_start = reference_date.replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    this_year_start = reference_date.replace(month=1, day=1)
    last_year_end = this_year_start - timedelta(days=1)
    last_year_start = last_year_end.replace(month=1, day=1)
    return {
        "This month": (this_month_start, reference_date),
        "Last month": (last_month_start, last_month_end),
        "This year": (this_year_start, reference_date),
        "Last year": (last_year_start, last_year_end),
    }


def render_date_range_picker(label, key, default_window_days, reference_date):
    """Renders the This month / Last month / This year / Last year shortcut
    buttons plus the manual date-range picker underneath, both writing into
    the same widget (via session_state), so either way of picking a period
    lands in the same place. Returns the chosen (start, end) as a pair of
    pandas Timestamps.

    Clicking a shortcut button sets st.session_state[key] *before* the
    st.date_input with that key is created further down in this same run —
    the supported way to have a button drive another widget's value."""
    presets = date_range_presets(reference_date)
    preset_cols = st.columns(len(presets))
    for col, (preset_label, preset_dates) in zip(preset_cols, presets.items()):
        if col.button(preset_label, key=f"{key}_preset_{preset_label}", **FULL_WIDTH):
            st.session_state[key] = preset_dates

    default_start = reference_date - timedelta(days=default_window_days)
    # Only pass `value=` on the widget's very first run. Once it has a value
    # in session_state, passing `value=` alongside it triggers a (harmless
    # but noisy) Streamlit warning about setting a widget two ways at once.
    date_input_kwargs = {"max_value": reference_date, "key": key}
    if key not in st.session_state:
        date_input_kwargs["value"] = (default_start, reference_date)
    selected_range = st.date_input(label, **date_input_kwargs)
    # Streamlit hands back a single date while a user is still picking the
    # second one in the range picker — fall back to the default range then.
    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        range_start, range_end = selected_range
    else:
        range_start, range_end = default_start, reference_date

    return pd.Timestamp(range_start), pd.Timestamp(range_end)


def add_months(d, delta):
    month_index = d.month - 1 + delta
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@st.cache_data(ttl=270)  # Zoho access tokens last 1hr; refresh well before that
def get_access_token():
    try:
        creds = st.secrets["zoho"]
    except Exception as err:
        raise RuntimeError(
            f"Missing Zoho credentials in Streamlit secrets. Details: {err}"
        )

    try:
        resp = requests.post(
            ZOHO_ACCOUNTS_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "refresh_token": creds["refresh_token"],
            },
            timeout=15,
        )
        payload = resp.json()
    except Exception as err:
        raise RuntimeError(f"Could not reach Zoho accounts server. Details: {err}")

    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"Zoho authentication failed: {payload}")
    return token


def _paged_get(path, params, what, quiet=False):
    """Fetches every page of a Zoho module list. Raises a readable error on
    failure unless quiet=True (used for nice-to-have lookups), in which case
    it returns whatever it managed to get."""
    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    records = []
    page = 1
    while True:
        try:
            resp = requests.get(
                f"{ZOHO_API_DOMAIN}/crm/v2/{path}",
                headers=headers,
                params={**params, "per_page": 200, "page": page},
                timeout=20,
            )
        except Exception as err:
            if quiet:
                break
            raise RuntimeError(f"Could not reach Zoho CRM API for {what}. Details: {err}")

        if resp.status_code == 204:
            break  # no data at all
        if resp.status_code != 200:
            if quiet:
                break
            raise RuntimeError(
                f"Zoho CRM API returned an error fetching {what} "
                f"(status {resp.status_code}): {resp.text}"
            )

        payload = resp.json()
        records.extend(payload.get("data", []))
        if not payload.get("info", {}).get("more_records"):
            break
        page += 1
    return records


@st.cache_data(ttl=60)
def load_accounts():
    records = _paged_get(
        "Accounts",
        {"fields": ACCOUNT_FIELDS, "sort_by": "Modified_Time", "sort_order": "desc"},
        "Accounts",
    )

    rows = []
    for r in records:
        if (r.get("Account_Type") or "") != ACCOUNT_TYPE:
            continue

        tag_names = [t.get("name", "") for t in (r.get("Tag") or [])]

        if DEAD_ACCOUNT_TAG in tag_names:
            continue  # closed account — never show it

        exclude_tag, unless_tag = EXCLUDE_UNLESS_ALSO_TAGGED
        if exclude_tag in tag_names and unless_tag not in tag_names:
            continue  # MY PA without SYC alongside it — not a real customer

        rows.append(
            {
                "Account ID": r.get("id"),
                "Account Name": r.get("Account_Name") or "",
                "Account Owner": (r.get("Owner") or {}).get("name") or "",
                "All Tags": ", ".join(sorted(tag_names)),
                "Primary Contact": r.get("Primary_Contact_Name") or "",
                "Primary Contact Number": r.get("Primary_Contact_Number") or "",
                "Phone": r.get("Phone") or "",
                "Postal Code": r.get("Post_Code") or "",
                "Contract Signed": r.get("Network_Signed") or "",
                "Contract Term (months)": r.get("Contact_Term"),
                "Contract End Date": r.get("Contract_Date_End") or "",
                "No. of Handsets": r.get("No_of_Handsets"),
            }
        )

    return pd.DataFrame(rows)


@st.cache_data(ttl=600)  # site contacts change far less often than contract dates
def get_contacts_lookup():
    """Fall back for accounts with no Primary Contact set directly, from their
    linked Contact records. Pulls the whole Contacts module in bulk (a handful
    of paginated requests) rather than one request per account — much faster
    than looking up each account's contacts one at a time. Picks whichever
    linked contact has a mobile or phone number on file (preferring mobile),
    so the number is one someone can actually ring. Contacts are a
    nice-to-have, so any failure here is swallowed rather than sinking the
    whole page."""
    records = _paged_get(
        "Contacts", {"fields": "Account_Name,Full_Name,Phone,Mobile"}, "Contacts", quiet=True
    )

    contacts_by_account_id = {}
    for c in records:
        account = c.get("Account_Name") or {}
        account_id = account.get("id")
        if account_id:
            contacts_by_account_id.setdefault(account_id, []).append(c)

    contacts_by_account = {}
    for account_id, contacts in contacts_by_account_id.items():
        best = next((c for c in contacts if c.get("Mobile")), None)
        if best is None:
            best = next((c for c in contacts if c.get("Phone")), contacts[0])
        contacts_by_account[account_id] = {
            "name": best.get("Full_Name") or "",
            "number": best.get("Mobile") or best.get("Phone") or "",
        }

    return contacts_by_account


# The "Legal Contracts" related list shown on each Account page in Zoho is a
# custom module rather than a plain field, so it needs its own small lookup.
# Its REST API name is "Contracts" — the tab in the CRM's own UI shows it
# internally as "CustomModule4", which is a different, unrelated identifier.
LEGAL_CONTRACTS_MODULE = "Contracts"


@st.cache_data(ttl=3600)  # field structure changes rarely, if ever
def get_amount_field_api_name():
    """Looks up the Amount field's actual Zoho API name by its on-screen
    label, rather than hardcoding it — this org's internal field names don't
    always match what's shown on screen (e.g. 'Contract Signed' is really
    stored as Network_Signed), so this is safer than guessing.

    Returns (api_name_or_None, error_message_or_None) so a permissions
    problem can be shown on the page instead of silently leaving every
    Amount blank."""
    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    try:
        resp = requests.get(
            f"{ZOHO_API_DOMAIN}/crm/v2/settings/fields",
            headers=headers,
            params={"module": LEGAL_CONTRACTS_MODULE},
            timeout=20,
        )
    except Exception as err:
        return None, f"could not reach Zoho ({err})"

    if resp.status_code != 200:
        return None, f"Zoho returned status {resp.status_code}: {resp.text[:200]}"

    for field in resp.json().get("fields", []):
        if (field.get("field_label") or "").strip().lower() == "amount":
            return field.get("api_name"), None
    return None, "no 'Amount' field found on the Legal Contracts module"


@st.cache_data(ttl=300)
def get_legal_contract_amounts(account_ids):
    """Pulls each account's Legal Contracts related list and sums the Amount
    field. Only ever called for the small handful of accounts in the New
    Accounts Added list, so one request per account is fine here — this
    isn't the hundreds-of-accounts case the Contacts lookup had to avoid.
    Cached, so clicking around the page doesn't re-fire these requests.

    Returns (amounts_by_account_id, first_error_or_None)."""
    amount_field, field_error = get_amount_field_api_name()
    if not amount_field:
        return {}, field_error
    if not account_ids:
        return {}, None

    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    amounts = {}
    first_error = None
    for account_id in account_ids:
        try:
            resp = requests.get(
                f"{ZOHO_API_DOMAIN}/crm/v2/Accounts/{account_id}/{LEGAL_CONTRACTS_MODULE}",
                headers=headers,
                params={"fields": amount_field},
                timeout=20,
            )
        except Exception as err:
            first_error = first_error or f"could not reach Zoho ({err})"
            continue

        if resp.status_code == 204:
            continue  # no legal contracts on file for this account
        if resp.status_code != 200:
            first_error = first_error or f"Zoho returned status {resp.status_code}: {resp.text[:200]}"
            continue

        total = 0
        for record in resp.json().get("data", []):
            value = record.get(amount_field)
            if isinstance(value, (int, float)):
                total += value
        amounts[account_id] = total

    return amounts, first_error


def parse_appt(raw):
    """Zoho returns the appointment as ISO 8601 with a timezone offset (e.g.
    2026-09-10T14:00:00+01:00). Converted to UK local time, so a visit shows
    on the right day and hour whatever the server's own clock is set to."""
    if not raw:
        return pd.NaT
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is not None:
            dt = dt.astimezone(UK_TZ).replace(tzinfo=None)
        return pd.Timestamp(dt)
    except ValueError:
        return pd.to_datetime(raw, errors="coerce", dayfirst=True)


@st.cache_data(ttl=60)
def load_deals():
    """Every deal, once, from the Deals module. The Sales Pipeline cards use
    the SYComms-owned slice of it; the Sold Deals card uses the Closed Won
    slice."""
    records = _paged_get(
        "Deals",
        {"fields": DEAL_FIELDS, "sort_by": "Modified_Time", "sort_order": "desc"},
        "Deals",
    )

    rows = []
    for r in records:
        owner = r.get("Owner") or {}
        account = r.get("Account_Name") or {}
        lease_total = float(r.get("Total_Lease_Value") or 0) or float(r.get("Potential_Value") or 0)
        network_monthly = float(r.get("Monthly_Network_Spend") or 0) or float(r.get("Services_Value") or 0)
        rows.append(
            {
                "Deal ID": r.get("id"),
                "Client Name": r.get("Deal_Name") or "",
                "Account Name": account.get("name") or "",
                "Sales Rep": owner.get("name") or "Unassigned",
                "Owner Email": (owner.get("email") or "").lower(),
                "Parsed Date": parse_appt(r.get("Appt_Date_Time")),
                "Status": r.get("Stage") or "",
                "Closing Date": r.get("Closing_Date") or "",
                "Monthly Lease Spend": float(r.get("Monthly_Lease_Spend") or 0),
                "Total Lease Value": lease_total,
                "Monthly Network Spend": network_monthly,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(
            columns=[
                "Deal ID", "Client Name", "Account Name", "Sales Rep", "Owner Email",
                "Parsed Date", "Status", "Closing Date", "Monthly Lease Spend",
                "Total Lease Value", "Monthly Network Spend",
            ]
        )
    df["Parsed Date"] = pd.to_datetime(df["Parsed Date"], errors="coerce")
    return df


# --- Load & Error Handling ---
try:
    df = load_accounts()
except Exception as e:
    st.error(f"🚨 Zoho CRM Connection Error: {e}")
    st.stop()

if df.empty:
    st.warning(
        f"No accounts with Account Type = **{ACCOUNT_TYPE}** were found in Zoho."
    )
    st.stop()

# The deals feed only powers the Sales Pipeline tab, so a problem there
# shouldn't take the Renewals tab down with it — it's reported inside that tab.
try:
    deals_df = load_deals()
    deals_error = None
except Exception as e:
    deals_df = pd.DataFrame()
    deals_error = str(e)

# Fill in a site contact for any account with no Primary Contact set directly
# on the Account record, from that account's linked Contact records.
try:
    contacts_lookup = get_contacts_lookup()
except Exception:
    contacts_lookup = {}

needs_lookup = df["Primary Contact"] == ""
for account_id, contact in contacts_lookup.items():
    mask = needs_lookup & (df["Account ID"] == account_id)
    df.loc[mask, "Primary Contact"] = contact["name"]
    df.loc[mask, "Primary Contact Number"] = contact["number"]

df["Open in Zoho"] = df["Account ID"].apply(zoho_account_url)


# --- Data Prep: contract end date, time remaining, urgency ---
def parse_zoho_date(value):
    """Zoho returns Contract End Date as a formula-driven string, and the
    signed date as a plain date string. Both use ISO-style yyyy-MM-dd."""
    if not value:
        return pd.NaT
    try:
        return pd.to_datetime(value, errors="coerce")
    except Exception:
        return pd.NaT


df["Contract End Date"] = df["Contract End Date"].apply(parse_zoho_date)
now_uk = datetime.now(UK_TZ).replace(tzinfo=None)
today = pd.Timestamp(now_uk.date())
df["Days Remaining"] = (df["Contract End Date"] - today).dt.days


def urgency_tier(days):
    if pd.isna(days):
        return "Unknown"
    if days <= 365:  # includes contracts already ended
        return "Red"
    if days <= 730:
        return "Amber"
    return "OK"


def time_remaining_label(days):
    if pd.isna(days):
        return "No end date on file"
    days = int(days)
    if days < 0:
        return f"Overdue by {abs(days) // 30} mo" if abs(days) >= 30 else f"Overdue by {abs(days)}d"
    years, rem_days = divmod(days, 365)
    months = rem_days // 30
    if years == 0 and months == 0:
        return f"{days}d left"
    parts = []
    if years:
        parts.append(f"{years}y")
    if months:
        parts.append(f"{months}m")
    return " ".join(parts) + " left"


df["Urgency"] = df["Days Remaining"].apply(urgency_tier)
df["Time Remaining"] = df["Days Remaining"].apply(time_remaining_label)


def is_rolling_contract(term):
    """Rolling contracts are marked with a contract term of exactly 12
    months — a fixed reference value, not a genuine 'expiring soon' date."""
    try:
        return int(term) == 12
    except (TypeError, ValueError):
        return False


df["Rolling Contract"] = df["Contract Term (months)"].apply(is_rolling_contract)


def format_handsets(value):
    if pd.isna(value):
        return "None"
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "None"


# New deals — contract signed within the last 30 days — flagged up front so
# they can be handed to billing for onboarding without digging for them.
NEW_DEAL_WINDOW_DAYS = 30
df["Contract Signed Date"] = df["Contract Signed"].apply(parse_zoho_date)
df["Days Since Signed"] = (today - df["Contract Signed Date"]).dt.days
df["New Deal"] = df["Days Since Signed"].apply(
    lambda d: pd.notna(d) and 0 <= d <= NEW_DEAL_WINDOW_DAYS
)


def days_since_label(days):
    if pd.isna(days):
        return "Unknown"
    days = int(days)
    if days == 0:
        return "Signed today"
    if days == 1:
        return "Signed yesterday"
    return f"Signed {days} days ago"


# --- Sidebar: brand, live snapshot, refresh, log out ---
render_html(
    '<div class="pe-brand"><div class="pe-logo">SC</div><div>'
    '<div class="name">SYComms</div><div class="tag">Renewals &amp; Sales Command Center</div>'
    "</div></div>",
    target=st.sidebar,
)
render_html(
    '<div class="pe-status-row"><span class="dot"></span> Connected to Zoho CRM</div>',
    target=st.sidebar,
)
render_html(
    '<div class="pe-mini-grid">'
    f'<div class="pe-mini"><div class="l">Customers</div><div class="v">{len(df)}</div></div>'
    f'<div class="pe-mini"><div class="l">Red</div><div class="v">{int(((df["Urgency"] == "Red") & (~df["Rolling Contract"])).sum())}</div></div>'
    f'<div class="pe-mini"><div class="l">Amber</div><div class="v">{int((df["Urgency"] == "Amber").sum())}</div></div>'
    f'<div class="pe-mini"><div class="l">New (30d)</div><div class="v">{int(df["New Deal"].sum())}</div></div>'
    "</div>",
    target=st.sidebar,
)

if st.sidebar.button("Refresh data now", type="primary", **FULL_WIDTH):
    # Pull fresh data within this same session — a browser refresh (F5) would
    # start a brand-new session and force the password to be re-entered, so
    # this button re-runs the app in place instead, staying logged in.
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption(f"Last refreshed: {datetime.now(UK_TZ).strftime('%d/%m/%Y %H:%M:%S')}")
st.sidebar.caption(
    "Data refreshes from Zoho CRM automatically every 60 seconds, or instantly "
    "with the button above."
)
st.sidebar.divider()
if st.sidebar.button("Log out", **FULL_WIDTH):
    st.session_state["password_correct"] = False
    st.rerun()

tab_renewals, tab_sales = st.tabs(["Renewals", "Sales Pipeline"])


# =====================================================================
# TAB 1 — RENEWALS
# =====================================================================
with tab_renewals:

    # --- 1. Overview: filters + top-line KPIs ---
    with st.container(key="card-ren-overview"):
        section_header(1, "Renewals Overview", "Live counts across your SYC Customer accounts")

        filter_cols = st.columns([2, 1])
        selected_urgency = filter_cols[0].multiselect(
            "Urgency",
            options=URGENCY_ORDER,
            default=["Red", "Amber", "Unknown"],
            format_func=lambda u: URGENCY_LABEL[u],
            key="ren_urgency",
            help="Accounts with 24+ months left are hidden by default — add OK to bring them back into view.",
        )
        name_search = filter_cols[1].text_input("Search account name", key="ren_search", placeholder="Type part of a name…")

        filtered_df = df[df["Urgency"].isin(selected_urgency)]
        if name_search:
            filtered_df = filtered_df[
                filtered_df["Account Name"].str.contains(name_search, case=False, na=False)
            ]

        # Rolling contract customers get their own list further down, regardless
        # of the Urgency filter — their contract term is a rolling 12-month
        # marker rather than a genuine countdown, so being caught by the Red
        # filter (or hidden by unticking it) isn't meaningful the way it is for
        # everyone else.
        name_filtered_df = df
        if name_search:
            name_filtered_df = name_filtered_df[
                name_filtered_df["Account Name"].str.contains(name_search, case=False, na=False)
            ]
        rolling_df = name_filtered_df[name_filtered_df["Rolling Contract"]].sort_values("Days Remaining")

        kpi_cols = st.columns(6)
        tiles = [
            ("Customers Tracked", len(df), "renewal-watchlist", ""),
            ("Red (< 12 months)", len(df[(df["Urgency"] == "Red") & (~df["Rolling Contract"])]), "renewal-watchlist", "bad"),
            ("Amber (12–24 months)", len(df[df["Urgency"] == "Amber"]), "renewal-watchlist", "warn"),
            ("No End Date", len(df[df["Urgency"] == "Unknown"]), "no-end-date-list", "muted"),
            ("Rolling Contracts", len(df[df["Rolling Contract"]]), "rolling-section", "cyan"),
            ("New Accounts (30d)", len(df[df["New Deal"]]), "new-accounts-section", "good"),
        ]
        for col, (label, value, anchor, tone) in zip(kpi_cols, tiles):
            with col:
                render_html(kpi_tile(label, value, href=anchor, tone=tone))

    # --- 2. New Accounts Added ---
    with st.container(key="card-ren-new"):
        section_header(
            2, "New Accounts Added",
            "Contracts signed in the chosen period — flag these to billing for onboarding.",
            anchor_id="new-accounts-section",
        )

        range_start_ts, range_end_ts = render_date_range_picker(
            "Show accounts signed between",
            key="new_deals_date_range",
            default_window_days=NEW_DEAL_WINDOW_DAYS,
            reference_date=today.date(),
        )

        st.caption(
            f"Contracts signed from {range_start_ts.strftime('%d/%m/%Y')} to "
            f"{range_end_ts.strftime('%d/%m/%Y')}."
        )

        # New deals also sit outside the Urgency filter — a freshly signed
        # contract is worth surfacing regardless of how far off its renewal is.
        new_deals_df = name_filtered_df[
            name_filtered_df["Contract Signed Date"].between(range_start_ts, range_end_ts)
        ].sort_values("Contract Signed Date", ascending=False)

        if new_deals_df.empty:
            st.info("No contracts signed in the selected date range.")
        else:
            try:
                legal_contract_amounts, amounts_error = get_legal_contract_amounts(
                    tuple(new_deals_df["Account ID"])
                )
            except Exception as err:
                legal_contract_amounts, amounts_error = {}, str(err)

            if amounts_error:
                st.warning(
                    "⚠️ Couldn't read the Legal Contracts amounts from Zoho, so the Amount "
                    f"column shows “—” for now. Details: {amounts_error}"
                )

            new_deals_display_df = new_deals_df[
                ["Account Name", "Account Owner", "Contract Signed Date", "All Tags", "Open in Zoho"]
            ].copy()
            new_deals_display_df["Contract Signed Date"] = new_deals_df["Days Since Signed"].apply(
                days_since_label
            )
            new_deals_display_df["Amount"] = new_deals_df["Account ID"].apply(
                lambda acc_id: legal_contract_amounts.get(acc_id)
            )
            new_deals_display_df = new_deals_display_df[
                ["Account Name", "Account Owner", "Contract Signed Date", "Amount", "All Tags", "Open in Zoho"]
            ]

            total_amount = sum(v for v in new_deals_display_df["Amount"] if pd.notna(v))
            new_deals_display_df["Amount"] = new_deals_display_df["Amount"].apply(
                lambda v: f"£{v:,.2f}" if pd.notna(v) else "—"
            )

            st.dataframe(
                new_deals_display_df,
                hide_index=True,
                **DF_WIDTH,
                column_config={"Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗")},
            )
            # Show the selected period as a proper month name when it lines up
            # with one calendar month (the common case), otherwise fall back to
            # showing the actual date range picked above.
            if (
                range_start_ts.year == range_end_ts.year
                and range_start_ts.month == range_end_ts.month
            ):
                period_label = range_start_ts.strftime("%B %Y")
            else:
                period_label = (
                    f"{range_start_ts.strftime('%d %b %Y')} – {range_end_ts.strftime('%d %b %Y')}"
                )
            st.metric(f"Total service value ({period_label})", f"£{total_amount:,.2f}")

            st.caption("Leaderboard — accounts added per consultant")
            owner_counts = (
                new_deals_df["Account Owner"]
                .replace("", "Unassigned")
                .value_counts()
                .sort_values(ascending=False)
            )
            render_leaderboard(owner_counts, "Consultant", "Accounts added")

    # --- 3. Renewal Watchlist ---
    with st.container(key="card-ren-list"):
        section_header(
            3, "Renewal Watchlist",
            "Accounts ranked by how soon their contract runs out, soonest first.",
            anchor_id="renewal-watchlist",
        )

        visible_df = filtered_df[
            (filtered_df["Urgency"] != "Unknown") & (~filtered_df["Rolling Contract"])
        ].sort_values("Days Remaining")

        table_cols = [
            "Account Name",
            "Urgency",
            "Time Remaining",
            "Contract End Date",
            "Postal Code",
            "Primary Contact",
            "Primary Contact Number",
            "No. of Handsets",
            "All Tags",
            "Open in Zoho",
        ]

        if visible_df.empty:
            st.info("No accounts match the current filters.")
        else:
            display_df = visible_df[table_cols].copy()
            display_df["Contract End Date"] = display_df["Contract End Date"].dt.strftime("%d/%m/%Y")
            display_df["Urgency"] = display_df["Urgency"].map(URGENCY_LABEL)
            display_df["No. of Handsets"] = display_df["No. of Handsets"].apply(format_handsets)

            def highlight_urgency(row):
                color = {
                    "Red": "background-color: rgba(248, 113, 113, 0.18)",
                    "Amber": "background-color: rgba(251, 191, 36, 0.14)",
                }.get(visible_df.loc[row.name, "Urgency"], "")
                return [color] * len(row)

            st.dataframe(
                display_df.style.apply(highlight_urgency, axis=1),
                hide_index=True,
                **DF_WIDTH,
                column_config={"Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗")},
            )

        # Accounts with no contract end date on file — listed separately rather
        # than mixed in (or silently dropped from) the coloured watchlist above.
        # Rolling contract accounts are excluded here too since they get their
        # own section below instead.
        render_html('<div id="no-end-date-list" class="pe-anchor"></div>')
        unknown_df = filtered_df[
            (filtered_df["Urgency"] == "Unknown") & (~filtered_df["Rolling Contract"])
        ]
        if not unknown_df.empty:
            with st.expander(f"{len(unknown_df)} account(s) with no contract end date on file"):
                st.dataframe(
                    unknown_df[
                        [
                            "Account Name",
                            "Primary Contact",
                            "Primary Contact Number",
                            "Contract Term (months)",
                            "All Tags",
                            "Open in Zoho",
                        ]
                    ],
                    hide_index=True,
                    **DF_WIDTH,
                    column_config={"Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗")},
                )

    # --- 4. Rolling Contract Customers ---
    # Rolling contract customers ("Contract Term (months)" == exactly 12) aren't
    # on a genuine fixed end date, so being flagged Red in the main list above
    # would be misleading — they get their own list here instead, still visible,
    # just kept separate from the "actually expiring soon" watchlist.
    with st.container(key="card-ren-rolling"):
        section_header(
            4, "Rolling Contract Customers",
            "Accounts on a rolling 12-month term. Shown here rather than flagged Red above, "
            "since their renewal date isn't a genuine deadline.",
            anchor_id="rolling-section",
        )

        rolling_table_cols = [
            "Account Name",
            "Time Remaining",
            "Contract End Date",
            "Postal Code",
            "Primary Contact",
            "Primary Contact Number",
            "No. of Handsets",
            "All Tags",
            "Open in Zoho",
        ]

        if rolling_df.empty:
            st.info("No rolling contract accounts match the current filters.")
        else:
            rolling_display_df = rolling_df[rolling_table_cols].copy()
            rolling_display_df["Contract End Date"] = rolling_display_df["Contract End Date"].apply(
                lambda d: d.strftime("%d/%m/%Y") if pd.notna(d) else "No end date on file"
            )
            rolling_display_df["No. of Handsets"] = rolling_display_df["No. of Handsets"].apply(format_handsets)

            st.dataframe(
                rolling_display_df,
                hide_index=True,
                **DF_WIDTH,
                column_config={"Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗")},
            )


# =====================================================================
# TAB 2 — SALES PIPELINE
# =====================================================================
def stage_in(series, names):
    return series.astype(str).str.lower().isin([n.lower() for n in names])


def money(v):
    return f"£{v:,.2f}"


with tab_sales:
    if deals_error:
        st.error(f"🚨 Could not load deals from Zoho: {deals_error}")
        pipeline_df = pd.DataFrame(
            {
                "Deal ID": pd.Series(dtype=str), "Client Name": pd.Series(dtype=str),
                "Sales Rep": pd.Series(dtype=str), "Status": pd.Series(dtype=str),
                "Parsed Date": pd.to_datetime(pd.Series([], dtype="object")),
                "Total Lease Value": pd.Series(dtype=float), "Monthly Network Spend": pd.Series(dtype=float),
            }
        )
        sold_source_df = pd.DataFrame()
        pipeline_filtered_df = pipeline_df
    else:
        # SYComms only — a deal with no owner, or an owner outside
        # sycomms.co.uk (SYPLUS, or an unrelated partner email), doesn't belong
        # on the SYComms pipeline.
        pipeline_df = deals_df[deals_df["Owner Email"].str.endswith(SYCOMMS_EMAIL_DOMAIN.lower())].copy()
        sold_source_df = deals_df

    current_date = now_uk

    # --- 1. Pipeline Overview: timeframe + filters + KPIs ---
    with st.container(key="card-sp-overview"):
        section_header(
            1, "Pipeline Overview",
            "SYComms deals by appointment date — choose a timeframe, then narrow by consultant or stage.",
        )

        timeframe_options = ["Specific Month", "Month-to-Date (MTD)", "Quarterly", "Yearly", "All Time"]
        tf_cols = st.columns([1.2, 1, 1, 1.1])  # timeframe, then its month/quarter/year picker(s)
        timeframe_option = tf_cols[0].selectbox(
            "Timeframe view", timeframe_options, index=0, key="sp_timeframe"
        )

        time_filtered_df = pipeline_df.copy()
        year_options = [current_date.year, current_date.year - 1, current_date.year - 2]

        if timeframe_option == "Month-to-Date (MTD)":
            time_filtered_df = time_filtered_df[
                (time_filtered_df["Parsed Date"].dt.year == current_date.year)
                & (time_filtered_df["Parsed Date"].dt.month == current_date.month)
                & (time_filtered_df["Parsed Date"] <= pd.Timestamp(current_date))
            ]
        elif timeframe_option == "Specific Month":
            valid_dates = pipeline_df["Parsed Date"].dropna()
            if not valid_dates.empty:
                available_months = (
                    valid_dates.dt.to_period("M").drop_duplicates().sort_values(ascending=False)
                )
                month_str_options = [m.to_timestamp().strftime("%B %Y") for m in available_months]
            else:
                month_str_options = [current_date.strftime("%B %Y")]
            current_month_str = current_date.strftime("%B %Y")
            default_index = (
                month_str_options.index(current_month_str)
                if current_month_str in month_str_options
                else 0
            )
            selected_month_str = tf_cols[1].selectbox(
                "Month", month_str_options, index=default_index, key="sp_month"
            )
            chosen_period = pd.to_datetime(selected_month_str, format="%B %Y")
            time_filtered_df = time_filtered_df[
                (time_filtered_df["Parsed Date"].dt.year == chosen_period.year)
                & (time_filtered_df["Parsed Date"].dt.month == chosen_period.month)
            ]
        elif timeframe_option == "Quarterly":
            current_quarter = (current_date.month - 1) // 3 + 1
            selected_q = tf_cols[1].selectbox("Quarter", [1, 2, 3, 4], index=current_quarter - 1, key="sp_quarter")
            selected_year = tf_cols[2].selectbox("Year", year_options, key="sp_q_year")
            time_filtered_df = time_filtered_df[
                (time_filtered_df["Parsed Date"].dt.year == selected_year)
                & (time_filtered_df["Parsed Date"].dt.quarter == selected_q)
            ]
        elif timeframe_option == "Yearly":
            selected_year = tf_cols[1].selectbox("Year", year_options, key="sp_year")
            time_filtered_df = time_filtered_df[time_filtered_df["Parsed Date"].dt.year == selected_year]

        # Consultant & stage filters (options come from what's in the chosen timeframe)
        rep_options = ["All"] + sorted(time_filtered_df["Sales Rep"].unique()) if not time_filtered_df.empty else ["All"]
        status_options = ["All"] + sorted(s for s in time_filtered_df["Status"].unique() if s) if not time_filtered_df.empty else ["All"]
        filter_row = st.columns([1.2, 1, 1, 1.1])
        selected_rep = filter_row[0].selectbox("Consultant", rep_options, key="sp_rep")
        selected_status = filter_row[1].selectbox("Stage", status_options, key="sp_status")
        show_financials = filter_row[2].toggle("Show financials", value=False, key="sp_financials")

        pipeline_filtered_df = time_filtered_df.copy()
        if selected_rep != "All":
            pipeline_filtered_df = pipeline_filtered_df[pipeline_filtered_df["Sales Rep"] == selected_rep]
        if selected_status != "All":
            pipeline_filtered_df = pipeline_filtered_df[pipeline_filtered_df["Status"] == selected_status]

        def count_stages(frame, stages):
            return 0 if frame.empty else int(stage_in(frame["Status"], stages).sum())

        total_deals_count = len(pipeline_filtered_df)
        early_count = count_stages(pipeline_filtered_df, STAGES_EARLY)
        active_count = count_stages(pipeline_filtered_df, STAGES_ACTIVE)
        won_count = count_stages(pipeline_filtered_df, STAGES_WON)
        lost_count = count_stages(pipeline_filtered_df, STAGES_LOST)

        pk = st.columns(4)
        with pk[0]:
            render_html(kpi_tile("Deals in view", total_deals_count))
        with pk[1]:
            render_html(kpi_tile("New / booked appointments", early_count, tone="warn"))
        with pk[2]:
            render_html(kpi_tile("In progress / closing", active_count, tone="cyan"))
        with pk[3]:
            render_html(kpi_tile("Won / closed", f"{won_count} won · {lost_count} lost", tone="good"))

        if show_financials:
            st.caption(
                "Financials use each deal's Total Lease Value and Monthly Network Spend "
                "(the fields filled in when a deal is closed)."
            )
            won_mask = stage_in(pipeline_filtered_df["Status"], STAGES_WON) if not pipeline_filtered_df.empty else pd.Series(dtype=bool)
            fk = st.columns(3)
            with fk[0]:
                render_html(kpi_tile("Pipeline lease value", money(pipeline_filtered_df["Total Lease Value"].sum())))
            with fk[1]:
                render_html(kpi_tile("Won lease value", money(pipeline_filtered_df.loc[won_mask, "Total Lease Value"].sum()), tone="good"))
            with fk[2]:
                render_html(kpi_tile("Won monthly network spend", money(pipeline_filtered_df.loc[won_mask, "Monthly Network Spend"].sum()), tone="good"))

    # --- 2. Pipeline Schedule ---
    with st.container(key="card-sp-schedule"):
        section_header(
            2, "Pipeline Schedule",
            f"Deals and their stage, soonest appointment first ({timeframe_option}).",
        )
        if pipeline_filtered_df.empty:
            st.info("No records found matching your selected timeframe and filters.")
        else:
            sched = pipeline_filtered_df.sort_values("Parsed Date", ascending=True).copy()
            sched["Appointment"] = sched["Parsed Date"].apply(
                lambda d: d.strftime("%d/%m/%Y %H:%M") if pd.notna(d) else "No appointment date"
            )
            sched["Open in Zoho"] = sched["Deal ID"].apply(zoho_deal_url)
            sched_cols = ["Appointment", "Client Name", "Sales Rep", "Status"]
            if show_financials:
                sched["Total Lease Value"] = sched["Total Lease Value"].apply(money)
                sched["Monthly Network Spend"] = sched["Monthly Network Spend"].apply(money)
                sched_cols += ["Total Lease Value", "Monthly Network Spend"]
            sched_cols.append("Open in Zoho")
            st.dataframe(
                sched[sched_cols],
                **DF_WIDTH,
                hide_index=True,
                column_config={"Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗")},
            )

    # --- 3. Diary ---
    with st.container(key="card-sp-diary"):
        section_header(
            3, "Diary — Booked Appointments",
            "Every deal with an appointment date on file. Follows the consultant and stage filters "
            "above, but not the timeframe — so you can page back and forward freely.",
            anchor_id="sp-diary-section",
        )

        diary_source = pipeline_df
        if selected_rep != "All":
            diary_source = diary_source[diary_source["Sales Rep"] == selected_rep]
        if selected_status != "All":
            diary_source = diary_source[diary_source["Status"] == selected_status]

        appointments = []
        for _, row in diary_source.iterrows():
            if pd.notna(row["Parsed Date"]):
                appointments.append(
                    {
                        "deal_id": row.get("Deal ID"),
                        "client_name": row["Client Name"],
                        "consultant": row["Sales Rep"],
                        "status": row["Status"] or "Unknown",
                        "date": row["Parsed Date"].date().isoformat(),
                        "time": row["Parsed Date"].strftime("%H:%M"),
                    }
                )

        appointments_by_date = {}
        for appt in appointments:
            appointments_by_date.setdefault(appt["date"], []).append(appt)
        for day_appts in appointments_by_date.values():
            day_appts.sort(key=lambda a: a["time"])

        def render_diary_appointment(appt):
            """One diary entry: time, client, consultant and stage."""
            with st.container(key=f"appt-{appt['deal_id']}"):
                deal_link = zoho_deal_url(appt["deal_id"]) if appt["deal_id"] else None
                client_label = f"[{appt['client_name']}]({deal_link})" if deal_link else appt["client_name"]
                st.markdown(f"**{appt['time']}** — {client_label}")
                color = STAGE_DOT_COLORS.get(appt["status"].lower(), "#8C98B0")
                st.markdown(
                    f"👤 {esc(appt['consultant'])} &nbsp;·&nbsp; "
                    f"<span style='color:{color}'>●</span> {esc(appt['status'])}",
                    unsafe_allow_html=True,
                )

        if "diary_ref_date" not in st.session_state:
            st.session_state["diary_ref_date"] = date.today()

        diary_view_mode = st.radio("View", options=["Week", "Month"], horizontal=True, key="diary_view_mode")

        nav_cols = st.columns([1, 1, 1, 4])
        if nav_cols[0].button("Previous", key="sp_diary_prev", **FULL_WIDTH):
            if diary_view_mode == "Week":
                st.session_state["diary_ref_date"] -= timedelta(days=7)
            else:
                st.session_state["diary_ref_date"] = add_months(st.session_state["diary_ref_date"], -1)
        if nav_cols[1].button("Today", key="sp_diary_today", **FULL_WIDTH):
            st.session_state["diary_ref_date"] = date.today()
        if nav_cols[2].button("Next", key="sp_diary_next", **FULL_WIDTH):
            if diary_view_mode == "Week":
                st.session_state["diary_ref_date"] += timedelta(days=7)
            else:
                st.session_state["diary_ref_date"] = add_months(st.session_state["diary_ref_date"], 1)

        diary_ref_date = st.session_state["diary_ref_date"]

        if diary_view_mode == "Week":
            week_start = diary_ref_date - timedelta(days=diary_ref_date.weekday())
            week_days = [week_start + timedelta(days=i) for i in range(7)]
            st.caption(f"Week of {week_start.strftime('%d %b %Y')}")

            day_cols = st.columns(7)
            for col, day in zip(day_cols, week_days):
                with col:
                    is_today = day == date.today()
                    st.markdown(f"{'🔵 ' if is_today else ''}**{day.strftime('%a %d %b')}**")
                    day_appts = appointments_by_date.get(day.isoformat(), [])
                    if not day_appts:
                        st.caption("—")
                    else:
                        for appt in day_appts:
                            render_diary_appointment(appt)
        else:
            st.caption(diary_ref_date.strftime("%B %Y"))
            weeks = calendar.monthcalendar(diary_ref_date.year, diary_ref_date.month)

            header_cols = st.columns(7)
            for col, day_name in zip(header_cols, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
                col.markdown(f"**{day_name}**")

            for week_idx, week in enumerate(weeks):
                week_cols = st.columns(7)
                for col_idx, (col, day_num) in enumerate(zip(week_cols, week)):
                    with col:
                        # Keyed per cell position (not day number) — the blank
                        # filler cells all have day_num 0 and would collide.
                        with st.container(key=f"day-{diary_ref_date.year}-{diary_ref_date.month}-{week_idx}-{col_idx}"):
                            if day_num == 0:
                                st.markdown("&nbsp;")
                                continue
                            day_date = date(diary_ref_date.year, diary_ref_date.month, day_num)
                            is_today = day_date == date.today()
                            st.markdown(f"{'🔵 ' if is_today else ''}**{day_num}**")
                            day_appts = appointments_by_date.get(day_date.isoformat(), [])
                            if day_appts:
                                with st.popover(f"{len(day_appts)} 📅", **FULL_WIDTH):
                                    for appt in day_appts:
                                        render_diary_appointment(appt)

    # --- 4. Consultant Performance ---
    with st.container(key="card-sp-perf"):
        section_header(
            4, "Consultant Performance",
            f"Deals by consultant across the whole timeframe ({timeframe_option}), ignoring the consultant and stage filters.",
        )
        if not time_filtered_df.empty:
            rep_summary = (
                time_filtered_df.groupby("Sales Rep")
                .agg(
                    Total_Deals=("Client Name", "count"),
                    Deals_Won=("Status", lambda x: int(stage_in(x, STAGES_WON).sum())),
                    Deals_In_Progress=("Status", lambda x: int(stage_in(x, STAGES_ACTIVE).sum())),
                    Deals_Booked=("Status", lambda x: int(stage_in(x, STAGES_EARLY).sum())),
                    Deals_Lost=("Status", lambda x: int(stage_in(x, STAGES_LOST).sum())),
                )
                .reset_index()
                .sort_values(["Deals_Won", "Total_Deals"], ascending=False)
            )
            rep_summary.columns = ["Sales Rep", "Total Deals", "Won", "In Progress", "Booked", "Lost"]
            st.dataframe(rep_summary, **DF_WIDTH, hide_index=True)

            won_by_rep = rep_summary.set_index("Sales Rep")["Won"]
            won_by_rep = won_by_rep[won_by_rep > 0].sort_values(ascending=False)
            if not won_by_rep.empty:
                st.caption("Leaderboard — deals won per consultant")
                render_leaderboard(won_by_rep, "Consultant", "Deals won")
        else:
            st.info("Insufficient data for consultant metrics in this timeframe.")

    # --- 5. Stage Breakdown ---
    with st.container(key="card-sp-stages"):
        section_header(5, "Stage Breakdown", f"How many deals sit at each stage ({timeframe_option}).")
        if not time_filtered_df.empty:
            tracked_stages = STAGES_EARLY + STAGES_ACTIVE + ["Sold", "Closed Won", "Closed Lost", "Not Sold"]
            lowered = time_filtered_df["Status"].astype(str).str.lower()
            stage_counts = [
                {"Stage / Status": stage, "Total Count": int((lowered == stage.lower()).sum())}
                for stage in tracked_stages
            ]
            # Any stage in the data that isn't one of the standard ones above
            # (e.g. a new stage added in Zoho, or "Lost") would otherwise be
            # silently left out of the breakdown — list them too.
            known = {s.lower() for s in tracked_stages}
            other_stages = sorted({s for s in time_filtered_df["Status"].astype(str) if s and s.lower() not in known})
            for stage in other_stages:
                stage_counts.append(
                    {"Stage / Status": f"{stage} (other)", "Total Count": int((time_filtered_df["Status"] == stage).sum())}
                )
            st.dataframe(pd.DataFrame(stage_counts), **DF_WIDTH, hide_index=True)
        else:
            st.info("No data available for stage breakdown.")

    # --- 6. Sold Deals (Closed Won) ---
    with st.container(key="card-sp-sold"):
        section_header(
            6, "Sold Deals (Closed Won)",
            "Deals closed won in the chosen period, with the lease value sold per consultant.",
        )
        sold_syc_only = st.toggle(
            "SYComms-owned deals only",
            value=False,
            key="sold_syc_only",
            help="Off = every Closed Won deal in Zoho (SYComms and SYPLUS). On = only deals owned by a @sycomms.co.uk consultant.",
        )

        if deals_error:
            st.info("Sold deals are unavailable while the deals feed is down (see the error above).")
        else:
            sold_deals_df = sold_source_df[sold_source_df["Status"] == CLOSED_WON_STAGE].copy()
            if sold_syc_only:
                sold_deals_df = sold_deals_df[sold_deals_df["Owner Email"].str.endswith(SYCOMMS_EMAIL_DOMAIN.lower())]

            if sold_deals_df.empty:
                st.info("No Closed Won deals found.")
            else:
                sold_deals_df["Closing Date"] = sold_deals_df["Closing Date"].apply(parse_zoho_date)

                sold_range_start_ts, sold_range_end_ts = render_date_range_picker(
                    "Show deals closed between",
                    key="sold_deals_date_range",
                    default_window_days=SOLD_DEALS_WINDOW_DAYS,
                    reference_date=today.date(),
                )

                st.caption(
                    f"Closed Won from {sold_range_start_ts.strftime('%d/%m/%Y')} to "
                    f"{sold_range_end_ts.strftime('%d/%m/%Y')}."
                )

                recent_deals_df = sold_deals_df[
                    sold_deals_df["Closing Date"].between(sold_range_start_ts, sold_range_end_ts)
                ].sort_values("Closing Date", ascending=False)

                if recent_deals_df.empty:
                    st.info("No deals closed won in the selected date range.")
                else:
                    deals_display_df = recent_deals_df[
                        [
                            "Client Name", "Account Name", "Sales Rep", "Monthly Lease Spend",
                            "Total Lease Value", "Monthly Network Spend", "Closing Date", "Deal ID",
                        ]
                    ].rename(columns={"Client Name": "Deal Name", "Sales Rep": "Sales Consultant"}).copy()
                    deals_display_df["Closing Date"] = deals_display_df["Closing Date"].dt.strftime("%d/%m/%Y")
                    deals_display_df["Open in Zoho"] = deals_display_df["Deal ID"].apply(zoho_deal_url)
                    deals_display_df = deals_display_df.drop(columns=["Deal ID"])
                    for col in ["Monthly Lease Spend", "Total Lease Value", "Monthly Network Spend"]:
                        deals_display_df[col] = deals_display_df[col].apply(money)

                    st.dataframe(
                        deals_display_df,
                        hide_index=True,
                        **DF_WIDTH,
                        column_config={"Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗")},
                    )
                    st.metric("Total sold this period", money(recent_deals_df["Total Lease Value"].sum()))

                    st.caption("Leaderboard — value sold per consultant")
                    consultant_totals = (
                        recent_deals_df.assign(
                            **{"Sales Rep": recent_deals_df["Sales Rep"].replace("", "Unassigned")}
                        )
                        .groupby("Sales Rep")["Total Lease Value"]
                        .sum()
                        .sort_values(ascending=False)
                    )
                    render_leaderboard(consultant_totals, "Consultant", "Total Lease Value sold (£)")


# Fill in the hero banner reserved at the top of the page now that the
# live counts are known.
render_hero(hero_placeholder, len(df), len(pipeline_df) if not deals_error else 0)
