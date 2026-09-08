# Sources and validation

Checked 2026-09-04. These public AWS docs establish API behavior, not live resource state. Discover the current account, Region and resource type for each task.

| Official source | Retrieval | Used for |
|---|---|---|
| [Describe WorkSpaces](https://docs.aws.amazon.com/cli/latest/reference/workspaces/describe-workspaces.html) | Exa Contents | Desktop IDs, filters, bundle/directory metadata |
| [Describe WorkSpaces Pools](https://docs.aws.amazon.com/cli/latest/reference/workspaces/describe-workspaces-pools.html) | Exa Contents | Separate Pools API, capacity, errors, service pagination |
| [Describe directories](https://docs.aws.amazon.com/cli/latest/reference/ds/describe-directories.html) | Exa Contents | Directory type/state, DNS, VPC and AD Connector fields |
| [Update an Applications fleet](https://docs.aws.amazon.com/appstream2/latest/developerguide/update-fleets-new-image.html) | Exa Contents | Same/different OS, active sessions, mixed images and catalog risk |
| [Update fleet](https://docs.aws.amazon.com/cli/latest/reference/appstream/update-fleet.html) | Context7 CLI | `appstream` namespace, image flags, state/type restrictions |
| [Describe fleets](https://docs.aws.amazon.com/cli/latest/reference/appstream/describe-fleets.html) | Context7 CLI | Fleet discovery and name filtering |

Context7 resolved `AWS CLI` to `/websites/aws_amazon_cli`, then queried `appstream update-fleet` and `appstream describe-fleets`. Exa returned success for all four URLs. Only public API terms and URLs went to these tools.

Offline checks use AWS CLI `2.36.29`: Bash parsing, input skeletons, and projected output fields against its bundled API models. Generated output skeletons for some services fail their own sample-value validation; they are not live-service failures. No live AWS calls, permission checks, session tests, updates, or rollback were run. Runtime authorization, service state, capacity, and application behavior still need operator proof.
