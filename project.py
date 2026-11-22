"""Find flags with a full, stable rollout observation window."""
from datetime import date, timedelta

TITLE = "Flag Retirement Board"
DESCRIPTION = "Identify feature flags that held one terminal rollout state throughout a measured traffic window."
PROMPT = ("Explain retirement candidates using observed days, minimum traffic and error counts. "
          "Distinguish fully enabled from disabled flags and state what needs owner review before deletion.")


def day(value):
    if not isinstance(value, str):
        raise ValueError("Use YYYY-MM-DD dates.")
    result = date.fromisoformat(value)
    if result.isoformat() != value:
        raise ValueError("Use YYYY-MM-DD dates.")
    return result


def analyze(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Input must be an object.")
    end = day(data.get("as_of"))
    window, minimum = data.get("window_days", 7), data.get("min_daily_evaluations", 25)
    if type(window) is not int or not 1 <= window <= 366 or type(minimum) is not int or minimum < 1:
        raise ValueError("Use a 1–366 day window and a positive minimum daily evaluation count.")
    if end.toordinal() < window:
        raise ValueError("The observation window starts before the supported calendar.")
    start = end - timedelta(days=window - 1)
    flags = data.get("flags")
    if not isinstance(flags, dict) or not flags:
        raise ValueError("Provide flags as a nonempty mapping of names to daily observations.")
    rows = []
    for name, observations in flags.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(observations, list):
            raise ValueError("Each named flag needs a list of daily observations.")
        dates, recent = set(), []
        for observation in observations:
            if not isinstance(observation, dict):
                raise ValueError(f"{name}: each observation must be an object.")
            when = day(observation.get("date"))
            rollout, traffic, errors = [observation.get(k) for k in ("rollout_pct", "evaluations", "errors")]
            if (any(type(v) is not int for v in (rollout, traffic, errors))
                    or not 0 <= rollout <= 100 or not 0 <= errors <= traffic):
                raise ValueError(f"{name}: invalid rollout percentage or evaluation/error counts.")
            if when > end or when in dates:
                raise ValueError(f"{name}: dates must be unique and on or before as_of.")
            dates.add(when)
            if when >= start:
                recent.append((rollout, traffic, errors))
        levels = {r for r, _, _ in recent}
        lowest = min((n for _, n, _ in recent), default=None)
        failures = sum(x for _, _, x in recent)
        if len(recent) < window:
            decision = "Hold: missing days"
        elif levels not in ({0}, {100}):
            decision = "Hold: changing or partial rollout"
        elif lowest < minimum:
            decision = "Hold: insufficient traffic"
        elif failures:
            decision = "Hold: observed errors"
        else:
            decision = "Review enabled branch" if levels == {100} else "Review disabled branch"
        rows.append({"Flag": name, "Decision": decision, "Observed days": len(recent),
                     "Rollout levels (%)": ", ".join(str(n) for n in sorted(levels)),
                     "Lowest daily evaluations": lowest, "Errors in window": failures})
    eligible = sum(r["Decision"].startswith("Review") for r in rows)
    return {"summary": f"{eligible} of {len(rows)} flags meet the evidence threshold for owner review.",
            "metrics": {"Flags": len(rows), "Review candidates": eligible, "Window days": window}, "rows": rows}
