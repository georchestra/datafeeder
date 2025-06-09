install:
	./mvnw clean install -DskipTests

test:
	docker compose
	./mvnw clean verify

release:
	./mvnw clean release:prepare -Darguments="-DskipTests"