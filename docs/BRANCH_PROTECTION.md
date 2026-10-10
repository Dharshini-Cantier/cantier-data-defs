# Branch protection + CODEOWNERS (task B1.4)

`.github/CODEOWNERS` says who must approve changes per folder. It only takes effect when the repo is on GitHub
and a repo admin turns on the rule below. Done when: a pull request that changes `glossary/` cannot be merged
until a data steward approves and the `validate` check is green.

## 1. Before enabling

Replace the placeholders in `.github/CODEOWNERS` with real GitHub usernames or teams (company accounts).
GitHub ignores owners it does not know.

## 2. GitHub -> Settings -> Branches -> Add branch protection rule -> `main`

- [x] Require a pull request before merging
  - [x] Require approvals: **1**
  - [x] Require review from **Code Owners**
  - [x] Dismiss stale pull request approvals when new commits are pushed
- [x] Require status checks to pass before merging -> select **`validate`**
  - [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings
- [ ] Allow force pushes - **off**
- [ ] Allow deletions - **off**

(New GitHub UI: Settings -> Rules -> Rulesets -> New branch ruleset, same options.)

## 3. Test it

1. Create a branch, change one description in `glossary/enums.yaml` without bumping the version, open a pull request.
2. Expect: `validate` fails (version check) and the merge button is blocked until a code owner approves.

## If the team uses AWS CodeCommit instead

CodeCommit has no CODEOWNERS file: use an approval rule template (1 approval from the data-steward IAM role on `main`)
and deny direct pushes to `main` with an IAM condition on `codecommit:References`.
