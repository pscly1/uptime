# uptime

Daily reachability checks for the sites I actually run, recorded as a git history so the answer to
"has this been flaky lately?" is `git log` instead of a memory.

**[→ current status](STATUS.md)**

| endpoint | what it is |
| --- | --- |
| `pscly.cn` | personal site |
| `sub.pscly.cc` | API gateway |
| `qqhfqz1.pscly.cc` | paid tool front-end |

## How it works

`.github/workflows/monitor.yml` runs once a day at 03:17 UTC:

1. runs the unit tests (because a monitor that silently breaks is worse than no monitor),
2. hits each target in `targets.json` with a 20 s timeout,
3. writes `status/latest.json`, appends to `status/history.jsonl` (last 90 runs), and regenerates
   `STATUS.md`,
4. commits the diff — **and only if there is a diff**, so the history is a record of change rather
   than a record of the passage of time.

If any endpoint fails, the job goes red so the failure is visible in the Actions tab; the data is
committed either way, because a failure is the data.

## Run it yourself

```bash
python3 monitor.py          # writes status/ and STATUS.md, exit 1 if anything is down
python3 -m unittest discover -s tests -v
```

Add or remove targets in `targets.json`:

```json
{ "name": "pscly.cn", "url": "https://pscly.cn", "expect": 200 }
```

## Design notes

- **Standard library only.** No `requests`, no install step in the workflow — a monitoring job that
  can itself fail to install is a bad monitoring job.
- **Every failure is a result, not an exception.** Unreachable, TLS error, timeout, and HTTP 4xx all
  produce a row, so one dead host cannot erase the other two.
- **`expect` is explicit.** A 200-only check misses a redirect loop that returns 200 at the end; the
  field makes the expectation visible in the repo.
- **The workflow commits nothing when nothing changed.** `git diff --quiet` gates the commit.
- **90 runs are kept.** Enough to see a trend, small enough that the JSONL stays readable.

## License

MIT
