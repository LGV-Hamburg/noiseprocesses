.ONESHELL:
SHELL=/bin/bash
.PHONY: all clean build dist

# Variables
JAVA_HOME ?= $(shell which java)
GRADLE = ./gradlew
MVN = mvn
DIST_DIR = dist
WPS_SCRIPTS = wps_scripts

config ?= .env

include $(config)
export $(shell sed 's/=.*//' $(config))

GIT_COMMIT := $(shell git rev-parse --short HEAD)

all: build dist lock build-image run-local

lock:
	@echo 'Creating poetry lockfile'
	poetry lock

build-image:
	@echo 'Building release ${CONTAINER_REGISTRY}/analytics/$(IMAGE_NAME):$(IMAGE_TAG)'
# build your image
	docker compose -f docker-compose-build.yaml build --build-arg SOURCE_COMMIT=$(GIT_COMMIT) app

push-registry:
# login into our azure registry
	az acr login -n lgvudh
# push image to the registry
	docker push  ${CONTAINER_REGISTRY}/analytics/$(IMAGE_NAME):$(IMAGE_TAG)

run-local:
# run container in foreground
	docker compose -f docker-compose-dev.yaml up

build-docs:
	jupyter-book build docs

clean-docs:
	jupyter-book clean docs

# Clean build artifacts
clean:
	cd NoiseModelling && $(MVN) clean
	cd $(WPS_SCRIPTS) && $(GRADLE) clean
	rm -rf $(DIST_DIR)

# Build Java libraries and Groovy scripts
build:
	cd NoiseModelling && $(MVN) install -DskipTests
	cd $(WPS_SCRIPTS) && $(GRADLE) build -x test

# Create distribution
dist: build
	mkdir -p $(DIST_DIR)
	cd NoiseModelling/$(WPS_SCRIPTS) && $(GRADLE) assembleDist
	cd build/distributions && unzip -o scriptrunner.zip
	cp -r scriptrunner/* ../../../../$(DIST_DIR)
	rm -r NoiseModelling/wps_scripts/build

# Check Java version
check-java:
	@echo "Checking Java version..."
	@java -version
	@if [ $$(java -version 2>&1 | head -n 1 | cut -d'"' -f2 | cut -d'.' -f1) -lt 11 ]; then \
		echo "Error: Java 11 or higher is required"; \
		exit 1; \
	fi