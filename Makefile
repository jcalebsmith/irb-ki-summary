SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

IMAGE_NAME := summary-backend

build:
	podman build -t $(IMAGE_NAME) .
.PHONY: build

run_container:
	podman run --rm -d --name $(IMAGE_NAME) -p 2222:22 -v ./code:/code:Z $(IMAGE_NAME)
.PHONY: run_container
