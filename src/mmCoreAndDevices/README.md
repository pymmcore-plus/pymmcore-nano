# mmCoreAndDevices

This subtree was cloned from:

<https://github.com/micro-manager/mmCoreAndDevices.git@f2a5c90432635bd3ff176953c7c3b39039009bb0>

To pull in upstream changes, from the root of this project run:

```sh
python scripts/update_sources.py
python scripts/patch_sources.py
```

This subtree should never diverge far from the upstream repository (with the
exception of things that are required to build against c++17, which are not yet
merged upstream).
