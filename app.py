from datetime import datetime
from html import escape

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="HackMD Dashboard",
    page_icon="NOTE",
    layout="wide",
)

API_BASE_URL = "https://api.hackmd.io/v1"
API_URL = f"{API_BASE_URL}/notes"

st.title("HackMD Notes Dashboard")
st.caption("Connected to HackMD REST API")


def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


@st.cache_data(ttl=60, show_spinner=False)
def fetch_notes(token):
    response = requests.get(
        API_URL,
        headers=get_headers(token),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, list):
        raise ValueError("Unexpected API response format")

    return data


@st.cache_data(ttl=60, show_spinner=False)
def fetch_note_detail(note_id, token):
    response = requests.get(
        f"{API_URL}/{note_id}",
        headers=get_headers(token),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, dict):
        raise ValueError("Unexpected note detail response format")

    return data


def update_note(note_id, token, payload):
    response = requests.patch(
        f"{API_URL}/{note_id}",
        headers=get_headers(token),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()


def delete_note(note_id, token):
    response = requests.delete(
        f"{API_URL}/{note_id}",
        headers=get_headers(token),
        timeout=30,
    )
    response.raise_for_status()


def parse_tags(tags_text):
    return [tag.strip() for tag in tags_text.split(",") if tag.strip()]


def permission_index(value, options):
    return options.index(value) if value in options else 0


def get_folders(note):
    folders = note.get("folderPaths") or []
    return [folder.get("name", "") for folder in folders if folder.get("name")]


def get_note_link(note):
    if note.get("publishLink"):
        return note["publishLink"]

    if note.get("permalink"):
        if note.get("userPath"):
            return f"https://hackmd.io/@{note['userPath']}/{note['permalink']}"
        if note.get("teamPath"):
            return f"https://hackmd.io/@{note['teamPath']}/{note['permalink']}"
        return f"https://hackmd.io/{note['permalink']}"

    if note.get("shortId"):
        return f"https://hackmd.io/{note['shortId']}"

    if note.get("id"):
        return f"https://hackmd.io/{note['id']}"

    return ""


def format_date(timestamp):
    if not timestamp:
        return "N/A"

    try:
        return datetime.fromtimestamp(timestamp / 1000).strftime("%d %b %Y, %I:%M %p")
    except (ValueError, TypeError, OSError):
        return "N/A"


try:
    token = st.secrets["HACKMD_API_TOKEN"]

    with st.spinner("Fetching HackMD notes..."):
        notes = fetch_notes(token)

except KeyError:
    st.error("API token missing. Add HACKMD_API_TOKEN in Streamlit secrets.")
    st.stop()

except requests.exceptions.HTTPError as e:
    status = e.response.status_code
    st.error(f"HackMD API error: HTTP {status}")

    if status == 401:
        st.warning("Token invalid ho sakta hai. Authentication check karo.")
    elif status == 403:
        st.warning("API permission denied.")
    st.stop()

except requests.exceptions.RequestException as e:
    st.error(f"Network/API connection failed: {e}")
    st.stop()

except ValueError as e:
    st.error(str(e))
    st.stop()


columns = [
    "ID",
    "Title",
    "Description",
    "Folders",
    "Tags",
    "Created",
    "Updated",
    "Created Timestamp",
    "Updated Timestamp",
    "Open Link",
    "Read Permission",
    "Write Permission",
    "Content",
]
rows = []

for note in notes:
    rows.append(
        {
            "ID": note.get("id", ""),
            "Title": note.get("title") or "Untitled Note",
            "Description": note.get("description") or "",
            "Folders": ", ".join(get_folders(note)) or "Unfiled",
            "Tags": ", ".join(note.get("tags") or []),
            "Created": format_date(note.get("createdAt")),
            "Updated": format_date(note.get("lastChangedAt")),
            "Created Timestamp": note.get("createdAt") or 0,
            "Updated Timestamp": note.get("lastChangedAt") or 0,
            "Open Link": get_note_link(note),
            "Read Permission": note.get("readPermission") or "N/A",
            "Write Permission": note.get("writePermission") or "N/A",
            "Content": note.get("content") or "",
        }
    )

df = pd.DataFrame(rows, columns=columns)

col1, col2, col3 = st.columns(3)
col1.metric("Total Notes", len(df))
col2.metric("Folders", len({folder for note in notes for folder in get_folders(note)}))
col3.metric("Tags", len({tag for note in notes for tag in (note.get("tags") or [])}))

st.divider()

st.subheader("Search, Filter & Sort")

search = st.text_input(
    "Search notes",
    placeholder="Example: Abstract Class, SQL, Python...",
)

all_folders = sorted({folder for note in notes for folder in get_folders(note)})
all_tags = sorted({tag for note in notes for tag in (note.get("tags") or [])})

filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    selected_folders = st.multiselect(
        "Folders",
        all_folders,
        placeholder="All folders",
    )

with filter_col2:
    selected_tags = st.multiselect(
        "Tags",
        all_tags,
        placeholder="All tags",
    )

with filter_col3:
    sort_by = st.selectbox(
        "Sort by",
        [
            "Last updated: newest first",
            "Last updated: oldest first",
            "Created: newest first",
            "Created: oldest first",
            "Title: A to Z",
            "Title: Z to A",
            "Folder: A to Z",
        ],
    )

filtered = df.copy()

if search:
    search_columns = ["Title", "Description", "Folders", "Tags", "Content"]
    mask = (
        filtered[search_columns]
        .fillna("")
        .agg(" ".join, axis=1)
        .str.contains(search, case=False, na=False, regex=False)
    )
    filtered = filtered[mask]

if selected_folders:
    filtered = filtered[
        filtered["Folders"].apply(
            lambda value: any(folder in value.split(", ") for folder in selected_folders)
        )
    ]

if selected_tags:
    filtered = filtered[
        filtered["Tags"].apply(
            lambda value: any(tag in value.split(", ") for tag in selected_tags)
        )
    ]

sort_options = {
    "Last updated: newest first": ("Updated Timestamp", False),
    "Last updated: oldest first": ("Updated Timestamp", True),
    "Created: newest first": ("Created Timestamp", False),
    "Created: oldest first": ("Created Timestamp", True),
    "Title: A to Z": ("Title", True),
    "Title: Z to A": ("Title", False),
    "Folder: A to Z": ("Folders", True),
}
sort_column, ascending = sort_options[sort_by]
filtered = filtered.sort_values(by=sort_column, ascending=ascending, kind="stable")

st.caption(f"Showing {len(filtered)} notes")

st.subheader("Your Notes")

display_columns = [
    "Title",
    "Description",
    "Folders",
    "Tags",
    "Updated",
    "Open Link",
]

st.dataframe(
    filtered[display_columns],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Open Link": st.column_config.LinkColumn(
            "Open",
            display_text="Open in new tab",
        )
    },
)

