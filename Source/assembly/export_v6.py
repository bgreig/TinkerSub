"""
Exports the v6 additions to out_v5/ in print orientation: the blank 3" pod front cap (303).
Run after export_v5.py: python3 export_v6.py
"""
import os
import export_v5 as E, rov_v6 as V6

if __name__ == "__main__":
    os.makedirs(E.OUT, exist_ok=True)
    E.save("rov6_pod_endcap_3in_blank", V6.pod_endcap_blank(), flip=True)      # plate down, like the rear cap
