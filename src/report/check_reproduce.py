"""复现校验：重跑模型后与 ledger/prediction.json 中记录值比较，判据 |ΔP| ≤ 2·MCSE。"""
import json
import sys

from src.fetch.common import ROOT


def main() -> int:
    pred = json.loads((ROOT / "ledger/prediction.json").read_text(encoding="utf-8"))
    cur = json.loads((ROOT / "artifacts/model/verdict.json").read_text(encoding="utf-8"))
    rec_p = pred["probability"]["point"]
    mcse = pred["probability"]["mcse"]
    diff = abs(cur["P_base"] - rec_p)
    tol = 2 * mcse + 1e-9
    print(f"recorded P={rec_p} | recomputed P={cur['P_base']:.4f} | diff={diff:.5f} | tol=2·MCSE={tol:.5f}")
    ok = diff <= tol and cur["seed"] == pred["probability"]["rng_seed"]
    print("REPRODUCE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
