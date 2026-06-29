name: Pull request
description: Open a PR against `main`
title: ""
labels: []
assignees: []

body:
  - type: markdown
    attributes:
      value: |
        Thanks for contributing. Please fill in the template below so reviewers can act fast.

  - type: dropdown
    id: type
    attributes:
      label: Type of change
      options:
        - Bug fix
        - New feature
        - Breaking change
        - Refactor / cleanup
        - Documentation
        - CI / infrastructure
        - Security fix
    validations:
      required: true

  - type: textarea
    id: summary
    attributes:
      label: What & why
      description: One-paragraph summary of the change and its motivation.
    validations:
      required: true

  - type: textarea
    id: testing
    attributes:
      label: How was this tested?
      description: Tests added, manual verification steps, screenshots, etc.
    validations:
      required: true

  - type: dropdown
    id: scope
    attributes:
      label: Approximate size
      options:
        - < 50 lines
        - 50-200 lines
        - 200-400 lines
        - 400-800 lines (consider splitting)
        - 800+ lines (must be split or have an explicit size:exception)
    validations:
      required: true

  - type: checkboxes
    id: checklist
    attributes:
      label: Checklist
      options:
        - label: I have read [CONTRIBUTING.md](../blob/main/CONTRIBUTING.md)
          required: true
        - label: I have added/updated tests
          required: false
        - label: I have run `make lint` and `make test` locally
          required: true
        - label: I have updated the docs (README, docs/, comments) if needed
          required: false
        - label: This PR does not introduce a security regression
          required: true

  - type: input
    id: related
    attributes:
      label: Related issues / ADRs
      description: "e.g. Closes #42, ADR-007"
    validations:
      required: false
