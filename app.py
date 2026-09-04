from datetime import datetime

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="SYC Customer Renewals Watchlist", page_icon="📅", layout="wide"
)


# --- Simple password gate ---
def check_password():
    """Ask for a password before showing anything else on the page. The
    correct password lives in Streamlit secrets (app_password) rather than
    in this file, so it can be changed later without touching the code."""

    def password_entered():
        if st.session_state.get("password_input") == st.secrets.get("app_password", ""):
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct"):
        return True

    st.text_input(
        "🔒 Password", type="password", on_change=password_entered, key="password_input"
    )
    if st.session_state.get("password_correct") is False:
        st.error("Incorrect password")
    return False


if not check_password():
    st.stop()


st.title("📅 SYC Customer Renewals Watchlist")
st.caption(
    "Live from Zoho CRM — SYC Customer accounts, flagged by how soon their "
    "contract runs out."
)

# --- Zoho CRM Connection & Loading ---
ZOHO_ACCOUNTS_URL = "https://accounts.zoho.eu/oauth/v2/token"
ZOHO_API_DOMAIN = "https://www.zohoapis.eu"
ACCOUNT_FIELDS = (
    "Account_Name,Account_Type,Phone,Post_Code,"
    "Primary_Contact_Name,Primary_Contact_Number,"
    "Contract_Date_End,Contact_Term,Network_Signed,No_of_Handsets"
)

# This side of the business doesn't use tags — accounts are identified purely
# by the "Account Type" picklist on the Account record.
ACCOUNT_TYPE = "SYC Customer"

URGENCY_ORDER = ["Red", "Amber", "OK", "Unknown"]
URGENCY_LABEL = {
    "Red": "🔴 Red — under 12 months",
    "Amber": "🟠 Amber — 12–24 months",
    "OK": "🟢 OK — 24+ months",
    "Unknown": "⚪ No end date on file",
}

# Org ID for building direct "open this account in Zoho" links in the tables
# below. Zoho's own record URLs follow this pattern.
ZOHO_ORG_ID = "20098805637"


def zoho_account_url(account_id):
    return f"https://crm.zoho.eu/crm/org{ZOHO_ORG_ID}/tab/Accounts/{account_id}"


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


