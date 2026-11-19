## What changes

<!-- Language, IR, target or documentation change, and why. -->

## Checklist

- [ ] `python3 scripts/validate_release.py` passes
- [ ] Generator output changes are intentional (`python3 scripts/update_goldens.py`, diff reviewed)
- [ ] Runtime behaviour verified with `python3 scripts/e2e_runtime.py` for the affected targets
- [ ] Every target behaves the same way (`docs/GENERATED_API.md`)
- [ ] Documentation and `CHANGELOG.md` updated
