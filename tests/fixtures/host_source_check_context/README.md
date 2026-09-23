# Exact historical input and source-preflight, not current execution permission

Copied without edits from already-retained native artifacts: input.json from
run35819538967/artifact10732853090; preflight.json from run35813943991.
The input SHA256 is 2626a4237beb14f674ae0e304466558ad5011730054ef9318410e57efbe0c5db.
The preflight Git blob is f36f55f22029679c8b0256a52c1c9923a2f3429d and its source
commit is 3b85b865ba61c2a29b24ff7981869363324d6d5c. Both match the original input
binding. The original cutoff is 2026-09-23T04:44:29.795878+00:00.

The test projects existing query status/window into metadata only. It neither
replays a model call nor converts the failed original Quick into a valid result,
nor treats expired preflight records as present-day permission or source truth.
Source documents and model outputs remain in their original archives, not here.
