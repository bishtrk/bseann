# app.py
import re
import json
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

API_BASE = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
BSE_ANN_PAGE = "https://www.bseindia.com/corporates/ann.html"
PDF_VIEW_BASE = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/"

st.set_page_config(page_title="BSE Announcements Explorer", layout="wide")
st.title("BSE Announcements Explorer")

# -------------------------
# Utilities
# -------------------------
def format_date_for_api(d):
    return d.strftime("%Y%m%d")

def _extract_json_from_html(text):
    """
    Best-effort: find a JSON blob containing "Table": [...] inside HTML and parse it.
    """
    # try a direct JSON object containing "Table"
    m = re.search(r'(\{[\s\S]*?"Table"\s*:\s*\[.*?\][\s\S]*?\})', text)
    if m:
        candidate = m.group(1)
        try:
            return json.loads(candidate)
        except Exception:
            pass
    # try JS variable: var foo = {... "Table": [...] };
    m2 = re.search(r'var\s+[A-Za-z0-9_]+\s*=\s*(\{[\s\S]*?"Table"\s*:\s*\[.*?\][\s\S]*?\});', text)
    if m2:
        try:
            return json.loads(m2.group(1))
        except Exception:
            pass
    return None

def build_pdf_url(attachment_name):
    if not attachment_name:
        return None
    return PDF_VIEW_BASE + attachment_name

def try_download_pdf(url, timeout=30):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200 and r.headers.get("content-type", "").lower().startswith(("application/pdf", "application/octet-stream")):
            return r.content
    except Exception:
        return None
    return None

# -------------------------
# Robust fetch function (returns 3 values)
# -------------------------
def fetch_announcements(scrip, category, prev_date, to_date, str_search, str_type, subcategory, pageno, timeout=20):
    """
    Returns (table_list_or_None, meta_dict_or_None, raw_html_or_None)
    - If successful JSON: returns (table, meta, None)
    - If HTML fallback and JSON extracted: returns (table, meta, None)
    - If HTML fallback and no JSON: returns (None, None, raw_html)
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": BSE_ANN_PAGE,
    })

    # prime session by visiting the announcements page to collect cookies (best-effort)
    try:
        session.get(BSE_ANN_PAGE, timeout=timeout)
    except Exception:
        pass  # still try the API call

    params = {
        "pageno": pageno,
        "strCat": category,
        "strPrevDate": format_date_for_api(prev_date),
        "strScrip": scrip,
        "strSearch": str_search if str_search != "All" else "P",
        "strToDate": format_date_for_api(to_date),
        "strType": str_type,
        "subcategory": subcategory
    }

    try:
        resp = session.get(API_BASE, params=params, timeout=timeout)
    except Exception as e:
        raise RuntimeError(f"Network error when calling BSE API: {e}")

    content_type = resp.headers.get("content-type", "").lower()
    text = resp.text

    # Case 1: JSON response
    if "application/json" in content_type or text.strip().startswith("{"):
        try:
            j = resp.json()
            table = j.get("Table", [])
            meta = j.get("Table1", [{}])[0] if j.get("Table1") else {}
            return table, meta, None
        except Exception:
            # malformed JSON despite content-type -> fall through to HTML extraction attempt
            pass

    # Case 2: HTML returned. Try to extract embedded JSON
    embedded = _extract_json_from_html(text)
    if embedded:
        table = embedded.get("Table", [])
        meta = embedded.get("Table1", [{}])[0] if embedded.get("Table1") else {}
        return table, meta, None

    # Case 3: no usable JSON found - return raw HTML for debugging
    return None, None, text

# -------------------------
# Sidebar: filters / params
# -------------------------
with st.sidebar.form("filters"):
    st.header("Query parameters")
    scrip = st.text_input("Scrip code", value="543985")
    category = st.text_input("Category (strCat)", value="Company Update")
    prev_date = st.date_input("From (YYYY-MM-DD)", value=datetime(2025, 8, 1))
    to_date = st.date_input("To (YYYY-MM-DD)", value=datetime(2025, 9, 1))
    str_search = st.selectbox("strSearch", options=["P", "S", "All"], index=0)
    str_type = st.text_input("strType", value="C")
    subcategory = st.text_input("subcategory", value="-1")
    pageno = st.number_input("Page number", min_value=1, value=1, step=1)
    fetch_btn = st.form_submit_button("Fetch announcements")

# -------------------------
# Fetch & display logic
# -------------------------
if fetch_btn:
    with st.spinner("Fetching announcements..."):
        try:
            table, meta, raw_html = fetch_announcements(
                scrip=scrip,
                category=category,
                prev_date=prev_date,
                to_date=to_date,
                str_search=str_search,
                str_type=str_type,
                subcategory=subcategory,
                pageno=pageno
            )
        except Exception as e:
            st.error(f"Failed to fetch data: {e}")
            st.stop()

    # If we received JSON table(s)
    if table is not None:
        if not table:
            st.info("No announcements found for given filters.")
            st.stop()

        df = pd.json_normalize(table)
        cols = [
            "DT_TM", "HEADLINE", "SUBCATNAME", "NEWSSUB", "CRITICALNEWS",
            "ATTACHMENTNAME", "Fld_Attachsize", "NSURL", "SCRIP_CD", "SLONGNAME", "PDFFLAG"
        ]
        present_cols = [c for c in cols if c in df.columns]
        df_display = df[present_cols].copy()
        if "DT_TM" in df_display.columns:
            df_display["DT_TM"] = pd.to_datetime(df_display["DT_TM"], errors="coerce")
            df_display = df_display.sort_values("DT_TM", ascending=False)

        # Add PDF URL column
        df_display["PDF_URL"] = df_display["ATTACHMENTNAME"].apply(lambda x: build_pdf_url(x) if x else "")

        st.markdown(f"**Total results (page {pageno})**: {meta.get('ROWCNT', 'unknown')}")
        st.dataframe(df_display.reset_index(drop=True), use_container_width=True)

        # Download buttons section
        st.markdown("---")
        st.subheader("PDF Downloads and Links")
        for i, (_, row) in enumerate(df_display.iterrows()):
            if row.get("ATTACHMENTNAME") and row.get("PDF_URL"):
                st.write(f"**{row.get('HEADLINE', 'Announcement')}** - {row.get('SCRIP_CD', '')}")
                cols = st.columns([1, 2])
                with cols[0]:
                    st.markdown(f"[Download PDF]({row['PDF_URL']})")
                with cols[1]:
                    st.write(f"Full PDF URL: `{row['PDF_URL']}`")
                st.markdown("---")

        st.caption("Tip: if attachments do not download, BSE may block hotlinking. Use 'Open PDF' / 'Open company page' to view in BSE UI.")

    else:
        # table is None -> probably HTML or anti-bot page returned. Show HTML excerpt for debugging.
        st.error("Endpoint returned HTML (not JSON). Showing first 4000 characters for debugging.")
        st.code(raw_html[:4000] if raw_html else "No response body available.")
        st.markdown("[Open announcements page on BSE for manual inspection](https://www.bseindia.com/corporates/ann.html)")

else:
    st.info("Set filters in the sidebar and click **Fetch announcements**.")
