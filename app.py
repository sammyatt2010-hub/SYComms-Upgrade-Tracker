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
    "Account_Name,Account_Type,Tag,Phone,Post_Code,"
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


# The "Legal Contracts" related list shown on each Account page in Zoho is a
# custom module (Zoho's auto-generated internal name for it is CustomModule4)
# rather than a plain field, so it needs its own small lookup.
LEGAL_CONTRACTS_MODULE = "CustomModule4"


@st.cache_data(ttl=3600)  # field structure changes rarely, if ever
def get_amount_field_api_name():
    """Looks up the Amount field's actual Zoho API name by its on-screen
    label, rather than hardcoding it — this org's internal field names don't
    always match what's shown on screen (e.g. 'Contract Signed' is really
    stored as Network_Signed), so this is safer than guessing."""
    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    try:
        resp = requests.get(
            f"{ZOHO_API_DOMAIN}/crm/v2/settings/fields",
            headers=headers,
            params={"module": LEGAL_CONTRACTS_MODULE},
            timeout=20,
        )
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    for field in resp.json().get("fields", []):
        if (field.get("field_label") or "").strip().lower() == "amount":
            return field.get("api_name")
    return None


def get_legal_contract_amounts(account_ids):
    """Pulls each account's Legal Contracts related list and sums the Amount
    field. Only ever called for the small handful of accounts in the New
    Accounts Added list, so one request per account is fine here — this
    isn't the hundreds-of-accounts case the Contacts lookup had to avoid."""
    amount_field = get_amount_field_api_name()
    if not amount_field or not account_ids:
        return {}

    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    amounts = {}
    for account_id in account_ids:
        try:
            resp = requests.get(
                f"{ZOHO_API_DOMAIN}/crm/v2/Accounts/{account_id}/{LEGAL_CONTRACTS_MODULE}",
                headers=headers,
                params={"fields": amount_field},
                timeout=20,
            )
        except Exception:
            continue

        if resp.status_code != 200:
            continue  # 204 = no legal contracts on file for this account

        total = 0
        for record in resp.json().get("data", []):
            value = record.get(amount_field)
            if isinstance(value, (int, float)):
                total += value
        amounts[account_id] = total

    return amounts


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
if st.sidebar.button("🔄 Refresh data now", use_container_width=True):
    # Pull fresh data within this same session — a browser refresh (F5) would
    # start a brand-new session and force the password to be re-entered, so
    # this button re-runs the app in place instead, staying logged in.
    load_accounts.clear()
    get_contacts_lookup.clear()
    st.rerun()
st.sidebar.caption(f"Last refreshed: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
st.sidebar.caption(
    "Data refreshes from Zoho CRM automatically every 60 seconds, or instantly "
    "with the button above."
)

filtered_df = df[df["Urgency"].isin(selected_urgency)]
if name_search:
    filtered_df = filtered_df[
        filtered_df["Account Name"].str.contains(name_search, case=False, na=False)
    ]

# Rolling contract customers get their own list further down, regardless of
# the Urgency filter above — their contract term is a rolling 12-month
# marker rather than a genuine countdown, so being caught by the Red filter
# (or hidden by unticking it) isn't meaningful the way it is for everyone else.
name_filtered_df = df
if name_search:
    name_filtered_df = name_filtered_df[
        name_filtered_df["Account Name"].str.contains(name_search, case=False, na=False)
    ]
rolling_df = name_filtered_df[name_filtered_df["Rolling Contract"]].sort_values("Days Remaining")

# New deals also sit outside the Urgency filter — a freshly signed contract
# is worth surfacing regardless of how far off its renewal is.
new_deals_df = name_filtered_df[name_filtered_df["New Deal"]].sort_values(
    "Contract Signed Date", ascending=False
)

st.divider()

# --- Top-Line KPIs ---
kpi_cols = st.columns(6)
kpi_cols[0].metric("SYC Customers Tracked", f"{len(df)}")
kpi_cols[1].metric(
    "🔴 Red (< 12 months)",
    f"{len(df[(df['Urgency'] == 'Red') & (~df['Rolling Contract'])])}",
)
kpi_cols[2].metric("🟠 Amber (12–24 months)", f"{len(df[df['Urgency'] == 'Amber'])}")
kpi_cols[3].metric("⚪ No End Date", f"{len(df[df['Urgency'] == 'Unknown'])}")
kpi_cols[4].metric("🔄 Rolling Contracts", f"{len(df[df['Rolling Contract']])}")
kpi_cols[5].metric("🆕 New Accounts (30d)", f"{len(df[df['New Deal']])}")

st.divider()

# --- New Accounts Added ---
st.subheader("🆕 New Accounts Added (signed in the last 30 days)")
st.caption(
    "Contracts signed within the last 30 days — flag these to billing for onboarding."
)

new_deals_table_cols = [
    "Account Name",
    "Contract Signed Date",
    "Amount",
    "All Tags",
    "Open in Zoho",
]

if new_deals_df.empty:
    st.info("No contracts signed in the last 30 days.")
else:
    try:
        legal_contract_amounts = get_legal_contract_amounts(
            tuple(new_deals_df["Account ID"])
        )
    except Exception:
        legal_contract_amounts = {}

    new_deals_display_df = new_deals_df[new_deals_table_cols[:2] + new_deals_table_cols[3:]].copy()
    new_deals_display_df["Contract Signed Date"] = new_deals_df["Days Since Signed"].apply(
        days_since_label
    )
    new_deals_display_df["Amount"] = new_deals_df["Account ID"].apply(
        lambda acc_id: legal_contract_amounts.get(acc_id)
    )
    new_deals_display_df = new_deals_display_df[new_deals_table_cols]

    total_amount = sum(v for v in new_deals_display_df["Amount"] if pd.notna(v))
    new_deals_display_df["Amount"] = new_deals_display_df["Amount"].apply(
        lambda v: f"£{v:,.2f}" if pd.notna(v) else "—"
    )

    st.dataframe(
        new_deals_display_df,
        hide_index=True,
        use_container_width=True,
        column_config={"Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗")},
    )
    st.metric("💰 Total signed this month", f"£{total_amount:,.2f}")

st.divider()

# --- Watchlist Table ---
st.subheader("📋 Renewal Watchlist")

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
# Rolling contract accounts are excluded here too since they get their own
# section below instead.
unknown_df = filtered_df[
    (filtered_df["Urgency"] == "Unknown") & (~filtered_df["Rolling Contract"])
]
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
                    "All Tags",
                    "Open in Zoho",
                ]
            ],
            hide_index=True,
            use_container_width=True,
            column_config={"Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗")},
        )

# Rolling contract customers ("Contract Term (months)" == exactly 12) aren't
# on a genuine fixed end date, so being flagged Red in the main list above
# would be misleading — they get their own list here instead, still visible,
# just kept separate from the "actually expiring soon" watchlist.
st.divider()
st.subheader("🔄 Rolling Contract Customers")
st.caption(
    "Accounts on a rolling 12-month contract term. Shown here rather than "
    "flagged Red above, since their renewal date isn't a genuine deadline."
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
        use_container_width=True,
        column_config={"Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗")},
    )
