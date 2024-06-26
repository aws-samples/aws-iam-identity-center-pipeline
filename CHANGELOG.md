# Change Log
All notable changes to this project will be documented in this file.
 
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [1.3.0] - 2024-03-28
### Added
- Added notification capability for failures in pipeline and CodeCommit status change
- Added CloudFormation metadata for parameters

### Changed
- Changed AWS partition hard-coded in ARNs for dynamic "${AWS::Partition}" to support multiple partitions
- Renamed CloudFormation parameters for cohesion
- Updated Python runtime in Lambda functions from 3.9 to 3.11
- Updated CodeBuild image version from amazonlinux2-x86_64-standard:3.0 to amazonlinux2-x86_64-standard:5.0
- Updated Terraform version from 1.4.4 to 1.7.5
- Removed unused CodeBuild environment variable IDENTITYCENTER_REPOSITORY

### Fixed
- Fixed CloudFormation parameter descriptions

## [1.2.1] - 2023-06-06
### Added
- N/A
 
### Changed
- Moved EventBridge and Lambda resources to Management account. The CloudTrail action "MoveAccount" must me captured in the us-east-1 of the AWS Organization Management Account.
- Added limitations in the README.md.

### Fixed
- N/A

## [1.2.0] - 2023-04-11
### Added
- Ability to deploy the pipeline in Identity Center delegated administrator account. For this, an IAM role needs to be deployed in the AWS Organization administrator account so the pipeline can look up for information using this role. See "Getting Started" for more information.
 
### Changed
- Assignment step in the pipeline is now using Terraform. A python script will resolve all OUs to AWS accounts and store in a file, that is used by Terraform. In this way, the pipeline will make much less APIs calls do Identity Center and will manage state, increasing speed. DynamoDB that was previously used is not required anymore and must be manually deleted.
- Permissions cannot be assigned to Management account (this is the Identity Center service limitation once you delegate the administration)
- Pipeline manual approval was removed. Most customer are managing approval via Pull Requests and this feature was being removed by them.

### Fixed
- N/A

## [1.1.0] - 2022-12-08
### Added
- Ability to add Permission Boundary and Customer Manager policy to Permission Sets
- Ability to reference OU name in assignment templates (see README)
 
### Changed
- Validation step now also validates AWS managed policies for Permission Boundary 
- Improved logging messages for better troubleshooting
 
### Fixed
- If it is first time running the pipeline, DynamoDB table will be created; If something goes wrong with the first pipeline run, the same table will be deleted; This avoid having to manually delete DynamoDB in case of errors

## [1.0.1] - 2022-06-05
### Added

### Changed
- N/A
 
### Fixed
- Added a missing permission in IAM role
- Better mechanism for managing Identity Center API throttling

## [1.0.0] - 2022-03-21
 
Initial version of the solution
 
### Added
- [AWS Single Sign On Pipeline](.) First release of the solution.

### Changed
- N/A
 
### Fixed
- N/A
