# identity-extract

Unified CLI to extract and prepare AWS IAM Identity Center data for the pipeline templates.

## Install/Run

Use it directly with Python:

```bash
python scripts/identity-extract/identity_extract.py --help
```

Install dependencies:

```bash
pip install -r scripts/identity-extract/requirements.txt
```

Optional virtualenv setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r scripts/identity-extract/requirements.txt
```

## Global options

Use these flags after the subcommands:

- `--profile` AWS CLI profile name (optional)
- `--region` AWS region (optional)

Example:

```bash
python scripts/identity-extract/identity_extract.py \
  assignments extract \
  --profile my-aws-profile \
  --region us-east-1 \
  --instance-arn arn:aws:sso:::instance/ssoins-12345678abc \
  --identity-store-id d-12345678 \
  --output templates/assignments/template_assignments.json
```

## Tutorial (Step by Step)

### Step 1: Extract assignments

Use this to build the assignments template from IAM Identity Center.

```bash
python scripts/identity-extract/identity_extract.py \
  assignments extract \
  --instance-arn arn:aws:sso:::instance/ssoins-12345678abc \
  --identity-store-id d-12345678 \
  --profile my-aws-profile \
  --region us-east-1 \
  --output templates/assignments/template_assignments.json
```

### Step 2 (optional): Filter Control Tower assignments

If your org uses Control Tower, remove Control Tower related assignments from the template.

```bash
python scripts/identity-extract/identity_extract.py assignments filter-controltower \
  --input templates/assignments/template_assignments.json \
  --output templates/assignments/filtered_template_assignments.json
```

### Step 3: Export permission sets

Use this to export permission sets and generate individual files in the output directory.
The aggregated JSON is removed after split.

```bash
python scripts/identity-extract/identity_extract.py permissionsets export \
  --instance-arn arn:aws:sso:::instance/ssoins-12345678abc \
  --profile my-aws-profile \
  --region us-east-1 \
  --output templates/permissionsets/formatted_permission_sets.json \
  --output-dir templates/permissionsets
```

## Other commands

### Assignments optimize

Use this to re-optimize an existing assignments JSON if you need to re-group it.

```bash
python scripts/identity-extract/identity_extract.py assignments optimize \
  --input templates/assignments/template_assignments.json \
  --output templates/assignments/optimized_template_assignments.json \
  --profile my-aws-profile \
  --region us-east-1
```

### Permission sets list-unused

Use this to list permission sets not assigned to any account.

```bash
python scripts/identity-extract/identity_extract.py permissionsets list-unused \
  --instance-arn arn:aws:sso:::instance/ssoins-12345678abc \
  --profile my-aws-profile \
  --region us-east-1
```

### Permission sets fill-description

Use this to fill empty descriptions across the permission set JSON files.

```bash
python scripts/identity-extract/identity_extract.py permissionsets fill-description \
  --dir templates/permissionsets \
  --value ps-description \
  --profile my-aws-profile \
  --region us-east-1
```

### Permission sets tag

Use this to tag permission sets with `SSOPipeline=true` (dry-run by default).

```bash
python scripts/identity-extract/identity_extract.py permissionsets tag \
  --instance-arn arn:aws:sso:::instance/ssoins-12345678abc \
  --profile my-aws-profile \
  --region us-east-1
```

Apply tags:

```bash
python scripts/identity-extract/identity_extract.py permissionsets tag \
  --instance-arn arn:aws:sso:::instance/ssoins-12345678abc \
  --profile my-aws-profile \
  --region us-east-1 \
  --apply
```

### OUs list-nested

Use this to list nested OU IDs for a parent OU.

```bash
python scripts/identity-extract/identity_extract.py ous list-nested \
  --ou-id ou-xxxx-xxxxxxxx \
  --profile my-aws-profile \
  --region us-east-1
```