st.subheader("Note Details")

if not filtered.empty:
    selected_id = st.selectbox(
        "Select a note",
        filtered["ID"].tolist(),
        format_func=lambda note_id: filtered.loc[
            filtered["ID"] == note_id, "Title"
        ].iloc[0],
    )

    note = filtered[filtered["ID"] == selected_id].iloc[0]

    try:
        note_detail = fetch_note_detail(selected_id, token)
    except requests.exceptions.HTTPError as e:
        note_detail = {}
        st.warning(
            f"Note detail load nahi hua: HTTP {e.response.status_code}. "
            "Edit content ke liye detail API access chahiye."
        )
    except requests.exceptions.RequestException as e:
        note_detail = {}
        st.warning(f"Note detail load nahi hua: {e}")
    except ValueError as e:
        note_detail = {}
        st.warning(str(e))

    st.markdown(f"### {note['Title']}")
    st.write(note["Description"] or "No description available.")

    left, right = st.columns(2)

    with left:
        st.write("**Folders:**", note["Folders"])
        st.write("**Tags:**", note["Tags"] or "No tags")

    with right:
        st.write("**Created:**", note["Created"])
        st.write("**Last updated:**", note["Updated"])

    st.write("**Read permission:**", note["Read Permission"])
    st.write("**Write permission:**", note["Write Permission"])

    action_col1, action_col2, action_col3 = st.columns([1, 1, 1])

    with action_col1:
        if note["Open Link"]:
            st.markdown(
                f'<a href="{escape(note["Open Link"])}" target="_blank" '
                'rel="noopener noreferrer">Open Note in HackMD</a>',
                unsafe_allow_html=True,
            )

    with action_col2:
        if st.button("Edit note", type="primary"):
            st.session_state["editing_note_id"] = selected_id
            st.session_state.pop("pending_delete_id", None)

    with action_col3:
        if st.button("Delete note", type="secondary"):
            st.session_state["pending_delete_id"] = selected_id
            st.session_state.pop("editing_note_id", None)

    if st.session_state.get("editing_note_id") == selected_id:
        st.divider()
        st.markdown("#### Edit Note")

        permission_options = ["owner", "signed_in", "guest"]
        current_title = note_detail.get("title") or note["Title"]
        current_description = note_detail.get("description") or note["Description"]
        current_tags = ", ".join(note_detail.get("tags") or parse_tags(note["Tags"]))
        current_content = note_detail.get("content") or note["Content"]
        current_read_permission = note_detail.get("readPermission") or note[
            "Read Permission"
        ]
        current_write_permission = note_detail.get("writePermission") or note[
            "Write Permission"
        ]

        with st.form(f"edit-note-{selected_id}"):
            edit_title = st.text_input("Title", value=current_title)
            edit_description = st.text_area(
                "Description",
                value=current_description,
                height=90,
            )
            edit_tags = st.text_input(
                "Tags",
                value=current_tags,
                help="Comma separated tags, example: python, sql, college",
            )
            edit_content = st.text_area(
                "Content",
                value=current_content,
                height=320,
            )

            perm_col1, perm_col2 = st.columns(2)
            with perm_col1:
                edit_read_permission = st.selectbox(
                    "Read permission",
                    permission_options,
                    index=permission_index(current_read_permission, permission_options),
                )
            with perm_col2:
                edit_write_permission = st.selectbox(
                    "Write permission",
                    permission_options,
                    index=permission_index(
                        current_write_permission, permission_options
                    ),
                )

            save_col, cancel_col = st.columns([1, 1])
            with save_col:
                submitted = st.form_submit_button("Save changes", type="primary")
            with cancel_col:
                cancelled = st.form_submit_button("Cancel")

        if cancelled:
            st.session_state.pop("editing_note_id", None)
            st.rerun()

        if submitted:
            if not edit_title.strip():
                st.error("Title blank nahi ho sakta.")
            else:
                payload = {
                    "title": edit_title.strip(),
                    "description": edit_description.strip(),
                    "tags": parse_tags(edit_tags),
                    "content": edit_content,
                    "readPermission": edit_read_permission,
                    "writePermission": edit_write_permission,
                }

                try:
                    update_note(selected_id, token, payload)
                    fetch_notes.clear()
                    fetch_note_detail.clear()
                    st.session_state.pop("editing_note_id", None)
                    st.success("Note updated successfully.")
                    st.rerun()
                except requests.exceptions.HTTPError as e:
                    st.error(
                        f"Update failed: HTTP {e.response.status_code}. "
                        f"Response: {e.response.text}"
                    )
                except requests.exceptions.RequestException as e:
                    st.error(f"Update failed: {e}")

    if st.session_state.get("pending_delete_id") == selected_id:
        st.warning(
            f"Delete '{note['Title']}'? Ye action HackMD se note permanently remove karega."
        )
        confirm_col, cancel_col = st.columns([1, 1])

        with confirm_col:
            if st.button("Yes, delete permanently", type="primary"):
                try:
                    delete_note(selected_id, token)
                    fetch_notes.clear()
                    fetch_note_detail.clear()
                    st.session_state.pop("pending_delete_id", None)
                    st.success("Note deleted successfully.")
                    st.rerun()
                except requests.exceptions.HTTPError as e:
                    st.error(
                        f"Delete failed: HTTP {e.response.status_code}. "
                        "Token permissions ya note access check karo."
                    )
                except requests.exceptions.RequestException as e:
                    st.error(f"Delete failed: {e}")

        with cancel_col:
            if st.button("Cancel"):
                st.session_state.pop("pending_delete_id", None)
                st.rerun()

    display_content = note_detail.get("content") or note["Content"]

    if display_content:
        with st.expander("View content returned by API"):
            st.markdown(display_content)
    else:
        st.info(
            "List API ne is note ka content return nahi kiya. "
            "Actual content ke liye note detail endpoint check karein."
        )

else:
    st.info("No notes match your search or filters.")

if st.button("Refresh Notes"):
    fetch_notes.clear()
    fetch_note_detail.clear()
    st.rerun()

st.caption("HackMD API - Data refresh cache: 60 seconds")
