from datetime import date, timedelta

import streamlit as st

from database.database import execute, fetch_all, require_db_or_stop
from services import event_service
from utils.helpers import fmt_time, next_weapon_id

st.set_page_config(page_title="Weapon Events & Inventory", page_icon="🔫", layout="wide")
require_db_or_stop()

st.title("🔫 Weapon Events & Inventory")

tab_events, tab_inventory = st.tabs(["Weapon Events", "Weapon Inventory"])

# Pre-fetch inventory weapons once for use in both tabs
inventory_weapons = fetch_all("SELECT * FROM weapons ORDER BY weapon_id")
# Dropdown options: "W001 – Glock 19 (Available)", etc.
STATUS_ICON = {"Available": "🟢", "In Use": "🔴", "Maintenance": "🟡"}

def weapon_dropdown_options(weapons: list) -> list[str]:
    """Build label list for weapon selectbox from inventory."""
    return [
        f"{w['weapon_id']} – {w['weapon_type']} ({STATUS_ICON.get(w['status'], '')} {w['status']})"
        for w in weapons
    ]

with tab_events:
    c1, c2, c3 = st.columns(3)
    date_from = c1.date_input("From", value=date.today() - timedelta(days=7), key="we_date_from")
    date_to = c2.date_input("To", value=date.today(), key="we_date_to")

    weapon_types = ["All"] + sorted({row["weapon_type"] for row in fetch_all("SELECT DISTINCT weapon_type FROM weapon_events")})
    weapon_filter = c3.selectbox("Filter by Weapon type", weapon_types, key="we_filter_type")
    weapon_type = None if weapon_filter == "All" else weapon_filter

    events = event_service.get_events(date_from=date_from, date_to=date_to, weapon_type=weapon_type)

    if not events:
        st.caption("No weapon events found in this date range.")
    else:
        # 1. Main Events Table with human-verified badges
        table_rows = []
        for e in events:
            is_manual = bool(e.get("manual_weapon_type"))
            primary_weapon = f"✓ {e['manual_weapon_type']} (Verified)" if is_manual else e["weapon_type"]
            system_detected = e["weapon_type"] if is_manual else "—"
            verifier = e.get("manually_verified_by") or "—"

            table_rows.append({
                "Event ID": f"#{e['event_id']}",
                "Time": fmt_time(e["detected_at"]),
                "User": e.get("name") or e.get("user_name") or "Unidentified",
                "Weapon (Verified / Active)": primary_weapon,
                "System Detected": system_detected,
                "Confidence": f"{float(e['confidence']):.1f}%",
                "Verified By": verifier,
                "Camera": e["camera_id"] or "-",
                "Lane": e["lane_id"] or "-",
            })

        st.dataframe(
            table_rows,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("---")
        st.subheader("✏️ Manual Verification & Type Override")
        st.caption(
            "Operators can select the exact weapon from inventory or correct the AI-detected type. "
            "The original AI-detected value is permanently preserved for auditing."
        )

        inv_labels = weapon_dropdown_options(inventory_weapons)
        has_inventory = bool(inv_labels)

        # 2. Per-event edit controls (recent 15 events)
        for e in events[:15]:
            eid = e["event_id"]
            user_lbl = e.get("name") or e.get("user_name") or "Unidentified"
            curr_weapon = e.get("manual_weapon_type") or e["weapon_type"]
            is_verified = bool(e.get("manual_weapon_type"))

            exp_label = (
                f"Event #{eid} — {user_lbl} · {curr_weapon} "
                f"{'[✓ Manually Verified]' if is_verified else '[System Detected: ' + e['weapon_type'] + ']'}"
            )

            with st.expander(exp_label, expanded=False):
                ec1, ec2, ec3 = st.columns([3, 3, 2])

                with ec1:
                    if has_inventory:
                        # Try to preselect the matching inventory item
                        preselect_idx = 0
                        for i, lbl in enumerate(inv_labels):
                            if curr_weapon.lower() in lbl.lower():
                                preselect_idx = i
                                break

                        use_inventory = st.checkbox(
                            "Select from Inventory",
                            value=True,
                            key=f"use_inv_{eid}",
                        )

                        if use_inventory:
                            chosen_label = st.selectbox(
                                "Select Weapon from Inventory",
                                inv_labels,
                                index=preselect_idx,
                                key=f"inv_sel_{eid}",
                            )
                            # Extract type: "W001 – Glock 19 (🟢 Available)" → "Glock 19"
                            override_val = chosen_label.split("–", 1)[1].rsplit("(", 1)[0].strip()
                        else:
                            override_val = st.text_input(
                                "Specific / Verified Weapon Type",
                                value=curr_weapon,
                                key=f"manual_wpn_{eid}",
                            )
                    else:
                        override_val = st.text_input(
                            "Specific / Verified Weapon Type",
                            value=curr_weapon,
                            key=f"manual_wpn_{eid}",
                        )

                with ec2:
                    operator_name = st.text_input(
                        "Verified by (Operator Name)",
                        value=e.get("manually_verified_by") or "",
                        key=f"verifier_{eid}",
                    )

                with ec3:
                    st.write("")
                    st.write("")
                    if st.button("💾 Save Correction", key=f"btn_save_corr_{eid}", type="primary", use_container_width=True):
                        if not override_val.strip():
                            st.error("Weapon type cannot be blank.")
                        elif not operator_name.strip():
                            st.error("Operator name is required for audit verification.")
                        else:
                            event_service.set_manual_weapon_type(
                                event_id=eid,
                                weapon_type=override_val.strip(),
                                verified_by=operator_name.strip(),
                            )
                            st.success(f"Event #{eid} updated: {override_val.strip()} (Verified by {operator_name.strip()})")
                            st.rerun()

with tab_inventory:
    st.subheader("Inventory Management")
    st.caption(
        "Manage the physical weapon catalog. "
        "🟢 Available weapons are shown in Manual Verification dropdowns. "
        "Mark weapons as 🔴 In Use or 🟡 Maintenance to reflect their real-world status."
    )

    if not inventory_weapons:
        st.info("No weapons registered in inventory yet. Add one below.")
    else:
        # Header row
        hc1, hc2, hc3 = st.columns([2, 4, 3])
        hc1.markdown("**Weapon ID**")
        hc2.markdown("**Type / Model**")
        hc3.markdown("**Status**")
        st.markdown("<hr style='margin:4px 0 8px 0;'>", unsafe_allow_html=True)

        for w in inventory_weapons:
            curr_st = w["status"] if w["status"] in ["Available", "In Use", "Maintenance"] else "Available"
            icon = STATUS_ICON.get(curr_st, "")

            cols = st.columns([2, 4, 3])
            cols[0].markdown(f"**`{w['weapon_id']}`**")
            cols[1].markdown(f"{w['weapon_type']}")
            new_status = cols[2].selectbox(
                f"status_{w['weapon_id']}",
                ["Available", "In Use", "Maintenance"],
                index=["Available", "In Use", "Maintenance"].index(curr_st),
                key=f"inv_status_{w['weapon_id']}",
                label_visibility="collapsed",
                format_func=lambda s: f"{STATUS_ICON.get(s, '')} {s}",
            )
            if new_status != w["status"]:
                execute("UPDATE weapons SET status = %s WHERE weapon_id = %s", (new_status, w["weapon_id"]))
                st.toast(f"Weapon {w['weapon_id']} status updated to {new_status}")
                st.rerun()

    st.markdown("---")
    with st.expander("➕ Register New Inventory Weapon", expanded=False):
        wtype = st.text_input("Weapon type / model", key="new_weapon_type_input")
        if st.button("Add to Inventory", type="primary"):
            if wtype.strip():
                existing_ids = [w["weapon_id"] for w in inventory_weapons] if inventory_weapons else []
                new_id = next_weapon_id(existing_ids)
                execute(
                    "INSERT INTO weapons (weapon_id, weapon_type, status) VALUES (%s, %s, 'Available')",
                    (new_id, wtype.strip()),
                )
                st.success(f"Added new weapon: {new_id} ({wtype.strip()})")
                st.rerun()
            else:
                st.error("Weapon type is required.")
