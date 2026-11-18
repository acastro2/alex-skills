# Facts for PR #329 (branch fix/schedules-404, base main)

Ticket API-877: "GET /v1/devices/{id}/schedules returns 200 with an empty list for a device that does not exist. The mobile app shows 'No schedules' instead of 'Device removed', and support gets tickets for it."

## $ git log --reverse --format='%h %s' main..HEAD
41d2a07 fix(api): return 404 for schedules of an unknown device
5e8b913 feat(sdk): raise DeviceNotFound on 404 from list_schedules
6f0c4a2 docs(api): document the 404 in openapi.yaml

## $ git diff --name-status main HEAD
M	src/api/handlers/schedules.py
M	src/sdk/client.py
M	src/sdk/errors.py
M	openapi.yaml
M	tests/api/test_schedules.py
M	tests/sdk/test_client.py

## $ git diff --shortstat main HEAD -- src
 3 files changed, 14 insertions(+), 2 deletions(-)

## $ git diff --shortstat main HEAD -- tests
 2 files changed, 58 insertions(+), 6 deletions(-)
