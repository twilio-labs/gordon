ORG := security
PROJECT := gordon
TAG := $(REPOSITORY)/$(ORG)/$(PROJECT):latest
TEST_IMAGE_NAME := $(ORG)/$(PROJECT)-test
TEST_ARGS:= --volume "$(CURDIR)/build":"/build" --env-file ./configuration/environment/test.env --name gordon-test $(TEST_IMAGE_NAME)

DOCKER_RUN:= docker run

build:
	docker build . --tag $(PROJECT)

build-test:
	echo $(TEST_IMAGE_NAME)
	docker build --file Dockerfile.test . --tag $(TEST_IMAGE_NAME)

test: build-test clean-test
	$(DOCKER_RUN) $(TEST_ARGS)

serve:
	docker-compose up --build gordon

clean:
	rm -rf build

clean-test:
	-@docker rm $(PROJECT)-test