@st.cache_data(ttl=60)
def load_accounts():
    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}

    records = []
    page = 1
    while True:
        try:
            resp = requests.get(
                f"{ZOHO_API_DOMAIN}/crm/v2/Accounts",
                headers=headers,
                params={
                    "fields": ACCOUNT_FIELDS,
                    "per_page": 200,
                    "page": page,
                    "sort_by": "Modified_Time",
                    "sort_order": "desc",
                },
                timeout=20,
            )
        except Exception as err:
            raise RuntimeError(f"Could not reach Zoho CRM API. Details: {err}")

        if resp.status_code == 204:
            break  # no data at all
        if resp.status_code != 200:
            raise RuntimeError(
                f"Zoho CRM API returned an error (status {resp.status_code}): {resp.text}"
            )

        payload = resp.json()
        records.extend(payload.get("data", []))
        info = payload.get("info", {})
        if not info.get("more_records"):
            break
        page += 1

    rows = []
    for r in records:
        if (r.get("Account_Type") or "") != ACCOUNT_TYPE:
            continue

        rows.append(
            {
                "Account ID": r.get("id"),
                "Account Name": r.get("Account_Name") or "",
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
    so the number is one someone can actually ring."""
    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}

    contacts_by_account_id = {}
    page = 1
    while True:
        try:
            resp = requests.get(
                f"{ZOHO_API_DOMAIN}/crm/v2/Contacts",
                headers=headers,
                params={
                    "fields": "Account_Name,Full_Name,Phone,Mobile",
                    "per_page": 200,
                    "page": page,
                },
                timeout=20,
            )
        except Exception:
            break  # contacts are a nice-to-have; don't sink the whole page over this

        if resp.status_code != 200:
            break  # 204 = no contacts at all; anything else, stop quietly

        payload = resp.json()
        for c in payload.get("data", []):
            account = c.get("Account_Name") or {}
            account_id = account.get("id")
            if not account_id:
                continue
            contacts_by_account_id.setdefault(account_id, []).append(c)

        if not payload.get("info", {}).get("more_records"):
            break
        page += 1

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
today = pd.Timestamp(datetime.now().date())
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


# --- Sidebar Filters ---
st.sidebar.header("🔍 Filters")
st.sidebar.caption(
    "Accounts with 24+ months left are hidden by default — tick **OK** below "
    "to bring them back into view."
)
selected_urgency = st.sidebar.multiselect(
    "Urgency",
    options=URGENCY_ORDER,
    default=["Red", "Amber", "Unknown"],
    format_func=lambda u: URGENCY_LABEL[u],
)
name_search = st.sidebar.text_input("Search account name")

st.sidebar.divider()
st.sidebar.caption(f"Last refreshed: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
st.sidebar.caption("Data refreshes from Zoho CRM automatically every 60 seconds.")

filtered_df = df[df["Urgency"].isin(selected_urgency)]
if name_search:
    filtered_df = filtered_df[
        filtered_df["Account Name"].str.contains(name_search, case=False, na=False)
    ]

st.divider()

# --- Top-Line KPIs ---
kpi_cols = st.columns(4)
kpi_cols[0].metric("SYC Customers Tracked", f"{len(df)}")
kpi_cols[1].metric("🔴 Red (< 12 months)", f"{len(df[df['Urgency'] == 'Red'])}")
kpi_cols[2].metric("🟠 Amber (12–24 months)", f"{len(df[df['Urgency'] == 'Amber'])}")
kpi_cols[3].metric("⚪ No End Date", f"{len(df[df['Urgency'] == 'Unknown'])}")

st.divider()

# --- Watchlist Table ---
st.subheader("📋 Renewal Watchlist")

visible_df = filtered_df[filtered_df["Urgency"] != "Unknown"].sort_values("Days Remaining")

table_cols = [
    "Account Name",
    "Urgency",
    "Time Remaining",
    "Contract End Date",
    "Postal Code",
    "Primary Contact",
    "Primary Contact Number",
    "No. of Handsets",
    "Open in Zoho",
]


def format_handsets(value):
    if pd.isna(value):
        return "None"
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "None"


if visible_df.empty:
    st.info("No accounts match the current filters.")
else:
    display_df = visible_df[table_cols].copy()
    display_df["Contract End Date"] = display_df["Contract End Date"].dt.strftime("%d/%m/%Y")
    display_df["Urgency"] = display_df["Urgency"].map(URGENCY_LABEL)
    display_df["No. of Handsets"] = display_df["No. of Handsets"].apply(format_handsets)

    def highlight_urgency(row):
        color = {
            "Red": "background-color: rgba(220, 53, 69, 0.25)",
            "Amber": "background-color: rgba(255, 165, 0, 0.22)",
        }.get(visible_df.loc[row.name, "Urgency"], "")
        return [color] * len(row)

    st.dataframe(
        display_df.style.apply(highlight_urgency, axis=1),
        hide_index=True,
        use_container_width=True,
        column_config={"Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗")},
    )

# Accounts with no contract end date on file — listed separately as requested,
# rather than mixed in (or silently dropped from) the coloured watchlist above.
unknown_df = filtered_df[filtered_df["Urgency"] == "Unknown"]
if not unknown_df.empty:
    with st.expander(
        f"⚪ {len(unknown_df)} account(s) with no contract end date on file"
    ):
        st.dataframe(
            unknown_df[
                [
                    "Account Name",
                    "Primary Contact",
                    "Primary Contact Number",
                    "Contract Term (months)",
                    "Open in Zoho",
                ]
            ],
            hide_index=True,
            use_container_width=True,
            column_config={"Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗")},
        )
