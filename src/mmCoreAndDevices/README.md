# mmCoreAndDevices

This subtree was cloned from:

<https://github.com/micro-manager/mmCoreAndDevices.git@870fdb121ba977ab00fb1032cab320457a811cf1>

To pull in upstream changes, from the root of this project run:

```sh
git subtree pull --prefix=src/mmCoreAndDevices https://github.com/micro-manager/mmCoreAndDevices main --squash
```

This subtree should never diverge far from the upstream repository (with the
exception of things that are required to build against c++17, which are not yet
merged upstream).
