"""(2026-10-20) The parts changed by the cowl fix and the printed-part review, for ROV_Reprint_2026-10-20.3mf."""
import parts_final as PF
WANT = {"801", "802", "803", "804", "805", "806", "216", "217", "218", "219", "401", "201", "202", "203", "301", "302", "303", "402"}
PRINTED_R = [p for p in PF.PRINTED if p[1][:3] in WANT]
